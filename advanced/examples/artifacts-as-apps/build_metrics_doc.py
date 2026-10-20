#!/usr/bin/env python3
"""Turn a metrics CSV into the JSON document a scheduled task writes to an
artifact's db (ArtifactData `set`/`update` with `file_path`).

Deterministic and idempotent: the same CSV for the same ISO week produces the
same document (except generated_at), and the doc carries `run_key` so the task
can skip a write when the stored doc already has this week's key.

Usage:
  python3 build_metrics_doc.py metrics.csv out/weekly.json
  python3 build_metrics_doc.py metrics.csv out/weekly.json --week 2026-W42

CSV columns: label,value   (value numeric; extra columns ignored)
"""
import argparse
import csv
import datetime as dt
import json
import sys
from typing import Dict, List

MAX_ROWS = 24


def iso_week(today: dt.date) -> str:
    year, week, _ = today.isocalendar()
    return "%d-W%02d" % (year, week)


def read_rows(path: str) -> List[Dict[str, object]]:
    rows = []  # type: List[Dict[str, object]]
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or "label" not in reader.fieldnames or "value" not in reader.fieldnames:
            raise ValueError("CSV needs 'label' and 'value' columns")
        for i, rec in enumerate(reader, start=2):
            label = (rec.get("label") or "").strip()
            raw = (rec.get("value") or "").strip().replace(",", "")
            if not label:
                continue
            try:
                value = float(raw)
            except ValueError:
                raise ValueError("line %d: value %r is not numeric" % (i, raw))
            rows.append({"label": label[:60], "value": int(value) if value.is_integer() else round(value, 2)})
    if not rows:
        raise ValueError("CSV has no data rows")
    return rows[:MAX_ROWS]


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv_path")
    ap.add_argument("out_path")
    ap.add_argument("--week", help="ISO week like 2026-W42; defaults to the current week (UTC)")
    args = ap.parse_args(argv)

    now = dt.datetime.now(dt.timezone.utc)
    week = args.week or iso_week(now.date())
    try:
        rows = read_rows(args.csv_path)
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    doc = {
        "week": week,
        "run_key": "weekly-metrics:%s" % week,
        "generated_at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "rows": rows,
    }
    with open(args.out_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps({"ok": True, "run_key": doc["run_key"], "rows": len(rows)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
