#!/usr/bin/env python3
"""Source synchronization and catalog build CLI for DND-BofA Rules API.

All network access is confined to the explicit allowlist below and is only
used by this ETL/CLI. The Go REST API never calls external services.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.ingest import pipeline  # noqa: E402
from scripts.ingest.report import write_report  # noqa: E402
from scripts.ingest.machine_translate import translate_catalog  # noqa: E402

ALLOWED_HOSTS = {"codeload.github.com", "www.5esrd.com", "a5esrd.com", "api.github.com"}


def _download(url: str) -> bytes:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"refusing to download from {url}: host is not allowlisted")
    request = urllib.request.Request(url, headers={"User-Agent": "DND-BofA-Rules-Importer/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _fetch(args: argparse.Namespace) -> None:
    config = pipeline.load_config()
    root = REPO / "data" / "original"
    root.mkdir(parents=True, exist_ok=True)
    for source in config["sources"]:
        if not source.get("commit"):
            continue
        repo_path = "/".join(source["url"].removeprefix("https://github.com/").split("/")[:2])
        url = f"https://codeload.github.com/{repo_path}/tar.gz/{source['commit']}"
        target = root / source["id"]
        target.mkdir(parents=True, exist_ok=True)
        archive = io.BytesIO(_download(url))
        with tarfile.open(fileobj=archive, mode="r:gz") as tar:
            for member in tar.getmembers():
                parts = Path(member.name).parts
                if member.isdir() or not parts:
                    continue
                relative = Path(*parts[1:])
                if not relative.parts or any(part == ".." for part in relative.parts):
                    continue
                if source["id"] == "open5e-api" and not str(relative).startswith(("data/v1/", "data/v2/", "LICENSE")):
                    continue
                if source["id"] == "srd-ru" and not str(relative).startswith("docs/"):
                    continue
                if source["id"] not in ("open5e-api", "srd-ru") and not str(relative).startswith("src/dnd/"):
                    continue
                if member.size > 20_000_000:
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                destination = target / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(extracted.read())
        print(f"fetched {source['id']} @ {source['commit'][:12]} -> {target}")
    for source in config["sources"]:
        if source.get("adapter") not in ("site5esrd", "sitea5esrd"):
            continue
        directory = root / ("5esrd" if source["adapter"] == "site5esrd" else "a5esrd")
        directory.mkdir(parents=True, exist_ok=True)
        for index, url in enumerate(source.get("entry_points", [])):
            try:
                html = _download(url).decode("utf-8", errors="replace")
            except Exception as exc:  # network failures must not break the whole build
                print(f"warning: could not fetch {url}: {exc}", file=sys.stderr)
                continue
            (directory / f"index-{index}.html").write_text(html, encoding="utf-8")
        print(f"fetched {source['id']} site index -> {directory}")


def _build(args: argparse.Namespace) -> None:
    manifest = pipeline.build(Path(args.snapshot_root), Path(args.legacy_root) if args.legacy_root else None,
                              args.version)
    write_report(manifest)
    print(f"built catalog v{manifest['version']}: {manifest['counts']['entities']} entities, "
          f"{manifest['counts']['translated']} with RU translation")


def _translate(args: argparse.Namespace) -> None:
    root = REPO / "data"
    if not args.endpoint.startswith("https://") and not args.endpoint.startswith("http://localhost"):
        raise SystemExit("translation endpoint must use HTTPS or localhost")
    glossary_path = root / "translations" / "memory.json"
    glossary = {}
    if glossary_path.exists():
        glossary = json.loads(glossary_path.read_text(encoding="utf-8")).get("glossary", {}).get("2024", {})
    count = translate_catalog(root, args.endpoint, args.model, args.edition, args.limit, glossary)
    print(f"machine-translated {count} records (status=machine, review required)")


def _verify(args: argparse.Namespace) -> None:
    from scripts.ingest.validate import validate_dirs
    problems = validate_dirs(Path(args.dir))
    if problems:
        for problem in problems[:50]:
            print(problem, file=sys.stderr)
        raise SystemExit(f"{len(problems)} validation problems")
    print("catalog layers valid")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="download pinned public snapshots (ETL only)")
    fetch.set_defaults(func=_fetch)
    build = sub.add_parser("build", help="build normalized/translated/catalog layers")
    build.add_argument("--snapshot-root", default=str(REPO / "data" / "original"))
    build.add_argument("--legacy-root", default="")
    build.add_argument("--version", default="")
    build.set_defaults(func=_build)
    machine = sub.add_parser("translate", help="fill RU gaps with an explicitly configured LLM")
    machine.add_argument("--endpoint", required=True)
    machine.add_argument("--model", required=True)
    machine.add_argument("--edition", default="2024", choices=["2014", "2024"])
    machine.add_argument("--limit", type=int, default=100)
    machine.set_defaults(func=_translate)
    verify = sub.add_parser("verify", help="validate generated layers")
    verify.add_argument("--dir", default=str(REPO / "data"))
    verify.set_defaults(func=_verify)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
