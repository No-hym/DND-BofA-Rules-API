#!/usr/bin/env python3
"""Split legacy aggregated catalog files into one JSON file ("card") per record.

Before:  data/catalog/2024/weapon.json            (one array, many records)
After:   data/catalog/2024/weapon/<record>.json   (one record object per file)

The catalog build (scripts/ingest/pipeline.py) already writes cards; this
utility only migrates catalogs produced by older tooling. It is idempotent:
running it on an already split catalog is a no-op.

    python3 scripts/split_catalog_cards.py [--dir data/catalog] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ingest.cards import write_cards  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=Path("data/catalog"), help="catalog root directory")
    parser.add_argument("--dry-run", action="store_true", help="report what would change without writing")
    args = parser.parse_args()
    if not args.dir.is_dir():
        print(f"catalog directory not found: {args.dir}", file=sys.stderr)
        return 1
    total = 0
    for path in sorted(args.dir.rglob("*.json")):
        if path.name.endswith(".schema.json"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            continue
        if args.dry_run:
            print(f"{path} -> {path.with_suffix('')}/ ({len(data)} cards)")
            total += len(data)
        else:
            total += write_cards(path.with_suffix(""), data)
            print(f"{path} -> {path.with_suffix('')}/ ({len(data)} cards)")
    print(f"{'would split' if args.dry_run else 'split'} {total} records into individual card files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
