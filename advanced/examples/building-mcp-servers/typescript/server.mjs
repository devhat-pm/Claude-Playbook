// Remote MCP server for an internal Orders API (MCP TypeScript SDK v2).
// Plain ESM so it runs with `node server.mjs` (Node 20+), no build step.
//
// Env (same contract as the Python version):
//   PUBLIC_URL               https://orders-mcp.example.com/mcp  (exact URL clients use)
//   OAUTH_ISSUER             https://auth.example.com  (serves /.well-known/oauth-authorization-server)
//   OAUTH_INTROSPECTION_URL  RFC 7662 endpoint; if unset, MCP_DEV_TOKEN is accepted (dev only)
//   OAUTH_CLIENT_ID / OAUTH_CLIENT_SECRET
//   MCP_DEV_TOKEN            static bearer for local testing
//   INTERNAL_API_URL / INTERNAL_API_TOKEN   real Orders API; fixtures if unset
//   HOST / PORT              default 127.0.0.1:3000

import {
  createMcpExpressApp,
  getOAuthProtectedResourceMetadataUrl,
  mcpAuthMetadataRouter,
  requireBearerAuth,
} from '@modelcontextprotocol/express';
import { toNodeHandler } from '@modelcontextprotocol/node';
import { createMcpHandler, McpServer, OAuthError, OAuthErrorCode, requireScopes } from '@modelcontextprotocol/server';
import * as z from 'zod/v4';

const env = process.env;
const PUBLIC_URL = new URL(env.PUBLIC_URL ?? `http://127.0.0.1:${env.PORT ?? 3000}/mcp`);
const HOST = env.HOST ?? '127.0.0.1';
const PORT = Number(env.PORT ?? 3000);

// ---------------------------------------------------------------- auth ----
async function verifyAccessToken(token) {
  const now = Math.floor(Date.now() / 1000);
  if (env.OAUTH_INTROSPECTION_URL) {
    const basic = Buffer.from(`${env.OAUTH_CLIENT_ID ?? ''}:${env.OAUTH_CLIENT_SECRET ?? ''}`).toString('base64');
    const res = await fetch(env.OAUTH_INTROSPECTION_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', Authorization: `Basic ${basic}` },
      body: new URLSearchParams({ token }),
      signal: AbortSignal.timeout(5000),
    });
    const body = res.ok ? await res.json() : {};
    if (!body.active) throw new OAuthError(OAuthErrorCode.InvalidToken, 'token inactive or unknown');
    const auds = [body.aud ?? []].flat();
    return {
      token,
      clientId: String(body.sub ?? body.client_id ?? 'unknown'),
      scopes: String(body.scope ?? '').split(' ').filter(Boolean),
      expiresAt: body.exp ?? now + 300, // requireBearerAuth rejects tokens with no expiresAt
      resource: auds.includes(PUBLIC_URL.href) ? PUBLIC_URL : undefined,
    };
  }
  if (env.MCP_DEV_TOKEN && token === env.MCP_DEV_TOKEN) {
    return { token, clientId: 'dev', scopes: ['orders:read', 'orders:write'], expiresAt: now + 3600, resource: PUBLIC_URL };
  }
  throw new OAuthError(OAuthErrorCode.InvalidToken, 'unknown token');
}

// ------------------------------------------------------- upstream API ----
const FIXTURES = [
  { id: 'ord_7f3k2', customer_email: 'ana@example.com', status: 'shipped', total_cents: 12900, currency: 'USD',
    created_at: '2026-10-02', items: [{ sku: 'MUG-01', qty: 2 }], carrier: 'UPS', internal_flags: ['vip'] },
  { id: 'ord_9x1qa', customer_email: 'ana@example.com', status: 'paid', total_cents: 4500, currency: 'USD',
    created_at: '2026-10-15', items: [{ sku: 'TEE-M', qty: 1 }], carrier: null, internal_flags: [] },
];

class UpstreamError extends Error {}

async function api(method, path, caller, { params, json } = {}) {
  if (!env.INTERNAL_API_URL) return fixture(method, path, params, json);
  const url = new URL(path, env.INTERNAL_API_URL);
  for (const [k, v] of Object.entries(params ?? {})) url.searchParams.set(k, String(v));
  const res = await fetch(url, {
    method,
    headers: { Authorization: `Bearer ${env.INTERNAL_API_TOKEN ?? ''}`, 'X-On-Behalf-Of': caller,
      ...(json ? { 'Content-Type': 'application/json' } : {}) },
    body: json ? JSON.stringify(json) : undefined,
    signal: AbortSignal.timeout(20000),
  });
  if (res.status === 404) throw new UpstreamError(`Not found: ${path}. Use orders_search to find valid order ids.`);
  if (res.status === 409) throw new UpstreamError(`Conflict from Orders API: ${(await res.text()).slice(0, 300)}`);
  if (res.status >= 500) throw new UpstreamError(`Orders API is failing (${res.status}). Retry once; if it fails again, tell the user.`);
  if (!res.ok) throw new UpstreamError(`Orders API returned ${res.status}.`);
  return res.json();
}

function fixture(method, path, params = {}, json = {}) {
  if (path === '/orders') {
    const rows = FIXTURES.filter(o => (!params.email || o.customer_email === params.email) && (!params.status || o.status === params.status));
    return { data: rows.slice(0, params.limit ?? 10), has_more: false };
  }
  const id = path.split('/')[2];
  const order = FIXTURES.find(o => o.id === id);
  if (!order) throw new UpstreamError(`No order '${id}'. Ids look like 'ord_7f3k2'; use orders_search by customer email.`);
  if (method === 'POST') return { refund_id: 're_demo', order_id: id, amount_cents: json.amount_cents };
  return order;
}

const shape = (o, fmt) =>
  fmt === 'detailed'
    ? (({ internal_flags, ...rest }) => rest)(o)
    : { id: o.id, status: o.status, total: `${(o.total_cents / 100).toFixed(2)} ${o.currency}`, created_at: o.created_at };

const text = value => ({ content: [{ type: 'text', text: typeof value === 'string' ? value : JSON.stringify(value) }] });
const fail = message => ({ content: [{ type: 'text', text: message }], isError: true });

// Wrap handlers so upstream failures become tool errors Claude can act on.
const safe = fn => async (args, ctx) => {
  try {
    return await fn(args, ctx);
  } catch (err) {
    if (err instanceof UpstreamError) return fail(err.message);
    console.error(err);
    return fail('Unexpected server error. Do not retry; tell the user the orders tool failed.');
  }
};

// --------------------------------------------------------------- tools ----
const OrderId = z.string().regex(/^ord_[a-z0-9]+$/).describe("Order id, e.g. 'ord_7f3k2'.");
const Status = z.enum(['pending', 'paid', 'shipped', 'refunded', 'cancelled']);

function buildServer({ authInfo }) {
  const caller = authInfo?.clientId ?? 'local';
  const server = new McpServer(
    { name: 'orders', version: '1.0.0' },
    { instructions: 'Tools for the internal Orders system. Search before you get; get before you refund. Amounts are integer cents.' },
  );

  server.registerTool(
    'orders_search',
    {
      title: 'Search orders',
      description:
        "Find orders in the internal Orders system by customer email and/or status, newest first. Use this first whenever you do not already have an order id (ids look like 'ord_7f3k2'). Returns at most `limit` orders; if has_more is true, narrow the filters instead of raising the limit. Does not return payment details.",
      inputSchema: z.object({
        customer_email: z.string().email().optional().describe('Exact customer email. Use when the user names a customer.'),
        status: Status.optional().describe('Filter by lifecycle status.'),
        limit: z.number().int().min(1).max(50).default(10).describe('Max orders to return.'),
        response_format: z.enum(['concise', 'detailed']).default('concise')
          .describe("'concise' = id, status, total, date. 'detailed' adds items, carrier, email."),
      }),
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    safe(async ({ customer_email, status, limit, response_format }) => {
      if (!customer_email && !status) return fail('Give at least one filter: customer_email or status. Unfiltered scans are not allowed.');
      const params = { limit, ...(customer_email && { email: customer_email.toLowerCase() }), ...(status && { status }) };
      const page = await api('GET', '/orders', caller, { params });
      if (!page.data.length) return text(`No orders match ${JSON.stringify(params)}. Check the email spelling or drop the status filter.`);
      return text({ orders: page.data.map(o => shape(o, response_format)), has_more: page.has_more });
    }),
  );

  server.registerTool(
    'orders_get',
    {
      title: 'Get order',
      description: 'Fetch one order with line items, carrier and status. Use after orders_search, or when the user pastes an order id. Use before orders_refund to confirm the total.',
      inputSchema: z.object({ order_id: OrderId }),
      annotations: { readOnlyHint: true, openWorldHint: false },
    },
    safe(async ({ order_id }) => text(shape(await api('GET', `/orders/${order_id}`, caller), 'detailed'))),
  );

  server.registerTool(
    'orders_refund',
    {
      title: 'Refund order',
      description:
        'Issue a refund against a paid or shipped order. Moves real money and cannot be undone. Only call after the user has explicitly confirmed the order id and amount in this conversation. Fails if the order is already refunded or cancelled.',
      inputSchema: z.object({
        order_id: OrderId,
        reason: z.enum(['damaged', 'not_received', 'duplicate', 'customer_request']).describe('Why the refund is issued. Pick the closest value.'),
        amount_cents: z.number().int().min(1).optional().describe('Partial refund in cents. Omit for a full refund.'),
      }),
      annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: false },
      scopeChallenge: requireScopes('orders:write'), // 403 insufficient_scope -> client can step up
    },
    safe(async ({ order_id, reason, amount_cents }) => {
      const order = await api('GET', `/orders/${order_id}`, caller);
      if (!['paid', 'shipped'].includes(order.status)) return fail(`Order ${order_id} is '${order.status}'; only paid or shipped orders can be refunded.`);
      if (amount_cents && amount_cents > order.total_cents) return fail(`amount_cents ${amount_cents} exceeds order total ${order.total_cents}.`);
      return text(await api('POST', `/orders/${order_id}/refunds`, caller, { json: { reason, amount_cents: amount_cents ?? order.total_cents } }));
    }),
  );

  return server;
}

// ---------------------------------------------------------------- http ----
const app = createMcpExpressApp({ host: HOST, allowedHosts: [PUBLIC_URL.hostname, 'localhost', '127.0.0.1'] });

if (env.OAUTH_ISSUER) {
  // Publish RFC 9728 metadata so Claude can discover the authorization server from the 401.
  const asMeta = await fetch(new URL('/.well-known/oauth-authorization-server', env.OAUTH_ISSUER)).then(r => r.json());
  app.use(mcpAuthMetadataRouter({ oauthMetadata: asMeta, resourceServerUrl: PUBLIC_URL }));
}

const auth = requireBearerAuth({
  verifier: { verifyAccessToken },
  requiredScopes: ['orders:read'],
  resourceMetadataUrl: getOAuthProtectedResourceMetadataUrl(PUBLIC_URL),
  expectedResource: PUBLIC_URL,
});

const handler = createMcpHandler(buildServer);
const node = toNodeHandler(handler);
app.all('/mcp', auth, (req, res) => void node(req, res, req.body));
app.get('/healthz', (_req, res) => res.send('ok'));

app.listen(PORT, HOST, () => console.error(`orders MCP on http://${HOST}:${PORT}/mcp (public: ${PUBLIC_URL.href})`));
process.on('SIGTERM', async () => { await handler.close(); process.exit(0); });
