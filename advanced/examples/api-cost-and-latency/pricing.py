"""Claude API list prices and a usage -> USD calculator.

Prices: USD per million tokens, copied from
https://platform.claude.com/docs/en/about-claude/pricing (read 2026-10-20).
Re-check that page before trusting totals; prices change.

Multipliers (same page):
  5m cache write = 1.25x base input, 1h cache write = 2x base input
  cache read     = 0.1x base input, except Fable 5.1 (0.025x), Opus 5.5 / Sonnet 5.5 (0.05x)
  Batch API      = 0.5x on everything; stacks with caching
  inference_geo "us" = 1.1x on every category (4.6+ models)
  Fast mode (Opus 5.5) replaces base rates with $8 / $40; cache multipliers apply on top
  Haiku 5.5: prompts over 100k tokens (input + cache reads + cache writes) use the higher rates
"""
from __future__ import annotations

from typing import Any, Dict, Optional

PRICES: Dict[str, Dict[str, float]] = {
    "claude-fable-5-1": {"input": 10.00, "output": 50.00, "cache_read_mult": 0.025},
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read_mult": 0.05,
                        "fast_input": 8.00, "fast_output": 40.00},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read_mult": 0.05},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read_mult": 0.10,
                         "long_input": 0.50, "long_output": 2.50,
                         "long_threshold": 100_000},
}

CACHE_WRITE_5M = 1.25
CACHE_WRITE_1H = 2.0
BATCH_MULT = 0.5
US_GEO_MULT = 1.1


def _get(usage: Any, key: str, default: Any = 0) -> Any:
    if usage is None:
        return default
    if isinstance(usage, dict):
        val = usage.get(key, default)
    else:
        val = getattr(usage, key, default)
    return default if val is None else val


def cost_usd(model: str, usage: Any, speed: str = "standard", batch: bool = False,
             us_geo: bool = False) -> Optional[float]:
    """Price one response's `usage` (SDK object or dict). Returns None for unknown models."""
    p = PRICES.get(model)
    if p is None:
        return None
    inp = _get(usage, "input_tokens")
    out = _get(usage, "output_tokens")
    c_read = _get(usage, "cache_read_input_tokens")
    c_write = _get(usage, "cache_creation_input_tokens")
    breakdown = _get(usage, "cache_creation", None)
    w5 = _get(breakdown, "ephemeral_5m_input_tokens", None)
    w1 = _get(breakdown, "ephemeral_1h_input_tokens", None)
    if w5 is None and w1 is None:          # older usage shape: assume 5m TTL
        w5, w1 = c_write, 0
    w5, w1 = w5 or 0, w1 or 0

    base_in, base_out = p["input"], p["output"]
    if speed == "fast" and "fast_input" in p:
        base_in, base_out = p["fast_input"], p["fast_output"]
    if "long_threshold" in p and (inp + c_read + c_write) > p["long_threshold"]:
        base_in, base_out = p["long_input"], p["long_output"]

    usd = (inp * base_in
           + w5 * base_in * CACHE_WRITE_5M
           + w1 * base_in * CACHE_WRITE_1H
           + c_read * base_in * p["cache_read_mult"]
           + out * base_out) / 1_000_000
    if batch:
        usd *= BATCH_MULT
    if us_geo:
        usd *= US_GEO_MULT
    return usd


def uncached_cost_usd(model: str, usage: Any, **kw: Any) -> Optional[float]:
    """Counterfactual: the same request with every prompt token billed as plain input."""
    total_in = (_get(usage, "input_tokens") + _get(usage, "cache_read_input_tokens")
                + _get(usage, "cache_creation_input_tokens"))
    flat = {"input_tokens": total_in, "output_tokens": _get(usage, "output_tokens")}
    return cost_usd(model, flat, **kw)


if __name__ == "__main__":
    demo = {"input_tokens": 50, "output_tokens": 400,
            "cache_read_input_tokens": 100_000, "cache_creation_input_tokens": 0}
    for m in PRICES:
        print("%-18s cached $%.4f   uncached $%.4f" % (
            m, cost_usd(m, demo), uncached_cost_usd(m, demo)))
