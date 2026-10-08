"""Extract caption-reviewed game passages without regenerating speaker stills."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import unquote

GAME = Path(__file__).resolve().parent
ROOT = GAME.parent
OUTPUT = GAME / "assets" / "review-clips"


def load(name):
    return json.loads((GAME / name).read_text(encoding="utf-8"))


def probe(ffprobe, path):
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,codec_name,width,height", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error("Use 1 to 4 workers.")
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise SystemExit("FFmpeg and FFprobe must be available on PATH.")
    talks = {t["id"]: t for t in load("talks.json")}
    review = load("talk-review.json")
    durations = {t["talkId"]: t["duration"] for t in load("media-audit.json")["sourceTalks"]}
    old_path = GAME / "clip-library.json"
    previous = {c["id"]: c for c in load("clip-library.json")["clips"]} if old_path.exists() else {}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    work = [(r, p) for r in review["talks"] for p in r["passages"]]
    assert len({p["id"] for _, p in work}) == len(work), "Duplicate clip IDs"
    for r, p in work:
        assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", p["id"]), "Invalid clip ID"
        assert 0 <= p["start"] < p["end"] <= durations[r["talkId"]], p["id"]
    for row in review["talks"]:
        caption = (GAME / unquote(talks[row["talkId"]]["captions"])).resolve()
        if hashlib.sha256(caption.read_bytes()).hexdigest() != row["captionSha256"]:
            raise ValueError(f"Caption source changed since review: {row['talkId']}")

    def extract(row, passage):
        talk = talks[row["talkId"]]
        source = (GAME / unquote(talk["video"])).resolve()
        if not source.is_file() or source.parent.parent != ROOT / "talks":
            raise ValueError(f"Invalid talk source: {source}")
        source_stat = source.stat()
        fingerprint = hashlib.sha256(json.dumps([talk["id"], source_stat.st_size, source_stat.st_mtime_ns, passage["start"], passage["end"], "720p-crf25-aac96-v1"]).encode()).hexdigest()
        destination = OUTPUT / f"{passage['id']}-{fingerprint[:12]}.mp4"
        cached = previous.get(passage["id"], {})
        if not destination.exists() or cached.get("sourceFingerprint") != fingerprint:
            temporary = OUTPUT / f"{passage['id']}-{fingerprint[:12]}.partial.mp4"
            try:
                subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(passage["start"]), "-i", str(source), "-t", str(passage["end"] - passage["start"]), "-map", "0:v:0", "-map", "0:a:0", "-vf", "scale=-2:720", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-threads", "2", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(temporary)], check=True, capture_output=True, text=True)
                check = probe(ffprobe, temporary)
                stream_types = {s["codec_type"] for s in check["streams"]}
                if not {"audio", "video"} <= stream_types or abs(float(check["format"]["duration"]) - (passage["end"] - passage["start"])) > 0.25:
                    raise ValueError(f"Clip stream/duration check failed: {passage['id']}")
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
        check = probe(ffprobe, destination)
        actual_duration = float(check["format"]["duration"])
        if not {"audio", "video"} <= {s["codec_type"] for s in check["streams"]} or abs(actual_duration - (passage["end"] - passage["start"])) > 0.25:
            raise ValueError(f"Existing clip stream/duration check failed: {passage['id']}")
        return {
            **passage, "talkId": talk["id"], "speaker": talk["speaker"], "label": talk["label"],
            "qualifications": row["qualifications"],
            "sessionId": talk["sessionId"], "session": talk["session"],
            "sourceVideo": talk["video"], "sourceCaptions": talk["captions"],
            "path": destination.relative_to(GAME).as_posix(), "duration": actual_duration,
            "sourceFingerprint": fingerprint, "mediaVerified": True,
            "audioContentVerified": False,
        }

    results = []
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(extract, r, p): p["id"] for r, p in work}
        for future in as_completed(futures):
            clip_id = futures[future]
            try:
                results.append(future.result())
                print(f"[{len(results)}/{len(work)}] {clip_id}", flush=True)
            except Exception as error:
                failures.append(f"{clip_id}: {error}")
    if failures:
        raise SystemExit("Clip extraction failed; library was not replaced:\n" + "\n".join(failures))
    order = {p["id"]: i for i, (_, p) in enumerate(work)}
    results.sort(key=lambda c: order[c["id"]])
    library = {"schemaVersion": 1, "reviewedDate": review["reviewedDate"], "status": "Caption-reviewed candidate excerpts; streams and durations verified. Exact wording and final edit listening remain unverified.", "topics": review["topics"], "sessions": load("sessions.json")["sessions"], "clips": results}
    staged_library = old_path.with_suffix(".partial.json")
    staged_library.write_text(json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staged_library.replace(old_path)
    print(f"Prepared {len(results)} reviewed clips from {len({c['talkId'] for c in results})} addresses.")


if __name__ == "__main__":
    main()
