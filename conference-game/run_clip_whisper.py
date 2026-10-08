"""Transcribe prepared clips locally with Whisper.cpp; cache against actual media/model hashes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

GAME = Path(__file__).resolve().parent
AUDIT = GAME / "speech-audit"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    staged = path.with_suffix(".partial.json")
    staged.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staged.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, default=Path(r"C:\whisper-work\cuda\Release\whisper-cli.exe"))
    parser.add_argument("--model", type=Path, default=AUDIT / "models" / "ggml-base.en.bin")
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument("--threads", type=int, default=min(os.cpu_count() or 4, 8))
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--clips", nargs="+")
    parser.add_argument("--recheck", action="store_true")
    parser.add_argument("--prototype", action="store_true", help="Transcribe the separately indexed original 20 clips.")
    args = parser.parse_args()
    if args.batch_size < 1 or args.threads < 1:
        parser.error("Batch size and threads must be positive.")
    if not args.engine.is_file() or not args.model.is_file():
        parser.error("Whisper executable and model must exist.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        parser.error("FFmpeg is required.")
    clips = read(AUDIT / "prototype-input.json")["clips"] if args.prototype else read(GAME / "clip-library.json")["clips"]
    if args.clips:
        requested = set(args.clips)
        if requested - {c["id"] for c in clips}:
            parser.error("Unknown clip ID.")
        clips = [c for c in clips if c["id"] in requested]
    output = AUDIT / ("rechecks" if args.recheck else "raw")
    audio = AUDIT / "audio"
    logs = AUDIT / "logs"
    for folder in [output, audio, logs]:
        folder.mkdir(parents=True, exist_ok=True)
    version = subprocess.run([str(args.engine), "--version"], capture_output=True, text=True, check=True).stdout.strip()
    model_sha = sha(args.model)
    pending = []
    metadata = {}
    for clip in clips:
        media = (GAME / clip["path"]).resolve()
        allowed = GAME / "assets" / ("clips" if args.prototype else "review-clips")
        if not media.is_relative_to(allowed):
            raise ValueError("Clip must be inside the prepared review library.")
        meta = {
            "clipId": clip["id"], "clipSha256": sha(media), "sourceFingerprint": clip["sourceFingerprint"],
            "model": str(args.model.resolve()), "modelSha256": model_sha, "engine": str(args.engine),
            "engineVersion": version, "backend": "cpu" if args.cpu else "cuda", "language": "en",
            "initialPrompt": None, "maxContext": 0, "threads": args.threads,
            "status": "Independent machine transcription; not a human listening audit.",
        }
        metadata[clip["id"]] = meta
        transcript = output / f"{clip['id']}.json"
        meta_path = output / f"{clip['id']}.meta.json"
        if transcript.exists() and meta_path.exists():
            previous = read(meta_path)
            if all(previous.get(k) == meta[k] for k in ["clipId", "sourceFingerprint", "clipSha256", "modelSha256", "engineVersion", "language", "initialPrompt", "maxContext"]):
                if isinstance(read(transcript).get("transcription"), list):
                    continue
        wav = audio / f"{clip['id']}.wav"
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(media), "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)], capture_output=True, check=True)
        pending.append(clip)
    print(f"{len(clips) - len(pending)}/{len(clips)} cached; transcribing {len(pending)} with {args.model.name} ({'CPU' if args.cpu else 'CUDA'}).", flush=True)
    completed = len(clips) - len(pending)
    for offset in range(0, len(pending), args.batch_size):
        batch = pending[offset:offset + args.batch_size]
        command = [str(args.engine), "-m", str(args.model.resolve()), "-l", "en", "-t", str(args.threads), "-mc", "0", "-otxt", "-osrt", "-ojf"]
        if args.cpu:
            command.append("-ng")
        # Whisper.cpp accepts repeated input and output options in matching order.
        for clip in batch:
            command += ["-f", str(audio / f"{clip['id']}.wav"), "-of", str(output / clip["id"])]
        logfile = logs / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{offset:03d}.log"
        with logfile.open("w", encoding="utf-8") as log:
            run_started = time.time_ns()
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            done = set()
            while True:
                for clip in batch:
                    cid = clip["id"]
                    if cid in done:
                        continue
                    path = output / f"{cid}.json"
                    # A prior result may be present while this run regenerates it.
                    if not path.exists() or path.stat().st_mtime_ns < run_started:
                        continue
                    try:
                        result = read(path)
                        if not isinstance(result.get("transcription"), list):
                            continue
                        if Path(result.get("params", {}).get("model", "")).resolve() != args.model.resolve():
                            continue
                    except (OSError, json.JSONDecodeError):
                        continue
                    write(output / f"{cid}.meta.json", {**metadata[cid], "transcribedAt": datetime.now(timezone.utc).isoformat()})
                    done.add(cid)
                    completed += 1
                    print(f"[{completed}/{len(clips)}] {cid}", flush=True)
                if process.poll() is not None:
                    break
                time.sleep(.5)
            if process.returncode or len(done) != len(batch):
                raise RuntimeError(f"Whisper failed or did not complete the batch; inspect {logfile} (exit {process.returncode}).")
        for clip in batch:
            wav = audio / f"{clip['id']}.wav"
            if wav.resolve().is_relative_to(AUDIT):
                wav.unlink(missing_ok=True)
    print(f"Finished {len(clips)} local Whisper transcriptions.", flush=True)


if __name__ == "__main__":
    main()
