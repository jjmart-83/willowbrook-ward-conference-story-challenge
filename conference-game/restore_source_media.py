"""Restore or verify original talk downloads from the project's release archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def destination_for(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative or not path.parts or path.parts[0] != "talks":
        raise ValueError(f"Invalid source path: {relative}")
    destination = root.joinpath(*path.parts).resolve()
    if not destination.is_relative_to((root / "talks").resolve()):
        raise ValueError(f"Source path escapes talks/: {relative}")
    return destination


def matches(path, record):
    return path.is_file() and path.stat().st_size == record["bytes"] and sha256(path) == record["sha256"]


def restore_talk(talk, root, archive_dir, verify_only=False):
    files = [(record, destination_for(root, record["path"])) for record in talk["files"]]
    for record, destination in files:
        if destination.exists() and not matches(destination, record):
            raise ValueError(f"Existing file differs from the archive: {destination}. Restore to an empty folder to compare.")
    missing = [(record, destination) for record, destination in files if not destination.exists()]
    if verify_only:
        if missing:
            raise FileNotFoundError(f"{talk['id']}: {len(missing)} source files missing")
        return
    if missing:
        asset = talk["archive"]
        if Path(asset["assetName"]).name != asset["assetName"]:
            raise ValueError("Invalid release asset name")
        archive = archive_dir / asset["assetName"]
        archive_dir.mkdir(parents=True, exist_ok=True)
        if not archive.exists():
            partial = archive.with_suffix(archive.suffix + ".partial")
            request = urllib.request.Request(asset["url"], headers={"User-Agent": "Conference-Story-Challenge-Source-Restore"})
            try:
                with urllib.request.urlopen(request, timeout=60) as incoming, partial.open("wb") as outgoing:
                    for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                        outgoing.write(chunk)
                if not matches(partial, asset):
                    raise ValueError(f"Downloaded archive failed its SHA-256 check: {asset['assetName']}")
                partial.replace(archive)
            finally:
                partial.unlink(missing_ok=True)
        if not matches(archive, asset):
            raise ValueError(f"Archive failed its SHA-256 check: {archive}")
        with zipfile.ZipFile(archive) as bundle:
            if set(bundle.namelist()) != {record["path"] for record, _ in files} or len(bundle.namelist()) != len(files):
                raise ValueError(f"Archive file list does not match the manifest: {archive}")
            for record, destination in missing:
                destination.parent.mkdir(parents=True, exist_ok=True)
                partial = destination.with_name(destination.name + ".partial")
                try:
                    with bundle.open(record["path"]) as incoming, partial.open("wb") as outgoing:
                        for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                            outgoing.write(chunk)
                    if not matches(partial, record):
                        raise ValueError(f"Restored file failed its SHA-256 check: {destination}")
                    partial.replace(destination)
                finally:
                    partial.unlink(missing_ok=True)
    # Clip caches use source timestamps; restore those as well as the bytes.
    for record, destination in files:
        if record.get("mtimeNs"):
            os.utime(destination, ns=(destination.stat().st_atime_ns, record["mtimeNs"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=HERE / "source-media-manifest.json")
    parser.add_argument("--destination", type=Path, default=ROOT, help="Workspace root; files restore beneath talks/.")
    parser.add_argument("--archive-dir", type=Path, default=ROOT / ".qa" / "source-archive")
    parser.add_argument("--talks", nargs="+", help="Optional talk IDs to restore or verify.")
    parser.add_argument("--verify-only", action="store_true", help="Check current files without downloading or changing them.")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1:
        raise ValueError("Unsupported source archive manifest")
    talks = manifest["talks"]
    if args.talks:
        known = {talk["id"] for talk in talks}
        if set(args.talks) - known:
            parser.error("Unknown talk ID")
        talks = [talk for talk in talks if talk["id"] in args.talks]
    for index, talk in enumerate(talks, 1):
        restore_talk(talk, args.destination.resolve(), args.archive_dir.resolve(), args.verify_only)
        print(f"[{index}/{len(talks)}] {'Verified' if args.verify_only else 'Restored/verified'} {talk['id']}", flush=True)


if __name__ == "__main__":
    main()
