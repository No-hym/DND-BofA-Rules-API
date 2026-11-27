#!/usr/bin/env python3
"""Migrate a catalog to one JSON file ("card") per record, grouped by book.

Before:  data/catalog/2024/weapon.json            (one array, many records)
         data/catalog/2024/weapon/<record>.json   (flat cards)
After:   data/catalog/2024/srd-2024/weapon/<record>.json

i.e. ``data/catalog/<edition>/<book>/<category>/<record>.json`` — a separate
folder for every edition, every book or supplement, and every category. The
catalog build (scripts/ingest/pipeline.py) already writes this layout; this
utility only migrates catalogs produced by older tooling. It is idempotent:
running it on an already migrated catalog rewrites the same files.

    python3 scripts/split_catalog_cards.py [--dir data/catalog] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ingest.cards import read_records, write_catalog_cards  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=Path("data/catalog"), help="catalog root directory")
    parser.add_argument("--dry-run", action="store_true", help="report what would change without writing")
    args = parser.parse_args()
    if not args.dir.is_dir():
        print(f"catalog directory not found: {args.dir}", file=sys.stderr)
        return 1
    total = 0
    for edition_dir in sorted(path for path in args.dir.iterdir() if path.is_dir()):
        records = read_records(edition_dir)
        if not records:
            continue
        books = sorted({str(record["book_id"]) for record in records})
        print(f"{edition_dir}: {len(records)} records in {len(books)} book folders")
        total += len(records)
        if not args.dry_run:
            write_catalog_cards(edition_dir, records)
    print(f"{'would migrate' if args.dry_run else 'migrated'} {total} records into book/category card folders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
