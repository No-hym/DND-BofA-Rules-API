#!/usr/bin/env python3
"""Package a verified, versioned catalog for DND-BofA consumption.

The archive is deterministic: file mtimes are normalized and only published
layers/manifest are included. It is uploaded as a GitHub Release asset by the
sync workflow, so the main site never depends on this repository's source data.
"""

from __future__ import annotations

import argparse
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"


def package(version: str, output: Path) -> Path:
    manifest_path = DATA / "releases" / f"v{version}.json"
    if not manifest_path.exists():
        raise SystemExit(f"missing manifest {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        for directory in ("catalog", "releases"):
            for path in sorted((DATA / directory).rglob("*")):
                if not path.is_file() or path.name in ("latest.json", "LICENSE"):
                    continue
                if directory == "releases" and path.name not in {f"v{version}.json", "aliases.json"}:
                    continue
                info = tarfile.TarInfo(str(path.relative_to(DATA)))
                info.size = path.stat().st_size
                info.mtime = 0
                info.mode = 0o644
                archive.addfile(info, path.open("rb"))
        license_path = DATA / "catalog" / "2024" / "LICENSE"
        if license_path.exists():
            info = tarfile.TarInfo("catalog/2024/LICENSE")
            info.size = license_path.stat().st_size
            info.mtime = 0
            info.mode = 0o644
            archive.addfile(info, license_path.open("rb"))
        meta = {
            "version": version,
            "packaged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "entrypoint": "catalog/<edition>/<category>.json",
            "manifest": f"releases/v{version}.json",
            "aliases": "releases/aliases.json",
            "primary_edition": manifest["primary_edition"],
        }
        payload = json.dumps(meta, ensure_ascii=False, sort_keys=True).encode("utf-8")
        info = tarfile.TarInfo("catalog-release.json")
        info.size = len(payload)
        info.mtime = 0
        info.mode = 0o644
        import io
        archive.addfile(info, io.BytesIO(payload))
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", default="dist/catalog-release.tar.gz")
    args = parser.parse_args()
    path = package(args.version, Path(args.out))
    print(f"packaged {path.stat().st_size} bytes -> {path}")


if __name__ == "__main__":
    main()
