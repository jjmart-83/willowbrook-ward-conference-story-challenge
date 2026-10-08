"""Package original JDownloader2 downloads as one verifiable release ZIP per talk."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPOSITORY = "jjmart-83/willowbrook-ward-conference-story-challenge"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_archive(folder, destination, root):
    files = []
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_STORED, allowZip64=True) as bundle:
        for source in sorted(folder.rglob("*")):
            if not source.is_file():
                continue
            if source.is_symlink() or not source.resolve().is_relative_to(folder.resolve()):
                raise ValueError(f"Unexpected source link: {source}")
            relative = source.relative_to(root).as_posix()
            stat = source.stat()
            digest = hashlib.sha256()
            info = zipfile.ZipInfo.from_file(source, arcname=relative)
            with source.open("rb") as incoming, bundle.open(info, "w", force_zip64=True) as outgoing:
                for chunk in iter(lambda: incoming.read(1024 * 1024), b""):
                    outgoing.write(chunk)
                    digest.update(chunk)
            files.append({"path": relative, "bytes": stat.st_size,
                "sha256": digest.hexdigest(), "mtimeNs": stat.st_mtime_ns})
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conference", default="October 2026")
    parser.add_argument("--tag", default="october-2026-project-archive")
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".qa" / "source-archive")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", args.tag):
        parser.error("Use a simple release tag without slashes.")
    talks = json.loads((HERE / "talks.json").read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"schemaVersion": 1, "conference": args.conference,
        "downloadTool": "JDownloader2", "downloadToolEvidence": "Reported by the activity organizer on October 7, 2026.",
        "repository": REPOSITORY, "releaseTag": args.tag, "talks": []}
    ffprobe = shutil.which("ffprobe")
    for index, talk in enumerate(talks, 1):
        folder = (ROOT / "talks" / talk["folder"]).resolve()
        if not folder.is_relative_to((ROOT / "talks").resolve()) or not folder.is_dir():
            raise ValueError(f"Missing or invalid source folder: {talk['folder']}")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", talk["id"]):
            raise ValueError("Invalid talk ID")
        asset_name = f"source-{talk['id']}.zip"
        archive = args.output_dir / asset_name
        files = create_archive(folder, archive, ROOT.resolve())
        video = next(folder.glob("*.mp4"))
        source_url = None
        if ffprobe:
            info = json.loads(subprocess.run([ffprobe, "-v", "error", "-show_entries",
                "format_tags=comment", "-of", "json", str(video)], check=True, capture_output=True, text=True).stdout)
            comment = info.get("format", {}).get("tags", {}).get("comment", "")
            if comment.startswith(("https://www.youtube.com/", "https://youtube.com/", "https://youtu.be/")):
                source_url = comment
        manifest["talks"].append({"id": talk["id"], "speaker": talk["speaker"],
            "youtubeUrl": source_url, "files": files, "archive": {"assetName": asset_name,
            "bytes": archive.stat().st_size, "sha256": sha256(archive),
            "url": f"https://github.com/{REPOSITORY}/releases/download/{args.tag}/{asset_name}"}})
        print(f"[{index}/{len(talks)}] {asset_name}: {len(files)} files, {archive.stat().st_size / 1e6:.1f} MB", flush=True)
    manifest["totalFiles"] = sum(len(talk["files"]) for talk in manifest["talks"])
    manifest["totalBytes"] = sum(file["bytes"] for talk in manifest["talks"] for file in talk["files"])
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (HERE / "source-media-manifest.json").write_text(text, encoding="utf-8")
    (args.output_dir / "source-media-manifest.json").write_text(text, encoding="utf-8")
    urls = [talk["youtubeUrl"] for talk in manifest["talks"] if talk["youtubeUrl"]]
    (HERE / "source-youtube-links.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")
    print(f"Preserved {manifest['totalFiles']} source files and {len(urls)} YouTube links.")


if __name__ == "__main__":
    main()
