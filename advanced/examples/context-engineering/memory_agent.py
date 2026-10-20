#!/usr/bin/env python3
"""Long-running API agent: context editing + memory tool, with a safe memory store.

- clear_thinking_20251015 + clear_tool_uses_20250919 (beta context-management-2025-06-27)
  clear old thinking and bulky tool results server-side once input passes a trigger.
- memory_20250818 lets Claude save what matters to /memories before results are cleared;
  this file implements the six memory commands against a local directory, with
  path-traversal protection and a size cap.
- read_file is a deliberately bulky local tool so clearing has something to clear.

Usage:
    export ANTHROPIC_API_KEY=...
    python3 memory_agent.py --task "Audit ./src for unsafe SQL and keep findings" --root ./src
    python3 memory_agent.py --task "..." --dry-run   # print request config, no API call

Requires: pip install anthropic
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

MODEL = "claude-opus-5-5"
BETAS = ["context-management-2025-06-27"]
MAX_FILE_BYTES = 64 * 1024  # cap a single memory file
VIEW_CHAR_CAP = 16000

CONTEXT_MANAGEMENT = {
    "edits": [
        # thinking strategy must come first when combining
        {"type": "clear_thinking_20251015", "keep": {"type": "thinking_turns", "value": 2}},
        {
            "type": "clear_tool_uses_20250919",
            "trigger": {"type": "input_tokens", "value": 60000},
            "keep": {"type": "tool_uses", "value": 4},
            "clear_at_least": {"type": "input_tokens", "value": 15000},
            "exclude_tools": ["memory"],  # never clear memory reads/writes
        },
    ]
}

TOOLS: List[Dict[str, Any]] = [
    {"type": "memory_20250818", "name": "memory"},
    {
        "name": "read_file",
        "description": "Read a text file under the project root. Returns the full file.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "path relative to root"}},
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List files under a directory relative to the project root (recursive, max 500).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
]

SYSTEM = (
    "You are auditing a codebase over many turns. Old tool results will be cleared from "
    "your context automatically. Before moving to the next file, record findings (file, line, "
    "issue, severity) in /memories/findings.md and your position in /memories/progress.md. "
    "Keep memory files short and organized; update rather than append duplicates."
)


class MemoryStore:
    """Client-side handler for memory_20250818. Maps /memories onto base_dir."""

    def __init__(self, base_dir: Path) -> None:
        self.base = base_dir.resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, vpath: str) -> Path:
        if "%2e" in vpath.lower() or "\\" in vpath:
            raise ValueError("Error: invalid path %s" % vpath)
        if vpath != "/memories" and not vpath.startswith("/memories/"):
            raise ValueError("Error: path must be under /memories")
        real = (self.base / vpath[len("/memories"):].lstrip("/")).resolve()
        try:
            real.relative_to(self.base)
        except ValueError:
            raise ValueError("Error: path escapes /memories")
        return real

    def handle(self, inp: Dict[str, Any]) -> str:
        cmd = inp.get("command")
        if cmd == "view":
            return self._view(inp["path"], inp.get("view_range"))
        if cmd == "create":
            p = self._resolve(inp["path"])
            text = inp.get("file_text", "")
            if len(text.encode()) > MAX_FILE_BYTES:
                raise ValueError("Error: file exceeds %d bytes; summarize instead" % MAX_FILE_BYTES)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)  # overwrite is an allowed implementation choice
            return "File created successfully at: %s" % inp["path"]
        if cmd == "str_replace":
            p = self._resolve(inp["path"])
            if not p.is_file():
                raise ValueError("Error: The path %s does not exist. Please provide a valid path." % inp["path"])
            text = p.read_text()
            old, new = inp["old_str"], inp.get("new_str", "")
            n = text.count(old)
            if n == 0:
                raise ValueError("No replacement was performed, old_str `%s` did not appear verbatim in %s." % (old, inp["path"]))
            if n > 1:
                lines = [str(i + 1) for i, l in enumerate(text.splitlines()) if old.splitlines()[0] in l]
                raise ValueError("No replacement was performed. Multiple occurrences of old_str `%s` in lines: %s. Please ensure it is unique" % (old, ", ".join(lines)))
            p.write_text(text.replace(old, new))
            return "The memory file has been edited."
        if cmd == "insert":
            p = self._resolve(inp["path"])
            if not p.is_file():
                raise ValueError("Error: The path %s does not exist" % inp["path"])
            lines = p.read_text().splitlines(True)
            at = int(inp["insert_line"])
            if at < 0 or at > len(lines):
                raise ValueError("Error: Invalid `insert_line` parameter: %d. It should be within the range of lines of the file: [0, %d]" % (at, len(lines)))
            lines.insert(at, inp["insert_text"])
            p.write_text("".join(lines))
            return "The file %s has been edited." % inp["path"]
        if cmd == "delete":
            p = self._resolve(inp["path"])
            if p == self.base:
                raise ValueError("Error: cannot delete /memories")
            if not p.exists():
                raise ValueError("Error: The path %s does not exist" % inp["path"])
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            return "Successfully deleted %s" % inp["path"]
        if cmd == "rename":
            src, dst = self._resolve(inp["old_path"]), self._resolve(inp["new_path"])
            if src == self.base:
                raise ValueError("Error: cannot rename /memories")
            if not src.exists():
                raise ValueError("Error: The path %s does not exist" % inp["old_path"])
            if dst.exists():
                raise ValueError("Error: The destination %s already exists" % inp["new_path"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            return "Successfully renamed %s to %s" % (inp["old_path"], inp["new_path"])
        raise ValueError("Error: unknown command %s" % cmd)

    def _view(self, vpath: str, view_range: Any) -> str:
        p = self._resolve(vpath)
        if p.is_dir():
            rows = ["Here're the files and directories up to 2 levels deep in %s, excluding hidden items and node_modules:" % vpath]
            for f in sorted(p.rglob("*")):
                rel = f.relative_to(p)
                if len(rel.parts) > 2 or any(part.startswith(".") for part in rel.parts):
                    continue
                size = f.stat().st_size if f.is_file() else 0
                rows.append("%.1fK\t%s/%s" % (size / 1024.0, vpath.rstrip("/"), rel.as_posix()))
            return "\n".join(rows)
        if not p.is_file():
            raise ValueError("The path %s does not exist. Please provide a valid path." % vpath)
        lines = p.read_text().splitlines()
        start, end = 1, len(lines)
        if view_range:
            start = int(view_range[0])
            end = len(lines) if int(view_range[1]) == -1 else int(view_range[1])
        body = "\n".join("%6d\t%s" % (i, lines[i - 1]) for i in range(start, end + 1) if 0 < i <= len(lines))
        return ("Here's the content of %s with line numbers:\n" % vpath + body)[:VIEW_CHAR_CAP]


def local_tool(name: str, inp: Dict[str, Any], root: Path) -> str:
    target = (root / inp.get("path", ".")).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError("path outside root")
    if name == "read_file":
        return target.read_text(errors="replace")
    if name == "list_files":
        files = [str(p.relative_to(root)) for p in target.rglob("*") if p.is_file()][:500]
        return "\n".join(files)
    raise ValueError("unknown tool %s" % name)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--memory-dir", default="./.agent-memory")
    ap.add_argument("--max-steps", type=int, default=80)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.dry_run:
        print(json.dumps({"model": MODEL, "betas": BETAS, "context_management": CONTEXT_MANAGEMENT,
                          "tools": [t.get("type", t["name"]) for t in TOOLS]}, indent=2))
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("set ANTHROPIC_API_KEY", file=sys.stderr)
        return 1

    import anthropic  # imported late so --dry-run works without the SDK

    client = anthropic.Anthropic()
    root = Path(args.root).resolve()
    memory = MemoryStore(Path(args.memory_dir))
    messages: List[Dict[str, Any]] = [{"role": "user", "content": args.task}]

    for step in range(args.max_steps):
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            betas=BETAS,
            context_management=CONTEXT_MANAGEMENT,
        )
        cm = getattr(resp, "context_management", None)
        for edit in (getattr(cm, "applied_edits", None) or []):
            print("[step %d] context edit: %s" % (step, edit))
        print("[step %d] input_tokens=%s stop=%s" % (step, resp.usage.input_tokens, resp.stop_reason))

        # Keep full, unmodified history client-side; the API edits its own copy.
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason != "tool_use":
            for block in resp.content:
                if block.type == "text":
                    print(block.text)
            return 0

        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            try:
                if block.name == "memory":
                    out = memory.handle(block.input)
                else:
                    out = local_tool(block.name, block.input, root)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
            except (ValueError, OSError, KeyError) as e:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": str(e), "is_error": True})
        messages.append({"role": "user", "content": results})
    print("max steps reached; state is in %s" % args.memory_dir)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
