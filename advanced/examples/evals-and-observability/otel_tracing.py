#!/usr/bin/env python3
"""Trace Claude SDK calls inside your own spans and ship them over OTLP/HTTP.

  pip install anthropic opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
  export ANTHROPIC_API_KEY=...
  export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318   # collector (see otel-collector.yaml)
  export OTEL_SERVICE_NAME=support-bot
  python3 otel_tracing.py --console "What's your refund window?"   # print spans locally
  python3 otel_tracing.py --content --conversation conv_42 "..."   # include prompts/responses

The SDK emits anthropic.messages.create (CLIENT) spans under whatever span is
current, and propagates traceparent so API-side spans (if you added a Console
destination) join the same trace. Beta: pin your SDK version.
"""
from __future__ import annotations

import argparse
import sys

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)


def build_provider(console: bool) -> TracerProvider:
    # Resource.create() also reads OTEL_SERVICE_NAME / OTEL_RESOURCE_ATTRIBUTES.
    provider = TracerProvider(resource=Resource.create({}))
    if console:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    else:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        # Reads OTEL_EXPORTER_OTLP_ENDPOINT / _HEADERS from the environment.
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)  # register BEFORE the first SDK call
    return provider


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--console", action="store_true", help="print spans instead of exporting")
    ap.add_argument("--content", action="store_true",
                    help="content_mode=content: spans carry prompts and responses")
    ap.add_argument("--conversation", help="gen_ai.conversation.id (exported in both modes: no PII)")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--feature", default="support_reply", help="your own span attribute")
    args = ap.parse_args()

    provider = build_provider(args.console)
    from anthropic import Anthropic  # after the provider is registered

    otel_opts = {"tracer_provider": provider,
                 "traces": {"content_mode": "content" if args.content else "metadata_only"}}
    if args.conversation:
        otel_opts["conversation_id"] = args.conversation
    client = Anthropic(open_telemetry=otel_opts)

    tracer = trace.get_tracer("support-bot")
    # Your span: carries the business context the SDK can't know.
    with tracer.start_as_current_span("answer_question") as span:
        span.set_attribute("app.feature", args.feature)
        span.set_attribute("app.prompt_version", "support_v3")
        msg = client.messages.create(
            model=args.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": args.question}],
        )
        span.set_attribute("app.stop_reason", msg.stop_reason or "")
        print("".join(b.text for b in msg.content if b.type == "text"))

    provider.shutdown()  # flush the batch processor before exit
    return 0


if __name__ == "__main__":
    sys.exit(main())
