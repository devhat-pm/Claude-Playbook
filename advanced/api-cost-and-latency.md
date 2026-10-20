# API cost and latency: caching, effort, fast mode, batch, routing

Runnable scripts are in [`examples/api-cost-and-latency/`](examples/api-cost-and-latency/). All of them read `ANTHROPIC_API_KEY` from the environment, need `pip install anthropic`, and have a `--dry-run` or `--offline` mode that makes no calls.

To rerun the measured benchmarks, recreate `examples/api-cost-and-latency/.env` containing `ANTHROPIC_API_KEY=...`. It's git-ignored and not shipped. `bench.py` and `cache_probe.py` load it when `python-dotenv` is installed.

| File | Does |
|---|---|
| `pricing.py` | List-price table and a `usage -> USD` function: cache 5m/1h writes, model-specific cache-read multipliers, fast mode, batch, Haiku 5.5 long-prompt tier, US geo |
| `cache_probe.py` | Measures cache writes, reads, hit ratio, TTFT and savings for a fixed prefix |
| `bench.py` | Streams a model × effort × speed matrix and reports TTFT, total latency, output tokens/s, cost and pass rate |
| `task.json` | 20 labelled spam/ham messages (phishing, newsletters, personal mail, receipts) used for the measured run in Recipe 2 |
| `cache-fixture/` | A fictional ~3.5k-token handbook and six questions used for the measured run in Recipe 1 |
| `results-2026-10-20.json`, `cache-results-2026-10-20.txt` | Raw output of those two runs |
| `batch_pipeline.py` | JSONL → Message Batches → JSONL, with chunking, cached shared prefix, retry file and cost |
| `route.py` | Picks model, effort and speed by task type and token count, and prices the alternatives |

**Prices used** (USD per MTok, [pricing page](https://platform.claude.com/docs/en/about-claude/pricing), read 2026-10-20):

| Model | Input | 5m write | 1h write | Cache read | Output | Batch in/out |
|---|---|---|---|---|---|---|
| `claude-fable-5-1` | 10 | 12.50 | 20 | 0.25 (0.025×) | 50 | 5 / 25 |
| `claude-opus-5-5` | 4 | 5 | 8 | 0.20 (0.05×) | 20 | 2 / 10 |
| `claude-opus-5-5` `speed: "fast"` | 8 | 10* | 16* | 0.40* | 40 | not available |
| `claude-sonnet-5-5` | 2 | 2.50 | 4 | 0.10 (0.05×) | 10 | 1 / 5 |
| `claude-haiku-5-5` ≤100k prompt | 0.10 | 0.125 | 0.20 | 0.01 | 0.50 | 0.05 / 0.25 |
| `claude-haiku-5-5` >100k prompt | 0.50 | 0.625 | 1 | 0.05 | 2.50 | 0.25 / 1.25 |

\* Derived: the pricing page says cache multipliers apply on top of fast-mode rates. It doesn't list these figures.

US-only inference (`inference_geo: "us"`) multiplies every category by 1.1. Current models use a tokenizer that produces about 30% more tokens than the pre-Opus 4.7 one, so old token counts understate cost.

---

## Recipe 1: Lay out prompts for caching and measure the hit rate

**Problem.** "We turned on caching" often means a breakpoint on the user message, so every request pays a 1.25× write and never reads it back. Two other common causes are a timestamp in the system prompt, and parallel requests that all miss because none of them waited for the first write.

**Setup.** Order the request from most static to least static: `tools` → `system` → `messages`. Put `cache_control` on the **last block that is identical across requests**, never on the block that varies.

```python
system=[
  {"type": "text", "text": INSTRUCTIONS},                                # static
  {"type": "text", "text": DOC, "cache_control": {"type": "ephemeral"}},  # static, breakpoint
],
messages=[{"role": "user", "content": question}],                        # varies, after breakpoint
output_config={"effort": "low"},                                         # part of the cache key, keep fixed
```

For multi-turn chat, use top-level `cache_control={"type": "ephemeral"}` instead (automatic caching). The breakpoint then moves to the last cacheable block each turn and uses one of the 4 slots.

```bash
python3 cache_probe.py --doc handbook.md --questions qs.txt --model claude-sonnet-5-5 --warm
python3 cache_probe.py --doc handbook.md --questions qs.txt --ttl 1h --gap 400   # survive >5 min gaps
```

**Minimum prefix.** Nothing is cached unless the prefix up to the breakpoint reaches the model's minimum cacheable length: 512 tokens on Fable 5.1, Opus 5.5, Sonnet 5.5 and Haiku 5.5, and higher on older models. Below it, the API returns no error and both cache fields are 0. Size test fixtures well above the minimum. The measured run below uses a ~3.5k-token prefix so the result doesn't depend on that threshold.

`--warm` first sends the same prefix with `max_tokens: 0`. The API writes the cache and returns an empty `content` with `stop_reason: "max_tokens"`, and no output is billed. A user's first real request then reads from cache.

Read these three `usage` fields: `cache_creation_input_tokens` (written), `cache_read_input_tokens` (read) and `input_tokens` (after the last breakpoint). Hit ratio = read ÷ (read + written + input). With 1h writes, `usage.cache_creation.ephemeral_1h_input_tokens` shows the split.

**Output.** One row per request, then totals. Measured on 2026-10-20 (one run, not a benchmark suite), Claude API with default `inference_geo` (not pinned), client region not recorded:

```
python3 cache_probe.py --doc cache-fixture/handbook.md --questions cache-fixture/questions.txt \
  --model claude-sonnet-5-5 --warm

prefix ~3483 tokens (count_tokens estimate)
warm-up: wrote 3476 cache tokens, stop_reason=max_tokens
#      write     read   uncach  ttft_s    hit%     cost$
1          0     3476       22    0.87     99%   0.00077
2          0     3476       23    0.77     99%   0.00083
3          0     3476       19    1.38     99%   0.00104
4          0     3476       23    1.51     99%   0.00124
5          0     3476       18    0.88     99%   0.00148
6          0     3476       16    0.96    100%   0.00122

hit ratio (read / all prompt tokens): 99.4%
cost with cache $0.0066 vs without $0.0462  (saved 86%)
```

`write` is `usage.cache_creation_input_tokens`, `read` is `usage.cache_read_input_tokens` and `uncach` is `usage.input_tokens`. The warm-up wrote 3,476 tokens (`cache_creation_input_tokens`). Every later request then read all 3,476 from cache (`cache_read_input_tokens`) and wrote none. The totals leave out the warm-up write itself, about $0.0087 at $2.50/MTok, so the net saving across these six questions is about 67%. Raw output: [`cache-results-2026-10-20.txt`](examples/api-cost-and-latency/cache-results-2026-10-20.txt).

**Failure modes.**
- *Both cache fields are 0.* The prefix is below the minimum: 512 tokens on Fable 5.1, Opus 5.5, Sonnet 5.5 and Haiku 5.5, and higher on older models. No error is returned. The probe prints `nothing cached` and runs `count_tokens` on the prefix up front.
- *Silent invalidation.* Changing tool definitions invalidates everything. Switching `speed` invalidates the system and messages caches. Changing `output_config.effort` or the thinking config always invalidates messages, and on some models also tools and system. So do toggling web search or citations, `tool_choice` changes and image changes. Non-deterministic JSON key order in `tool_use` input (Go, Swift) breaks matches.
- *Long agent loops.* The lookback checks only 20 blocks back from a breakpoint. If a turn adds 20 or more blocks, add a second breakpoint.
- *Parallel fan-out.* An entry only exists once the first response begins streaming. Send one request, wait for its first token, then fan out.
- *TTL.* The clock starts at the start of the request, not at the end of the response. A 4-minute stream leaves about 1 minute to reuse a 5m entry. Use 1h when gaps run 5–60 minutes (2× write; break-even after 2 reads). Within 5 minutes, the 5m TTL refreshes for free on every hit.
- Caches are isolated per workspace on the Claude API, so an identical prompt in another workspace doesn't hit.

Source: https://platform.claude.com/docs/en/build-with-claude/prompt-caching · https://platform.claude.com/docs/en/about-claude/pricing

---

## Recipe 2: Effort sweep before you switch models

**Problem.** Teams jump between models when the cheaper lever is `output_config.effort`. Effort scales every output token: thinking, text and tool calls. Defaults also differ by model. Opus 5.5 and Haiku 5.5 default to `medium`, while Fable 5.1 and Sonnet 5.5 default to `high`. So "same request, new model" also silently changes effort.

**Setup.** Either write a labelled task file (a JSON list of `{"id", "text", "label"}`) or a single prompt plus a pass regex, then sweep:

```bash
python3 bench.py --task-file task.json \
  --models claude-haiku-5-5 claude-sonnet-5-5 claude-opus-5-5 \
  --efforts low medium high --runs 5 --max-tokens 8000
python3 bench.py --prompt-file task.txt --system-file sys.txt ... --expect '"label":\s*"(spam|ham)"'
python3 bench.py ... --dry-run     # prints the 9-cell matrix, no calls
```

With `--task-file`, each run sends every item in one request and asks for a JSON object mapping id to label. The pass rate is the fraction of items whose label matches exactly. The script loads `ANTHROPIC_API_KEY` from a git-ignored `.env` next to it if `python-dotenv` is installed.

Each run streams (`client.messages.stream`), so TTFT is the first `content_block_delta` (thinking or text), and output tokens/s = output tokens ÷ (total − TTFT). Cost comes from the response `usage` through `pricing.py`. The docs show `output_config` and `speed` as keyword arguments on `messages.create`. `output_config` passed the same way to `messages.stream` worked in the measured run below (Python SDK 0.125.0). Passing `speed` to `messages.stream` is (unverified), because that run used standard speed only. If your SDK version rejects either, upgrade it, or pass them through `extra_body`. At `xhigh` or `max`, raise `--max-tokens` to 64k or more: `max_tokens` is a hard cap on thinking plus text.

To change effort mid-conversation without breaking the cache (beta: Fable 5.1, Opus 5.5, Opus 5, Sonnet 5.5, Haiku 5.5), send header `anthropic-beta: mid-conversation-output-config-2026-07-01` and insert `{"role": "system", "content": [], "output_config": {"effort": "low"}}` before the next user turn. Changing top-level effort instead starts the cache over.

**Output.** `bench_results.csv` (one row per run, or JSON if `--out` ends in `.json`) and a markdown table of medians.

Measured on 2026-10-20, 10:05–10:07 UTC. This is **one run, not a benchmark suite**: 5 repetitions per cell, `task.json` (20 spam/ham items, about 1.65k prompt tokens), `--max-tokens 8000`. It used the Claude API with default `inference_geo` (not pinned); the client region wasn't recorded. Latency includes the network path from one client machine. Cost is computed from each response's `usage` at list price.

| model | effort | speed | p50 total s | p50 TTFT s | p50 out tok | mean $/req | $/1k req | pass (20 items × 5 runs) |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-5-5 | low | standard | 1.37 | 1.00 | 144 | 0.00024 | 0.24 | 100% |
| claude-haiku-5-5 | medium | standard | 1.32 | 0.98 | 144 | 0.00024 | 0.24 | 100% |
| claude-haiku-5-5 | high | standard | 1.44 | 1.06 | 144 | 0.00024 | 0.24 | 100% |
| claude-sonnet-5-5 | low | standard | 1.60 | 1.04 | 125 | 0.00454 | 4.54 | 100% |
| claude-sonnet-5-5 | medium | standard | 1.57 | 1.02 | 125 | 0.00458 | 4.58 | 100% |
| claude-sonnet-5-5 | high | standard | 1.76 | 1.19 | 125 | 0.00458 | 4.58 | 100% |
| claude-opus-5-5 | low | standard | 2.33 | 1.48 | 144 | 0.00939 | 9.39 | 100% |
| claude-opus-5-5 | medium | standard | 2.76 | 1.86 | 144 | 0.00947 | 9.47 | 100% |
| claude-opus-5-5 | high | standard | 2.41 | 1.75 | 144 | 0.00947 | 9.47 | 100% |
| claude-opus-5-5 | any | fast | not measured | | | | | |
| claude-fable-5-1 | any | standard | not measured | | | | | |

Raw rows: [`results-2026-10-20.json`](examples/api-cost-and-latency/results-2026-10-20.json). The whole run cost about $0.21.

How to read it: this task is too easy to separate the models. Every cell labelled all 20 items correctly, and output-token counts barely moved with effort, so effort changed neither cost nor quality here. The spread is price per token, about 40× from Haiku to Opus, plus roughly 1 s more latency on Opus. On a task this easy, the cheapest cell wins. A harder task, where effort changes thinking length and the pass rate drops, is where the sweep earns its keep.

To read `bench.py`'s output: pick the cheapest row whose pass rate meets your bar, then confirm it with a higher `--runs` value. Most of the cost spread comes from output tokens, which is exactly what effort controls.

**Failure modes.**
- *400 errors on some cells.* Not every model accepts every level, and several reject `thinking: {"type": "disabled"}` at `xhigh` or `max`. On Opus 5.5 it's rejected at every level because thinking is always on. `bench.py` logs the HTTP error and moves on.
- *`stop_reason: max_tokens`* at high effort means thinking used up the budget. It's in the CSV. Raise `--max-tokens` before you judge quality.
- *Effort isn't a length control.* On some models lower effort mostly cuts thinking, not visible verbosity. Ask for length in the prompt.
- *Small n.* Medians over 3 runs are noisy. Use `--runs 10` or more for anything you'll publish internally.

Source: https://platform.claude.com/docs/en/build-with-claude/effort · https://platform.claude.com/docs/en/models/overview

---

## Recipe 3: Fast mode with a standard-speed fallback

**Problem.** Interactive Opus sessions feel slow while long answers stream. Fast mode on `claude-opus-5-5` runs the same model at up to 2.5× output tokens/s, with no beta header, for $8/$40 per MTok (2× standard). Its gain is in output tokens/s, not time to first token. It has its own rate limit, so you need a plan for 429s.

**Setup.**

```python
import anthropic
client = anthropic.Anthropic()                       # ANTHROPIC_API_KEY from env
fast = client.with_options(max_retries=0)            # fail fast on fast-mode 429

def create(**params):
    try:
        return fast.messages.create(speed="fast", **params)
    except anthropic.RateLimitError:
        return client.messages.create(**params)      # standard speed, default retries
```

Measure the difference with `bench.py --models claude-opus-5-5 --speeds standard fast --runs 10`. Compare `p50 OTPS` and `p50 total s`, not TTFT. Check `usage.speed` on every response (`"fast"` or `"standard"`). The `anthropic-fast-output-tokens-remaining` response header shows fast-mode headroom.

**Output.** Two rows per effort level. The expected shape is OTPS up to 2.5× higher, TTFT about the same, and `$/1k req` exactly 2× for the same tokens (`pricing.py` applies $8/$40 when `usage.speed == "fast"`).

**Failure modes.**
- *Fallback costs a cache miss.* Requests at different speeds don't share cached prefixes, so the first standard request after a 429 rewrites the prefix. With large cached prefixes, retrying fast after `retry-after` (short, because capacity replenishes continuously) can cost less than falling back.
- Setting `max_retries=0` also disables retries for 5xx and overloaded errors. Keep the default-retry client for the fallback, as above.
- Not available in the Batch API (`speed` is a validation error there) or with a Priority Tier commitment. On Opus 5 and Opus 4.8 it's a research preview behind `fast-mode-2026-02-01`. Other models return an error.
- Short replies gain little, because the speed-up applies to generation time. Use it where output is long and someone is waiting.

Source: https://platform.claude.com/docs/en/build-with-claude/fast-mode · https://platform.claude.com/docs/en/about-claude/pricing#fast-mode-pricing

---

## Recipe 4: Batch pipeline with a shared cached prefix

**Problem.** Nightly classification or extraction over 50k+ items doesn't need answers in seconds. Synchronous calls pay full price and compete with interactive traffic for rate limit.

**Setup.**

```bash
python3 batch_pipeline.py submit items.jsonl --model claude-haiku-5-5 --system-file rubric.md --effort low
python3 batch_pipeline.py status
python3 batch_pipeline.py collect --out results.jsonl --items-for-retry items.jsonl
python3 batch_pipeline.py submit retry.jsonl --model claude-haiku-5-5 --system-file rubric.md
```

What the script handles:
- **Chunking.** It splits input under the 100,000-request / 256 MB per-batch limits, using a 200 MB byte budget for margin.
- **custom_id.** It sanitises IDs to `^[a-zA-Z0-9_-]{1,64}$`, de-duplicates them, and keeps an `id_map` in `.batch_state.json`, because result order isn't guaranteed.
- **Caching.** Every request carries the same `system` block with `cache_control`. Discounts stack, so a cache read on Haiku 5.5 in a batch costs $0.005/MTok. Hits inside a batch are best-effort; the docs cite 30–98%.
- **Results.** It sorts results into `succeeded`, `errored`, `canceled` and `expired`. `invalid_request_error` items need a fixed body and are not retried. Other errors and expirations go to `retry.jsonl`.
- **Cost.** It prices each succeeded `usage` with `batch=True` (0.5×).

**Output.** `results.jsonl` (`{"id", "status", "text", "usage"}` per line), a count line such as `{'succeeded': 49873, 'errored': 12, 'canceled': 0, 'expired': 115}`, the batch cost at list price, and `retry.jsonl`.

**Failure modes.**
- Most batches end within 1 hour. Unfinished requests expire at 24 hours, and results can be downloaded for 29 days from creation. Heavy demand means more expirations, so keep the retry loop.
- `stream`, `speed` and `max_tokens: 0` are rejected inside batches, so don't try to pre-warm the cache there.
- Batches can slightly overshoot the workspace spend limit, because they're processed concurrently.
- Dry-run one request shape with the synchronous API first. A schema error is repeated across every request in the batch.
- For very long outputs, Messages Batches allows up to 300k output tokens on current models with beta header `output-300k-2026-03-24`. `batch_pipeline.py` doesn't send it.

Source: https://platform.claude.com/docs/en/build-with-claude/batch-processing · https://platform.claude.com/docs/en/about-claude/pricing#batch-processing

---

## Recipe 5: Count tokens, then route; know what service tiers still buy you

**Problem.** Sending everything to one model overpays on easy traffic or fails on hard traffic. Pricing from character counts is wrong by about 30% on the current tokenizer, and Haiku 5.5 prices change at 100k prompt tokens.

**Setup.**

```bash
python3 route.py --task extract --prompt-file ticket.txt
python3 route.py --task agentic --prompt-file spec.md --latency-critical
python3 route.py --task classify --prompt-file x.txt --offline     # chars/3.5 estimate, no call
```

- `client.messages.count_tokens(model=..., system=..., messages=..., tools=...)` is free. It has its own per-minute limits (5k, 10k or 20k RPM depending on tier, separate from message limits), and it counts with the tokenizer of the `model` you pass. Always count with the model you'll actually call.
- The `ROUTES` table follows the models overview: Haiku for classification, extraction and routing; Sonnet for speed plus intelligence; Opus as the default for agentic and knowledge work; Fable when Opus at high effort still falls short. It's a starting policy. Replace each row with the cheapest cell that passes in `bench.py`.
- `--latency-critical` switches Opus to fast mode, or lowers effort on the other models.

**Output.**

```
route: claude-opus-5-5 effort=high speed=fast
prompt tokens: 22 (estimate)
est. cost/request: $0.32018   per 1M requests: $320176
alternatives (same tokens, expected output 8000):
  claude-fable-5-1   $0.40022
  claude-opus-5-5    $0.16009
  claude-sonnet-5-5  $0.08004
  claude-haiku-5-5   $0.00400
note: Opus 5.5 fast mode: up to 2.5x output tok/s at 2x price; not in Batch.
```

**Service tiers in practice.** Priority Tier commitments can no longer be bought. They also don't cover any current 5.x model (Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5). So for these models your levers are standard (default), Batch (async, 50% off) and fast mode (sync, 2×, Opus 5.5). `service_tier` accepts `"auto"` (default) or `"standard_only"`, and `usage.service_tier` reports what you got. That's only useful for orgs that still hold a commitment on an older model.

**Failure modes.**
- `count_tokens` is an estimate and ignores caching. It rejects server tools (web search and fetch, code execution), the MCP connector, and `url` or `file` image and document sources. Send base64, or read the real `usage` instead.
- Thinking blocks from earlier turns count as input on models that keep them.
- Routing on prompt length alone sends short but hard prompts to Haiku. Route on task type first, then use length to adjust.
- `inference_geo: "us"` adds 10% to every category, including cache reads. Pass `us_geo=True` to `cost_usd` if you use it.

Source: https://platform.claude.com/docs/en/build-with-claude/token-counting · https://platform.claude.com/docs/en/api/service-tiers · https://platform.claude.com/docs/en/models/overview · https://platform.claude.com/docs/en/about-claude/pricing
