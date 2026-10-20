"""Remote MCP server for an internal Orders API (MCP Python SDK v2, `mcp>=2.3`).

Runtime: Python 3.11+ (SDK README; PyPI metadata says >=3.10). Kept 3.9-syntax-clean on purpose.

Env:
  PUBLIC_URL               https://orders-mcp.example.com/mcp  (exact URL clients use)
  OAUTH_ISSUER             https://auth.example.com            (your IdP)
  OAUTH_INTROSPECTION_URL  RFC 7662 endpoint; if unset, MCP_DEV_TOKEN is used (dev only)
  OAUTH_CLIENT_ID / OAUTH_CLIENT_SECRET   credentials for the introspection call
  MCP_DEV_TOKEN            static bearer token for local testing
  INTERNAL_API_URL         base URL of the real Orders API; if unset, fixtures are served
  INTERNAL_API_TOKEN       service credential for the Orders API (never exposed to Claude)
  HOST / PORT              bind address, default 127.0.0.1:8000
"""
from __future__ import annotations

import json
import os
import time
from typing import Annotated, Any, Dict, List, Literal, Optional
from urllib.parse import urlparse

import httpx
from pydantic import AnyHttpUrl, Field

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://127.0.0.1:8000/mcp")
ISSUER = os.environ.get("OAUTH_ISSUER", "https://auth.example.com")
INTROSPECTION_URL = os.environ.get("OAUTH_INTROSPECTION_URL")
API_URL = os.environ.get("INTERNAL_API_URL")
API_TOKEN = os.environ.get("INTERNAL_API_TOKEN", "")

Status = Literal["pending", "paid", "shipped", "refunded", "cancelled"]
RefundReason = Literal["damaged", "not_received", "duplicate", "customer_request"]


# ---------------------------------------------------------------- auth ----
class OrdersTokenVerifier(TokenVerifier):
    """Introspection in prod, a static dev token locally. Returns None to reject."""

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        if INTROSPECTION_URL:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    INTROSPECTION_URL,
                    data={"token": token},
                    auth=(os.environ.get("OAUTH_CLIENT_ID", ""), os.environ.get("OAUTH_CLIENT_SECRET", "")),
                )
            if resp.status_code != 200:
                return None
            body = resp.json()
            if not body.get("active"):
                return None
            aud = body.get("aud")
            auds = aud if isinstance(aud, list) else [aud]
            return AccessToken(
                token=token,
                client_id=str(body.get("client_id", "unknown")),
                scopes=str(body.get("scope", "")).split(),
                expires_at=body.get("exp"),
                resource=PUBLIC_URL if PUBLIC_URL in auds else None,
                subject=body.get("sub"),
            )
        dev = os.environ.get("MCP_DEV_TOKEN")
        if dev and token == dev:
            return AccessToken(
                token=token, client_id="dev", scopes=["orders:read", "orders:write"],
                expires_at=int(time.time()) + 3600, resource=PUBLIC_URL,
            )
        return None


mcp = MCPServer(
    "orders",
    instructions=(
        "Tools for the internal Orders system. Search before you get; get before you refund. "
        "Amounts are integer cents. Never refund without the user confirming the amount."
    ),
    token_verifier=OrdersTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(ISSUER),
        resource_server_url=AnyHttpUrl(PUBLIC_URL),
        required_scopes=["orders:read"],
        validate_token_resource=True,
    ),
)


# ------------------------------------------------------- upstream API ----
FIXTURES: List[Dict[str, Any]] = [
    {"id": "ord_7f3k2", "customer_email": "ana@example.com", "status": "shipped",
     "total_cents": 12900, "currency": "USD", "created_at": "2026-10-02",
     "items": [{"sku": "MUG-01", "qty": 2}], "carrier": "UPS", "internal_flags": ["vip"]},
    {"id": "ord_9x1qa", "customer_email": "ana@example.com", "status": "paid",
     "total_cents": 4500, "currency": "USD", "created_at": "2026-10-15",
     "items": [{"sku": "TEE-M", "qty": 1}], "carrier": None, "internal_flags": []},
]


async def api(method: str, path: str, caller: str, **kw: Any) -> Any:
    """Single choke point to the internal API. Swap fixtures for the real thing via env."""
    if not API_URL:
        return _fixture(method, path, kw)
    headers = {"Authorization": "Bearer " + API_TOKEN, "X-On-Behalf-Of": caller}
    async with httpx.AsyncClient(base_url=API_URL, timeout=20) as client:
        resp = await client.request(method, path, headers=headers, **kw)
    if resp.status_code == 404:
        raise ToolError("Not found: {}. Use orders_search to find valid order ids.".format(path))
    if resp.status_code == 409:
        raise ToolError("Conflict from Orders API: {}".format(resp.text[:300]))
    if resp.status_code >= 500:
        raise ToolError("Orders API is failing ({}). Retry once; if it fails again, tell the user.".format(resp.status_code))
    resp.raise_for_status()
    return resp.json()


def _fixture(method: str, path: str, kw: Dict[str, Any]) -> Any:
    if path == "/orders":
        p = kw.get("params") or {}
        rows = [o for o in FIXTURES
                if (not p.get("email") or o["customer_email"] == p["email"])
                and (not p.get("status") or o["status"] == p["status"])]
        return {"data": rows[: int(p.get("limit", 10))], "has_more": False}
    oid = path.split("/")[2]
    order = next((o for o in FIXTURES if o["id"] == oid), None)
    if order is None:
        raise ToolError("No order {!r}. Ids look like 'ord_7f3k2'; use orders_search by customer email.".format(oid))
    if method == "POST":
        return {"refund_id": "re_demo", "order_id": oid, "amount_cents": (kw.get("json") or {}).get("amount_cents")}
    return order


def caller_id() -> str:
    tok = get_access_token()
    return tok.subject or tok.client_id if tok else "local"


def shape(order: Dict[str, Any], fmt: str) -> Dict[str, Any]:
    if fmt == "detailed":
        return {k: v for k, v in order.items() if k != "internal_flags"}
    return {"id": order["id"], "status": order["status"], "total": "{:.2f} {}".format(
        order["total_cents"] / 100, order["currency"]), "created_at": order["created_at"]}


# --------------------------------------------------------------- tools ----
@mcp.tool(title="Search orders", annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
async def orders_search(
    customer_email: Annotated[Optional[str], Field(description="Exact customer email. Use this when the user names a customer.")] = None,
    status: Annotated[Optional[Status], Field(description="Filter by lifecycle status.")] = None,
    limit: Annotated[int, Field(ge=1, le=50, description="Max orders to return.")] = 10,
    response_format: Annotated[Literal["concise", "detailed"], Field(
        description="'concise' = id, status, total, date. 'detailed' adds items, carrier, email.")] = "concise",
) -> str:
    """Find orders in the internal Orders system by customer email and/or status, newest first.
    Use this first whenever you do not already have an order id (ids look like 'ord_7f3k2').
    Returns at most `limit` orders; if `has_more` is true, narrow the filters rather than raising the limit.
    Does not return payment details or internal flags."""
    if not customer_email and not status:
        raise ToolError("Give at least one filter: customer_email or status. Unfiltered scans are not allowed.")
    params: Dict[str, Any] = {"limit": limit}
    if customer_email:
        params["email"] = customer_email.strip().lower()
    if status:
        params["status"] = status
    page = await api("GET", "/orders", caller_id(), params=params)
    rows = [shape(o, response_format) for o in page["data"]]
    if not rows:
        return "No orders match {}. Check the email spelling or drop the status filter.".format(params)
    return json.dumps({"orders": rows, "has_more": page.get("has_more", False)})


@mcp.tool(title="Get order", annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
async def orders_get(
    order_id: Annotated[str, Field(pattern=r"^ord_[a-z0-9]+$", description="Order id, e.g. 'ord_7f3k2'.")],
) -> str:
    """Fetch one order with line items, carrier and status. Use after orders_search, or when
    the user pastes an order id. Use before orders_refund to confirm the total."""
    return json.dumps(shape(await api("GET", "/orders/" + order_id, caller_id()), "detailed"))


@mcp.tool(title="Refund order", annotations=ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
async def orders_refund(
    order_id: Annotated[str, Field(pattern=r"^ord_[a-z0-9]+$", description="Order to refund.")],
    reason: Annotated[RefundReason, Field(description="Why the refund is issued. Pick the closest value.")],
    amount_cents: Annotated[Optional[int], Field(ge=1, description="Partial refund in cents. Omit for a full refund.")] = None,
) -> str:
    """Issue a refund against a paid or shipped order. Moves real money and cannot be undone.
    Only call after the user has explicitly confirmed the order id and amount in this conversation.
    Fails if the order is already refunded or cancelled."""
    tok = get_access_token()
    if tok is not None and "orders:write" not in tok.scopes:
        raise ToolError("This connection is read-only (missing scope orders:write). Ask the user to have support issue the refund.")
    order = await api("GET", "/orders/" + order_id, caller_id())
    if order["status"] not in ("paid", "shipped"):
        raise ToolError("Order {} is '{}'; only paid or shipped orders can be refunded.".format(order_id, order["status"]))
    if amount_cents is not None and amount_cents > order["total_cents"]:
        raise ToolError("amount_cents {} exceeds order total {}.".format(amount_cents, order["total_cents"]))
    body = {"reason": reason, "amount_cents": amount_cents or order["total_cents"]}
    return json.dumps(await api("POST", "/orders/{}/refunds".format(order_id), caller_id(), json=body))


if __name__ == "__main__":
    public_host = urlparse(PUBLIC_URL).hostname or "127.0.0.1"
    mcp.run(
        transport="streamable-http",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        transport_security=TransportSecuritySettings(
            allowed_hosts=[public_host, public_host + ":*", "127.0.0.1:*", "localhost:*"],
        ),
    )
