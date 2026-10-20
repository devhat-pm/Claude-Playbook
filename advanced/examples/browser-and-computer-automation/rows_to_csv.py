"""Merge extract_table.js output into a CSV that a Google Sheet (or Excel) imports cleanly.

Usage:
  python3 rows_to_csv.py page1.json page2.json --out leads.csv --key name
  - accepts one or more JSON files produced by extract_table.js (one per page)
  - de-duplicates on --key, keeps first-seen, adds source_url + scraped_at columns
  - neutralises spreadsheet formula injection (cells starting with = + - @ get a leading ')
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
from typing import Dict, List


def safe(cell: str) -> str:
    return "'" + cell if cell[:1] in ("=", "+", "-", "@") else cell


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--key", default=None, help="column used for de-duplication")
    a = ap.parse_args()

    columns: List[str] = []
    seen = set()
    out_rows: List[Dict[str, str]] = []
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if os.path.exists(a.out):  # append mode: keep what's there, extend de-dupe set
        with open(a.out, newline="") as f:
            for r in csv.DictReader(f):
                out_rows.append(r)
                if a.key:
                    seen.add(r.get(a.key))
            columns = list(out_rows[0].keys()) if out_rows else []

    for path in a.inputs:
        data = json.load(open(path))
        if "error" in data:
            print("skip %s: %s" % (path, data["error"]))
            continue
        cols = data["columns"]
        for c in cols + ["source_url", "scraped_at"]:
            if c not in columns:
                columns.append(c)
        for raw in data["rows"]:
            row = dict(zip(cols, raw))
            if a.key and row.get(a.key) in seen:
                continue
            if a.key:
                seen.add(row.get(a.key))
            row.update(source_url=data["url"], scraped_at=stamp)
            out_rows.append(row)

    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in out_rows:
            w.writerow({k: safe(str(r.get(k, "") or "")) for k in columns})
    print("wrote %d rows x %d cols -> %s" % (len(out_rows), len(columns), a.out))


if __name__ == "__main__":
    main()
