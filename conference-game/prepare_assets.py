from __future__ import annotations

import difflib
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import quote


GAME_DIR = Path(__file__).resolve().parent
ROOT_DIR = GAME_DIR.parent
TALK_DIR = ROOT_DIR / "talks"
IMAGE_DIR = GAME_DIR / "assets" / "speakers"
CLIP_DIR = GAME_DIR / "assets" / "clips"
PROBE_SECONDS = 90

# Used only as a fallback when OCR cannot read a lower-third. The probe still
# examines the video first and the resulting report marks this image for review.
STILL_HINTS = {"vaiangina-sikahema": 29}

# One-off visual choices take precedence over automatic selection for these talks.
STILL_OVERRIDES = {"hutch-u-fale": 10.0}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value or "speaker"


def assign_talk_ids(entries: list[dict], existing_talks: list[dict]) -> None:
    """Preserve published IDs and give additional addresses their own assets."""
    known = {talk["folder"]: talk["id"] for talk in existing_talks}
    reserved = set(known.values())
    assigned = set()
    for entry in entries:
        if entry["folder"] in known:
            talk_id = known[entry["folder"]]
        else:
            base = slugify(entry["speaker"])
            talk_id = base
            if talk_id in reserved:
                parts = entry["folder"].split(chr(166))
                detail = " ".join(part.strip() for part in parts[2:])
                suffix = slugify(detail or entry["folder"])
                candidate = f"{base}-{suffix}"
                talk_id = candidate
                number = 2
                while talk_id in reserved:
                    talk_id = f"{candidate}-{number}"
                    number += 1
        if talk_id in assigned:
            raise ValueError(f"Duplicate talk ID in the existing inventory: {talk_id}")
        entry["id"] = talk_id
        assigned.add(talk_id)
        reserved.add(talk_id)


def url_path(path: Path) -> str:
    relative = Path("..") / path.relative_to(ROOT_DIR)
    return "/".join(quote(part, safe="") for part in relative.as_posix().split("/"))


def words(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", text)


def score_frame(speaker: str, text: str, second: float) -> dict:
    expected = [word for word in words(speaker) if len(word) >= 4]
    recognized = words(text)
    thresholds = {wanted: (0.80 if len(wanted) < 6 else 0.76) for wanted in expected}
    matched = {}
    for wanted in expected:
        best = max((difflib.SequenceMatcher(None, wanted, seen).ratio() for seen in recognized), default=0)
        if best >= thresholds[wanted]:
            matched[wanted] = best

    extras = [
        seen for seen in recognized
        if len(seen) >= 3 and all(
            difflib.SequenceMatcher(None, wanted, seen).ratio() < thresholds[wanted]
            for wanted in expected
        )
    ]
    lines = [line for line in text.splitlines() if words(line)]
    complete = bool(expected) and len(matched) == len(expected)
    title_visible = len(extras) >= 2 or (len(lines) >= 2 and len(extras) >= 1)
    return {
        "second": second,
        "text": text.strip(),
        "matches": len(matched),
        "expected": len(expected),
        "complete": complete,
        "titleVisible": title_visible,
        "extras": len(extras),
        "rank": (len(matched), int(complete), int(title_visible), len(extras), -second),
    }


def choose_stable_candidate(candidates: list[dict], max_gap: float = 1.25) -> dict:
    """Prefer the middle of the longest repeated OCR run, then the earliest on ties."""
    ordered = sorted(candidates, key=lambda item: item["second"])
    clusters = []
    for candidate in ordered:
        if not clusters or candidate["second"] - clusters[-1][-1]["second"] > max_gap:
            clusters.append([candidate])
        else:
            clusters[-1].append(candidate)

    stable = max(clusters, key=lambda cluster: (len(cluster), -cluster[0]["second"]))
    cluster = stable if len(stable) >= 2 else clusters[0]
    midpoint = (cluster[0]["second"] + cluster[-1]["second"]) / 2
    return max(
        cluster,
        key=lambda item: (*item["rank"][:4], -abs(item["second"] - midpoint)),
    )


def format_time(second: float) -> str:
    whole = round(second)
    if abs(second - whole) < 0.01:
        return f"{whole // 60}:{whole % 60:02d}"
    minutes = int(second // 60)
    return f"{minutes}:{second - minutes * 60:05.2f}"


def make_review_sheet(entry: dict, candidates: list[dict]) -> str:
    from PIL import Image, ImageDraw, ImageFont

    review_dir = IMAGE_DIR / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    path = review_dir / f"{entry['id']}-candidates.jpg"
    selected = sorted(candidates, key=lambda item: item["rank"], reverse=True)[:6]
    if not selected:
        return ""

    cell_w, image_h, caption_h = 440, 248, 58
    sheet = Image.new("RGB", (cell_w * 2, (image_h + caption_h) * ((len(selected) + 1) // 2)), "#f3f2ed")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for index, candidate in enumerate(selected):
        frame = Image.open(candidate["path"]).convert("RGB")
        frame.thumbnail((cell_w, image_h), Image.Resampling.LANCZOS)
        x = (index % 2) * cell_w
        y = (index // 2) * (image_h + caption_h)
        sheet.paste(frame, (x, y))
        label = f"{format_time(candidate['second'])}  name match {candidate['matches']}/{candidate['expected']}"
        ocr = unicodedata.normalize("NFKD", re.sub(r"\s+", " ", candidate["text"]))
        ocr = ocr.encode("ascii", "ignore").decode()[:90]
        draw.text((x + 5, y + image_h + 4), label, fill="#17333b", font=font)
        draw.text((x + 5, y + image_h + 23), ocr, fill="#526365", font=font)
    sheet.save(path, quality=88)
    return path.relative_to(GAME_DIR).as_posix()


def probe_speaker_frames(ffmpeg: str, entries: list[dict]) -> dict[str, dict]:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        raise SystemExit("Windows PowerShell is needed to OCR speaker title cards.")

    with tempfile.TemporaryDirectory(prefix="conference-speaker-probe-") as temporary:
        temp_dir = Path(temporary)
        manifest = []
        for entry in entries:
            frame_dir = temp_dir / entry["id"]
            frame_dir.mkdir()
            subprocess.run(
                [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(entry["video"]),
                    "-t", str(PROBE_SECONDS), "-vf", "fps=1,scale=1280:-2", "-q:v", "4",
                    str(frame_dir / "frame-%03d.jpg"),
                ],
                check=True,
            )
            frames = []
            for frame_path in sorted(frame_dir.glob("frame-*.jpg")):
                number = int(frame_path.stem.rsplit("-", 1)[-1])
                second = number - 1
                frames.append({"second": second, "path": str(frame_path.resolve())})
            manifest.append({"id": entry["id"], "frames": frames})

        def run_ocr(batch: list[dict], name: str) -> list[dict]:
            manifest_path = temp_dir / f"{name}-frames.json"
            output_path = temp_dir / f"{name}-ocr.json"
            manifest_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
            completed = subprocess.run(
                [
                    powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(GAME_DIR / "Probe-SpeakerFrames.ps1"), "-ManifestPath", str(manifest_path),
                    "-OutputPath", str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if completed.returncode != 0:
                details = completed.stderr.strip() or completed.stdout.strip()
                raise SystemExit(f"Windows OCR could not probe the video frames. {details}")
            return json.loads(output_path.read_text(encoding="utf-8-sig"))

        coarse_results = run_ocr(manifest, "coarse")
        coarse_by_id = {}
        for result in coarse_results:
            coarse_by_id.setdefault(result["id"], []).append(result)

        refine_manifest = []
        refine_paths = {}
        for entry in entries:
            coarse_frames = [
                score_frame(entry["speaker"], result.get("text", ""), float(result["second"]))
                for result in coarse_by_id.get(entry["id"], [])
            ]
            titled = [frame for frame in coarse_frames if frame["complete"] and frame["titleVisible"]]
            named = [frame for frame in coarse_frames if frame["complete"]]
            if titled:
                seed = choose_stable_candidate(titled)
            elif named:
                seed = choose_stable_candidate(named)
            elif entry["id"] in STILL_HINTS:
                seed = {"second": STILL_HINTS[entry["id"]]}
            else:
                partial = [frame for frame in coarse_frames if frame["matches"]]
                if not partial:
                    continue
                seed = max(partial, key=lambda frame: frame["rank"])

            start = max(0.0, float(seed["second"]) - 1.0)
            frame_dir = temp_dir / entry["id"] / "refined"
            frame_dir.mkdir()
            subprocess.run(
                [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.2f}",
                    "-i", str(entry["video"]), "-t", "4", "-vf", "fps=4,scale=1280:-2", "-q:v", "4",
                    str(frame_dir / "refined-%03d.jpg"),
                ],
                check=True,
            )
            frames = []
            for frame_path in sorted(frame_dir.glob("refined-*.jpg")):
                number = int(frame_path.stem.rsplit("-", 1)[-1])
                second = round(start + (number - 1) / 4, 2)
                frames.append({"second": second, "path": str(frame_path.resolve())})
                refine_paths.setdefault(entry["id"], {})[second] = str(frame_path.resolve())
            if frames:
                refine_manifest.append({"id": entry["id"], "frames": frames})

        refined_results = run_ocr(refine_manifest, "refined") if refine_manifest else []
        refined_by_id = {}
        for result in refined_results:
            refined_by_id.setdefault(result["id"], []).append(result)

        selected_by_id = {}
        for entry in entries:
            coarse_frames = []
            for result in coarse_by_id.get(entry["id"], []):
                candidate = score_frame(entry["speaker"], result.get("text", ""), float(result["second"]))
                candidate["path"] = next(
                    frame["path"] for talk in manifest if talk["id"] == entry["id"]
                    for frame in talk["frames"] if frame["second"] == int(candidate["second"])
                )
                coarse_frames.append(candidate)
            refined_frames = []
            for result in refined_by_id.get(entry["id"], []):
                candidate = score_frame(entry["speaker"], result.get("text", ""), float(result["second"]))
                candidate["path"] = refine_paths[entry["id"]][candidate["second"]]
                refined_frames.append(candidate)

            coarse_titled = [frame for frame in coarse_frames if frame["complete"] and frame["titleVisible"]]
            coarse_named = [frame for frame in coarse_frames if frame["complete"]]
            refined_titled = [frame for frame in refined_frames if frame["complete"] and frame["titleVisible"]]
            refined_named = [frame for frame in refined_frames if frame["complete"]]
            if entry["id"] in STILL_OVERRIDES:
                automatic = choose_stable_candidate(refined_titled) if refined_titled else None
                chosen = {
                    "second": STILL_OVERRIDES[entry["id"]],
                    "text": automatic["text"] if automatic else "",
                    "matches": automatic["matches"] if automatic else 0,
                    "expected": automatic["expected"] if automatic else 0,
                }
                status = "manual-time-override"
            elif refined_titled:
                chosen = choose_stable_candidate(refined_titled, max_gap=0.76)
                status = "name-and-title-detected"
            elif coarse_titled:
                chosen = choose_stable_candidate(coarse_titled)
                status = "name-and-title-detected"
            elif refined_named:
                chosen = choose_stable_candidate(refined_named, max_gap=0.76)
                status = "name-detected-title-unverified"
            elif coarse_named:
                chosen = choose_stable_candidate(coarse_named)
                status = "name-detected-title-unverified"
            elif entry["id"] in STILL_HINTS:
                hint = STILL_HINTS[entry["id"]]
                available = refined_frames or coarse_frames
                chosen = min(available, key=lambda frame: abs(frame["second"] - hint)) if available else None
                status = "manual-hint-review"
            else:
                frames_with_matches = refined_frames or coarse_frames
                partial = [frame for frame in frames_with_matches if frame["matches"]]
                chosen = max(partial, key=lambda frame: frame["rank"]) if partial else None
                status = "partial-name-review" if partial else "no-name-match-review"

            frames = refined_frames + coarse_frames
            if chosen is None and frames:
                chosen = min(frames, key=lambda frame: abs(frame["second"] - 4))
            if chosen is None:
                chosen = {
                    "second": 4,
                    "text": "",
                    "matches": 0,
                    "expected": len([word for word in words(entry["speaker"]) if len(word) >= 4]),
                }
            review_sheet = ""
            if status not in {"name-and-title-detected", "manual-time-override"}:
                review_sheet = make_review_sheet(entry, frames)
            still = IMAGE_DIR / f"{entry['id']}.jpg"
            copied_probe_frame = bool(chosen.get("path"))
            if copied_probe_frame:
                shutil.copyfile(chosen["path"], still)
            selected_by_id[entry["id"]] = {
                "second": chosen["second"],
                "text": chosen["text"],
                "status": status,
                "reviewSheet": review_sheet,
                "copiedProbeFrame": copied_probe_frame,
                "note": "Manual still-time choice" if status == "manual-time-override" else "",
            }
        return selected_by_id


def write_probe_report(entries: list[dict], selections: dict[str, dict]) -> None:
    lines = [
        "# Speaker title-card probe report",
        "",
        f"The preparation script sampled the first {PROBE_SECONDS} seconds at one frame per second, then rescanned each likely title-card moment at four frames per second. Windows OCR looks for each speaker's name plus title text; the exact image is saved from the middle of the longest repeated match, favoring a settled lower-third over its fade-in or fade-out.",
        "",
        "Rows marked `manual-time-override` use an intentional timestamp from `STILL_OVERRIDES`. Review any other row that does not say `name-and-title-detected`; candidate contact sheets are saved under `assets/speakers/review/`.",
        "",
        "| Speaker / address | Chosen frame | Result | OCR text |",
        "| :-- | --: | :-- | :-- |",
    ]
    for entry in entries:
        selection = selections[entry["id"]]
        ocr = re.sub(r"\s+", " ", selection["text"]).replace("|", "\\|")
        if selection.get("note"):
            ocr = f"{selection['note']}; OCR elsewhere in the probe: {ocr or 'no text'}"
        if selection["reviewSheet"]:
            ocr += f" · [candidate sheet]({selection['reviewSheet']})"
        lines.append(f"| {entry['label']} | {format_time(selection['second'])} | {selection['status']} | {ocr or 'No OCR text'} |")
    (GAME_DIR / "speaker_probe_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def discover_talks() -> list[dict]:
    """Find downloaded addresses under the workspace's talks folder."""
    if not TALK_DIR.is_dir():
        raise SystemExit(f"Talk source folder was not found: {TALK_DIR}")

    entries = []
    for folder in sorted(path for path in TALK_DIR.iterdir() if path.is_dir()):
        videos = sorted(folder.glob("*.mp4"))
        captions = sorted(folder.glob("*.English.srt"))
        if not videos or not captions:
            continue

        # Use the video's displayed name so OCR checks the same spelling as its lower-third.
        speaker = videos[0].name.split(chr(166), 1)[0].strip()
        folder_parts = folder.name.split(chr(166))
        detail = " / ".join(part.strip() for part in folder_parts[2:])
        description_file = next(iter(folder.glob("*(Description).txt")), None)
        description = ""
        if description_file:
            description = description_file.read_text(encoding="utf-8-sig", errors="replace").strip()
        entries.append({
            "id": slugify(speaker),
            "speaker": speaker,
            "label": f"{speaker} — {detail}" if detail else speaker,
            "folder": folder.name,
            "video": videos[0],
            "captionFile": captions[0],
            "description": description,
        })

    return entries


def main() -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg was not found. Install it, then rerun this script.")

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    CLIP_DIR.mkdir(parents=True, exist_ok=True)
    entries = discover_talks()

    inventory_path = GAME_DIR / "talks.json"
    existing_talks = json.loads(inventory_path.read_text(encoding="utf-8")) if inventory_path.exists() else []
    assign_talk_ids(entries, existing_talks)
    sessions_path = GAME_DIR / "sessions.json"
    session_by_talk = {}
    if sessions_path.exists():
        sessions = json.loads(sessions_path.read_text(encoding="utf-8"))["sessions"]
        session_by_talk = {
            talk_id: {
                "sessionId": session["id"],
                "session": session["label"],
                "sessionSource": session["sourceUrl"],
            }
            for session in sessions for talk_id in session["talkIds"]
        }

    print(f"Probing the first {PROBE_SECONDS} seconds of {len(entries)} talks for name-and-title frames…")
    selections = probe_speaker_frames(ffmpeg, entries)
    talks = []
    review_needed = []
    for entry in entries:
        selection = selections[entry["id"]]
        still = IMAGE_DIR / f"{entry['id']}.jpg"
        if not selection["copiedProbeFrame"]:
            result = subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(selection["second"]), "-i", str(entry["video"]), "-vf", "scale=1280:-2", "-frames:v", "1", "-q:v", "3", str(still)],
                check=False,
            )
            if result.returncode != 0 or not still.exists():
                print(f"Could not extract the selected speaker still for {entry['speaker']}.")
                continue
        talks.append({
            "id": entry["id"],
            "speaker": entry["speaker"],
            "label": entry["label"],
            "folder": entry["folder"],
            "video": url_path(entry["video"]),
            "captions": url_path(entry["captionFile"]),
            "image": f"assets/speakers/{still.name}",
            "imageTime": selection["second"],
            "imageStatus": selection["status"],
            "imageOcr": selection["text"],
            "description": entry["description"],
            **session_by_talk.get(entry["id"], {}),
        })
        if selection["status"] not in {"name-and-title-detected", "manual-time-override"}:
            review_needed.append(entry["speaker"])

    write_probe_report(entries, selections)
    output = GAME_DIR / "talks.json"
    output.write_text(json.dumps(talks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    talk_by_id = {talk["id"]: talk for talk in talks}
    activity = json.loads((GAME_DIR / "activity.json").read_text(encoding="utf-8"))
    clips = {}
    for quote_card in activity.get("quotes", []):
        talk = talk_by_id.get(quote_card["speakerId"])
        if not talk:
            print(f"Skipping clip {quote_card['id']}: speaker not found.")
            continue
        folder = TALK_DIR / talk["folder"]
        source_files = sorted(folder.glob("*.mp4"))
        if not source_files:
            continue
        source = source_files[0]
        duration = float(quote_card["end"]) - float(quote_card["start"])
        clip_name = f"{quote_card['id']}.mp4"
        clip_path = CLIP_DIR / clip_name
        result = subprocess.run(
            [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(quote_card["start"]), "-i", str(source), "-t", f"{duration:.3f}",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
                "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(clip_path),
            ],
            check=False,
        )
        if result.returncode != 0 or not clip_path.exists():
            print(f"Could not extract the quote clip {quote_card['id']}.")
            continue
        clips[quote_card["id"]] = {
            "path": f"assets/clips/{clip_name}",
            "duration": round(duration, 3),
        }

    clips_file = GAME_DIR / "clips.json"
    clips_file.write_text(json.dumps(clips, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    detected = sum(talk["imageStatus"] == "name-and-title-detected" for talk in talks)
    manual = sum(talk["imageStatus"] == "manual-time-override" for talk in talks)
    print(f"Prepared {len(talks)} talks, {detected} OCR-matched name-and-title stills, {manual} manually timed stills, and {len(clips)} short clips.")
    print(f"Talk inventory: {output}")
    print(f"Probe report: {GAME_DIR / 'speaker_probe_report.md'}")
    if review_needed:
        print("Manual image review needed: " + ", ".join(review_needed))


if __name__ == "__main__":
    main()
