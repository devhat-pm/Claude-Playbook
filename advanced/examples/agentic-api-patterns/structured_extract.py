"""Schema-guaranteed extraction + strict tools, with every stop_reason handled.

Requires: pip install anthropic pydantic ; export ANTHROPIC_API_KEY=...
Run:      python3 structured_extract.py invoice.txt

Grounded in:
  https://platform.claude.com/docs/en/build-with-claude/structured-outputs
  https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use
  https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons
  https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional

import anthropic
from pydantic import BaseModel

MODEL = "claude-sonnet-5-5"
CATEGORIES = ["hardware", "software", "services", "other"]


class LineItem(BaseModel):
    description: str
    category: str  # constrained via enum in the strict tool below; normalise casing anyway
    amount: float


class Invoice(BaseModel):
    vendor: str
    invoice_number: str
    currency: str
    total: float
    line_items: List[LineItem]
    short_rationale: str  # NOT "reasoning"/"thinking": those fields can trigger reasoning_extraction refusals


# Strict tool: grammar-constrained input. additionalProperties false, everything required.
FLAG_TOOL: Dict[str, Any] = {
    "name": "flag_for_review",
    "description": "Flag an invoice for human review when totals don't reconcile.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "reason": {"type": "string", "enum": ["total_mismatch", "missing_po", "duplicate"]},
        },
        "required": ["invoice_number", "reason"],
        "additionalProperties": False,
    },
}


def extract(client: anthropic.Anthropic, text: str, max_tokens: int = 2048) -> Optional[Invoice]:
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": "Extract this invoice. Categories: %s.\n\n%s"
                   % (", ".join(CATEGORIES), text)}],
        output_format=Invoice,
    )
    reason = resp.stop_reason
    if reason == "end_turn":
        inv = resp.parsed_output
        for li in inv.line_items:  # enum/const casing is not guaranteed
            li.category = li.category.lower() if li.category.lower() in CATEGORIES else "other"
        return inv
    if reason == "max_tokens" and max_tokens < 16000:
        return extract(client, text, max_tokens * 4)  # truncated JSON never matches the schema
    if reason == "refusal":
        d = resp.stop_details
        print("refused: category=%s explanation=%s" % (d.category, d.explanation))  # display, don't parse
        return None
    if reason == "model_context_window_exceeded":
        print("input too large: chunk the document")
        return None
    print("unhandled stop_reason:", reason)
    return None


def reconcile(client: anthropic.Anthropic, inv: Invoice) -> None:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[FLAG_TOOL],
        output_config={"format": {"type": "json_schema", "schema": {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}, "note": {"type": "string"}},
            "required": ["ok", "note"],
            "additionalProperties": False,
        }}},
        messages=[{"role": "user", "content": "Check the totals; flag if they don't add up.\n"
                   + inv.model_dump_json()}],
    )
    for b in resp.content:
        if b.type == "tool_use":
            # Strict: b.input is guaranteed to match FLAG_TOOL's schema. Execute, then send a
            # tool_result and read the final JSON answer from the next response.
            print("FLAG", b.input)
        elif b.type == "text":
            print("verdict", b.text)


if __name__ == "__main__":
    src = open(sys.argv[1]).read() if len(sys.argv) > 1 else (
        "ACME Corp  INV-881  USD\n2x Laptop 2,400.00\nSupport plan 300.00\nTOTAL 2,750.00")
    c = anthropic.Anthropic()
    invoice = extract(c, src)
    if invoice:
        print(invoice.model_dump_json(indent=2))
        reconcile(c, invoice)
