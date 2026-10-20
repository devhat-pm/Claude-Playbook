# Building MCP servers for internal APIs

Runnable files are in [`examples/building-mcp-servers/`](examples/building-mcp-servers/). Both servers expose the same three tools over the same fake-or-real Orders API, so you can diff the two implementations:

```
examples/building-mcp-servers/
  python/server.py, requirements.txt         # MCP Python SDK v2 (mcp>=2.3), Python 3.11+
  typescript/server.mjs, package.json        # MCP TypeScript SDK v2 (@modelcontextprotocol/server 2.3), Node 20+
  smoke.sh                                   # 401 check, initialize, tools/list, tools/call with curl only
```

Env contract (both servers): `PUBLIC_URL` (the exact URL clients connect to), `OAUTH_ISSUER`, `OAUTH_INTROSPECTION_URL` + `OAUTH_CLIENT_ID/SECRET` (prod), `MCP_DEV_TOKEN` (local only), and `INTERNAL_API_URL` + `INTERNAL_API_TOKEN` (fixtures are served when these are unset). The internal API credential stays on the server. Claude only ever holds a token for the MCP server, and the server forwards the caller as `X-On-Behalf-Of`.

Both SDKs are now on **v2** (TypeScript v2 shipped 2026-07-27), so most blog posts and older tutorials show v1 APIs. Python v1 is `from mcp.server.fastmcp import FastMCP` and TypeScript v1 is `@modelcontextprotocol/sdk` + `StreamableHTTPServerTransport`. That code still runs on v1 packages, but you can't mix it with v2.

Pick the deployment based on who needs to reach the server:

| Reached from | Requirement | Recipe |
|---|---|---|
| Claude Code only (your laptop, VPN) | Anything Claude Code can reach: localhost, internal DNS | 4 |
| claude.ai / Desktop / mobile / Cowork as a custom connector | Public HTTPS reachable from Anthropic's IP ranges (allowlist them on your firewall) | 4 |
| Messages API or Managed Agents, server stays private | MCP tunnel (research preview), with no inbound ports | 5 |

---

## Recipe 1: Remote server in Python with OAuth resource-server auth

**Problem.** You want Claude to query and act on an internal service with per-user identity, not a shared API key pasted into a config. It also has to survive being exposed beyond localhost.

**Setup.** [`python/server.py`](examples/building-mcp-servers/python/server.py). The parts that matter:

```python
class OrdersTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> Optional[AccessToken]:
        # prod: POST to RFC 7662 introspection; return None to reject
        ...
        return AccessToken(token=token, client_id=..., scopes=body["scope"].split(),
                           expires_at=body.get("exp"), resource=PUBLIC_URL if PUBLIC_URL in auds else None,
                           subject=body.get("sub"))

mcp = MCPServer("orders", instructions="Search before you get; get before you refund. ...",
    token_verifier=OrdersTokenVerifier(),
    auth=AuthSettings(issuer_url=AnyHttpUrl(ISSUER), resource_server_url=AnyHttpUrl(PUBLIC_URL),
                      required_scopes=["orders:read"], validate_token_resource=True))

@mcp.tool(title="Refund order", annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, ...))
async def orders_refund(order_id: Annotated[str, Field(pattern=r"^ord_[a-z0-9]+$")],
                        reason: Annotated[RefundReason, Field(description=...)], ...) -> str:
    tok = get_access_token()
    if tok is not None and "orders:write" not in tok.scopes:
        raise ToolError("This connection is read-only (missing scope orders:write). ...")

mcp.run(transport="streamable-http", host=..., port=...,
        transport_security=TransportSecuritySettings(allowed_hosts=[public_host, public_host + ":*", ...]))
```

Run it without installing anything globally:

```bash
cd examples/building-mcp-servers/python
MCP_DEV_TOKEN=devtok PORT=8000 uv run --no-project --python 3.12 --with 'mcp>=2.3,<3' --with httpx python server.py
MCP_URL=http://127.0.0.1:8000/mcp MCP_TOKEN=devtok ../smoke.sh orders_search '{"customer_email":"ana@example.com"}'
```

**Output.** This is from a real run against the fixtures. Unauthenticated requests get the discovery challenge, which is what lets Claude's OAuth client find your IdP:

```
HTTP/1.1 401 Unauthorized
www-authenticate: Bearer error="invalid_token", error_description="Authentication required",
  resource_metadata="http://127.0.0.1:8000/.well-known/oauth-protected-resource/mcp"
```

The SDK serves `/.well-known/oauth-protected-resource/mcp` (RFC 9728) from `AuthSettings`. `orders_search` returns `{"orders":[{"id":"ord_7f3k2","status":"shipped","total":"129.00 USD",...}],"has_more":false}`. `orders_refund` with `reason:"oops"` never reaches your code, because the Literal enum rejects it and the result comes back `isError: true`.

**Failure modes.**
- The Python SDK v2 needs Python 3.11+ per its README (PyPI metadata says ≥3.10). The file only uses 3.9 syntax so it lints anywhere, but it won't *run* on 3.9.
- `ToolError` vs `MCPError`: raise `ToolError` for anything a smarter call could fix (bad id, missing filter, upstream 5xx), because the model sees the message. `MCPError` becomes a JSON-RPC error that the model never sees. **Never `return` an error string**: it reads as success (`is_error=False`).
- `token_verifier=` without `auth=` (or the other way round) raises `ValueError` at construction.
- `validate_token_resource=True` rejects every token if your IdP puts its own audience ID (Auth0 API identifier, Entra app ID) in `aud`. In that case set it to `False` and check `aud` inside the verifier.
- Behind a proxy or tunnel, the default DNS-rebinding guard accepts only localhost `Host` headers. List the public host in `allowed_hosts` (both `host` and `host:*`), or set `enable_dns_rebinding_protection=False` if the proxy already pins `Host`.
- Auth only exists on HTTP. Over stdio and the in-memory test client, `get_access_token()` returns `None`. The scope check above treats `None` as local/dev, so don't ship stdio to untrusted hosts.

Source: https://py.sdk.modelcontextprotocol.io/run/authorization/index.md, https://py.sdk.modelcontextprotocol.io/run/index.md, https://py.sdk.modelcontextprotocol.io/servers/handling-errors/index.md, https://py.sdk.modelcontextprotocol.io/servers/tools/index.md, https://py.sdk.modelcontextprotocol.io/run/deploy/index.md

---

## Recipe 2: The same server in TypeScript (v2: per-request factory)

**Problem.** Your service team runs Node and wants the server deployed next to the API on their existing Express stack, scaling horizontally with no sticky sessions.

**Setup.** [`typescript/server.mjs`](examples/building-mcp-servers/typescript/server.mjs) is plain ESM, so `node server.mjs` runs it with no build step. In TS the shape is:

```ts
import { createMcpExpressApp, requireBearerAuth, getOAuthProtectedResourceMetadataUrl, mcpAuthMetadataRouter } from '@modelcontextprotocol/express';
import { toNodeHandler } from '@modelcontextprotocol/node';
import { createMcpHandler, McpServer, OAuthError, OAuthErrorCode, requireScopes, type AuthInfo } from '@modelcontextprotocol/server';
import * as z from 'zod/v4';

async function verifyAccessToken(token: string): Promise<AuthInfo> {
  const body = await introspect(token);                        // RFC 7662
  if (!body.active) throw new OAuthError(OAuthErrorCode.InvalidToken, 'inactive');
  return { token, clientId: body.sub, scopes: body.scope.split(' '),
           expiresAt: body.exp,                                // REQUIRED: unset => 401
           resource: [body.aud].flat().includes(PUBLIC_URL.href) ? PUBLIC_URL : undefined };
}

const handler = createMcpHandler(({ authInfo }) => {          // runs once PER REQUEST
  const server = new McpServer({ name: 'orders', version: '1.0.0' }, { instructions: '...' });
  server.registerTool('orders_refund', {
    description: '...', inputSchema: z.object({ order_id: z.string().regex(/^ord_[a-z0-9]+$/),
      reason: z.enum(['damaged', 'not_received', 'duplicate', 'customer_request']) }),
    annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: false },
    scopeChallenge: requireScopes('orders:write'),             // 403 insufficient_scope before the handler runs
  }, async (args, ctx) => { /* ctx.http?.authInfo is the verified caller */ });
  return server;
});

const app = createMcpExpressApp({ host: '0.0.0.0', allowedHosts: [PUBLIC_URL.hostname] });
app.use(mcpAuthMetadataRouter({ oauthMetadata, resourceServerUrl: PUBLIC_URL }));
const auth = requireBearerAuth({ verifier: { verifyAccessToken }, requiredScopes: ['orders:read'],
  resourceMetadataUrl: getOAuthProtectedResourceMetadataUrl(PUBLIC_URL), expectedResource: PUBLIC_URL });
const node = toNodeHandler(handler);
app.all('/mcp', auth, (req, res) => void node(req, res, req.body));
```

```bash
cd examples/building-mcp-servers/typescript && npm install
MCP_DEV_TOKEN=devtok node server.mjs
MCP_URL=http://127.0.0.1:3000/mcp MCP_TOKEN=devtok ../smoke.sh orders_get '{"order_id":"ord_7f3k2"}'
```

**Output.** This is from a real run. The 401 includes the required scope:

```
WWW-Authenticate: Bearer error="invalid_token", error_description="Missing Authorization header",
  scope="orders:read", resource_metadata="http://127.0.0.1:3000/.well-known/oauth-protected-resource/mcp"
```

`tools/list` shows the annotations (`orders_refund {'readOnlyHint': False, 'destructiveHint': True, ...}`). A bad enum comes back as `isError: true` with `Invalid option: expected one of "damaged"|"not_received"|...`, so Claude retries with a valid value.

**Failure modes.**
- Register tools **inside** the factory. A shared `McpServer` outside it breaks the stateless model. Put pools and caches at module scope and close over them.
- `requireBearerAuth` answers `401` for an `AuthInfo` with no `expiresAt`. Always populate it from `exp`.
- `@modelcontextprotocol/express` 2.0.1 silently drops `expectedResource`. `package.json` pins `^2.0.2`, and the docs say to upgrade it in lockstep with `@modelcontextprotocol/server`.
- The `createMcpExpressApp()` default is localhost only. Through a tunnel or load balancer, requests fail with `403 Invalid Host: <hostname>` until that hostname is in `allowedHosts`.
- Any other exception from the verifier becomes `500 server_error`, so throw `OAuthError(InvalidToken)` for rejections. Non-`UpstreamError` exceptions in tools are caught by `safe()` and turned into a non-retryable message, so stack traces never reach the model.

Source: https://ts.sdk.modelcontextprotocol.io/v2/serving/http.md, https://ts.sdk.modelcontextprotocol.io/v2/serving/express.md, https://ts.sdk.modelcontextprotocol.io/v2/serving/authorization.md, https://ts.sdk.modelcontextprotocol.io/v2/servers/errors.md, https://github.com/modelcontextprotocol/typescript-sdk/blob/main/examples/bearer-auth/server.ts

---

## Recipe 3: Tool design that Claude actually uses well

**Problem.** A wrapper with one tool per REST endpoint (`get_order`, `list_orders`, `list_order_items`, `get_customer`, `create_refund`, …) gets the wrong tool picked, unbounded lists that blow the context, opaque IDs Claude makes up, and `400 Bad Request` errors that it retries unchanged.

**Setup.** These are the rules the example servers follow, each tied to what it fixes:

| Rule | In the example | Fixes |
|---|---|---|
| Few workflow-shaped tools, namespaced `service_verb` | `orders_search`, `orders_get`, `orders_refund` | Wrong-tool selection, especially with tool search and many servers loaded |
| 3–4+ sentence descriptions: what, when to use, when not, what it doesn't return | "Use this first whenever you do not already have an order id … Does not return payment details." | Claude guessing at scope |
| Enums for closed sets (`Literal[...]` / `z.enum`), patterns for IDs, bounds for numbers | `status`, `reason`, `^ord_[a-z0-9]+$`, `limit` 1–50 | Invented values. Schema failures come back as `isError` before your code runs |
| Unambiguous param names | `customer_email`, `order_id`, `amount_cents` (not `user`, `id`, `amount`) | Unit and identity confusion |
| `response_format: "concise" \| "detailed"` | concise = id, status, formatted total, date | Context bloat. Detailed carries the IDs needed for follow-ups |
| Refuse unbounded queries | `orders_search` with no filter → `ToolError("Give at least one filter…")` | 25k-token dumps |
| Errors say what to do next | `No order 'ord_zzz'. Ids look like 'ord_7f3k2'; use orders_search by customer email.` | Blind retries |
| Strip internal fields, format for reading | `internal_flags` dropped; `"129.00 USD"` not `12900` | Leaks and misreads |
| Annotations on every tool | read-only tools `readOnlyHint: true`; refund `destructiveHint: true, idempotentHint: false` | Clients deciding when to confirm. **Hints, not security** |
| Server `instructions` for cross-tool rules | "Search before you get; get before you refund. Amounts are integer cents." | Ordering mistakes |
| Ask for an explanation, never "reasoning" | No `reasoning` param | `reasoning_extraction` refusals |

Size and time budgets to design within: claude.ai/Desktop allow about 150,000 characters per tool result and 240 s per call. Claude Code allows 25,000 tokens per result (`MAX_MCP_OUTPUT_TOKENS`) and the tool timeout is set with `MCP_TOOL_TIMEOUT`. Claude Code warns above 10,000 tokens.

Eval prompt (run it in Claude Code with only this server enabled):

```
Using only the orders tools: ana@example.com says her mug order arrived broken.
Find it, confirm the total with me, then refund it. Stop and ask before the refund.
```

**Output.** The expected trace is `orders_search(customer_email=…)` → `orders_get(ord_7f3k2)` → a question to you with the 129.00 USD total → after you confirm, `orders_refund(order_id, reason="damaged")`. Run it 5–10 times after every description change. Small wording edits move tool selection a lot.

**Failure modes.**
- Returning errors as normal content. Claude and client UIs treat the call as successful. Use `isError: true` / `raise ToolError`.
- One "god tool" with `action` + free-form `params`. Consolidating is good, but give `action` an enum and keep the schema typed.
- Descriptions that refer to other tools by a name that doesn't exist on this server. Claude will try to call it.
- Relying on `destructiveHint` to protect money. Enforce scopes server-side (Recipe 1/2). In claude.ai research mode, connector tools can run without per-call approval, so turn write tools off there.

Source: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools, https://www.anthropic.com/engineering/writing-tools-for-agents, https://claude.com/docs/connectors/building, https://py.sdk.modelcontextprotocol.io/servers/tools/index.md

---

## Recipe 4: Test from Claude Code, then ship it as a custom connector

**Problem.** The server works in curl. Now you need it in Claude Code for the team without pasting tokens into committed files, and in claude.ai for people who don't use a terminal.

**Setup.**

1. **Protocol check.** Run `smoke.sh` (above), then the Inspector CLI: `npx @modelcontextprotocol/inspector --cli http://127.0.0.1:3000/mcp --transport http --method tools/list`.
2. **Claude Code, personal.** `claude mcp add --transport http orders http://127.0.0.1:3000/mcp --header "Authorization: Bearer $MCP_DEV_TOKEN"`, then `claude mcp get orders` (on failure, the `Issue:` line shows the HTTP status and server error text) and `/mcp` inside a session.
3. **Claude Code, team.** Commit `.mcp.json` with env expansion, not a literal token:

   ```json
   { "mcpServers": { "orders": {
       "type": "http",
       "url": "${ORDERS_MCP_URL:-https://orders-mcp.internal.example.com/mcp}",
       "headers": { "Authorization": "Bearer ${ORDERS_MCP_TOKEN}" } } } }
   ```

   With SSO or short-lived tokens, replace `headers` with `"headersHelper": "/opt/bin/orders-mcp-headers.sh"`, which prints `{"Authorization": "Bearer …"}`. Claude Code re-runs it on auth errors. If the server does real OAuth, omit both: Claude Code follows the 401 → `resource_metadata` discovery and you sign in from `/mcp` (or `claude mcp login orders`; `--client-id`/`--callback-port` if your IdP needs a pre-registered redirect).
4. **Pre-approve the read tools** in `.claude/settings.json`: `"allow": ["mcp__orders__orders_search", "mcp__orders__orders_get"]`, and leave `orders_refund` prompting.
5. **claude.ai custom connector.** Deploy behind public HTTPS (or for a quick test, a tunnel such as `cloudflared tunnel --url http://localhost:3000` (unverified flag) or ngrok), set `PUBLIC_URL` to that URL so the Host allowlist and resource match, then:
   - Pro/Max: **Customize → Connectors → + Add → Add custom connector**. Team/Enterprise: an Owner goes to **Organization settings → Connectors → Add → Custom → Web**, then each member connects individually.
   - Auth options are *Sign in now / Sign in when needed / No sign in*. The OAuth client can be Claude's published identity, automatic registration (DCR), or your own. For static credentials, use **Request headers**.
   - Your IdP must allow the redirect `https://claude.ai/api/mcp/auth_callback` (plus a loopback redirect for Claude Code) and support refresh.

**Output.** `claude mcp list` shows `orders` connected. In claude.ai the connector shows **Connected**, and its page lists every tool under **Tool permissions** with your descriptions, which is exactly what Claude reads. Turn it on per chat with **+ → Connectors** and run the eval prompt from Recipe 3.

**Failure modes.**
- `.mcp.json` servers sit at `⏸ Pending approval` until someone runs `claude` interactively in a trusted folder. A cloned repo can't approve itself.
- `${ANTHROPIC_AUTH_TOKEN}`-style credential variables expand to **empty** in remote `url`/`headers`, which shows up as a 401. Use your own variable name.
- In `claude -p`/Agent SDK runs there's no `/mcp`, so complete OAuth interactively first.
- claude.ai `initialize` timeouts usually come from slow OAuth endpoints (keep them under 10 s), an overly strict `Origin` check, or a firewall/WAF dropping Anthropic egress. `403`s your app didn't generate are your CDN.
- Don't gate behaviour on `clientInfo.name` (`claude-ai`, `Anthropic`, `claude-code` all appear, and it's unauthenticated).
- Free plans get one custom connector. A shared request-header credential gives everyone that credential's access.

Source: https://code.claude.com/docs/en/mcp, https://claude.com/docs/connectors/building/testing, https://support.claude.com/en/articles/11175166-getting-started-with-custom-connectors-using-remote-mcp, https://claude.com/docs/connectors/building

---

## Recipe 5: Keep the server private with an MCP tunnel

**Problem.** Security won't expose the Orders MCP server to the internet or allowlist Anthropic IPs, but an agent on the Messages API or Managed Agents needs it.

**Setup.** MCP tunnels are a **research preview** (request access at https://claude.com/form/mcp-tunnels). Two containers in your network open outbound-only connections: `cloudflared`, plus Anthropic's `mcp-proxy`, which terminates inner TLS with a cert only you hold and routes by subdomain.

1. Console → **MCP tunnels** → **New tunnel**. Copy the **Domain** (`abcd1234.tunnel.anthropic.com`) and **Token**. For production, use programmatic access via Workload Identity Federation instead of the static token.
2. Generate a CA and a server cert for `*.${TUNNEL_DOMAIN}` (openssl commands are in the quickstart) and upload `ca.crt` with **Add certificate**. Anthropic won't connect until a CA is registered.
3. Add a route to the proxy config:

   ```yaml
   listen_addr: ":8080"
   tunnel_domain: ${TUNNEL_DOMAIN}
   tls: { cert_file: /data/tls.crt, key_file: /data/tls.key }
   routes:
     orders: http://orders-mcp:8000      # the Python server from Recipe 1, on the compose network
   ```

4. Run the server with `PUBLIC_URL=https://orders.${TUNNEL_DOMAIN}/mcp` and `HOST=0.0.0.0` so the Host allowlist and token audience match the tunnel URL.
5. Call it:

   ```bash
   curl https://api.anthropic.com/v1/messages -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01" -H "anthropic-beta: mcp-client-2025-11-20" -H "content-type: application/json" \
     -d '{"model":"claude-opus-5-5","max_tokens":1024,
          "messages":[{"role":"user","content":"List ana@example.com orders"}],
          "mcp_servers":[{"type":"url","url":"https://orders.'"$TUNNEL_DOMAIN"'/mcp","name":"orders","authorization_token":"'"$ORDERS_TOKEN"'"}],
          "tools":[{"type":"mcp_toolset","mcp_server_name":"orders"}]}'
   ```

   For Managed Agents: Console → Sessions → create a new agent → **+ MCP Server**. Tunnels with an active cert appear at the top, and you set Subdomain `orders` and Path `/mcp`.

**Output.** Claude calls `orders_search` through the tunnel with no inbound port and no public DNS for your server. Cloudflare sees connection metadata (egress IP, timing, bytes, your `*.tunnel.anthropic.com` subdomain) but not payloads.

**Failure modes.**
- **Console tunnels are not available as claude.ai connectors.** They only work with the Messages API and Managed Agents. For claude.ai you still need Recipe 4's public endpoint.
- The tunnel doesn't authenticate to your server. Keep the bearer/OAuth check and pass `authorization_token`.
- Outbound requirements: `api.anthropic.com:443` for setup, and the tunnel edge (`198.41.192.0/19`, `2606:4700:a0::/44`) on **7844 TCP and UDP**. Egress firewalls usually block 7844.
- Tunnel token + TLS private key = a party that can impersonate your proxy. Store both as high-value secrets and renew the server cert (the quickstart issues it for 90 days) before it expires.
- Whether the proxy forwards the original `Host` header or the upstream's is not stated in the docs (unverified). If the Python server returns 421/403 through the tunnel, add the upstream host (`orders-mcp:*`) to `allowed_hosts`.
- Make the request in the workspace that owns the tunnel (or set `anthropic-workspace-id`).

Source: https://platform.claude.com/docs/en/agents-and-tools/mcp-tunnels/overview.md, https://platform.claude.com/docs/en/agents-and-tools/mcp-tunnels/quickstart.md, https://platform.claude.com/docs/en/agents-and-tools/mcp-tunnels/concepts.md, https://platform.claude.com/docs/en/agents-and-tools/mcp-connector.md
