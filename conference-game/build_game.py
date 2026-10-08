"""Prepare the self-contained game content and a GitHub Pages upload package."""
import json
import math
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SITE = ROOT / "github-pages"


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8-sig"))


def prepare_previews(content):
    """Cache preview frames; skip opening fades without changing clip playback."""
    clips = {clip["path"]: clip for card in content["cards"] for clip in card["clips"]}
    clips[content["closingClip"]["path"]] = content["closingClip"]
    paths = sorted(clips)
    cache = HERE / "assets" / "clip-frames"
    cache.mkdir(parents=True, exist_ok=True)
    columns, rows = 4, math.ceil(len(paths) / 4)
    sheet = HERE / "assets" / "clip-previews.jpg"
    layout = cache / "layout.json"
    previous_layout = json.loads(layout.read_text()) if layout.exists() else None
    previous_offsets = {item["path"]: item["previewTime"] for item in (previous_layout or []) if isinstance(item, dict)}
    current_layout = [{"path": path, "previewTime": 2 if clips[path]["start"] < 2 else 0} for path in paths]
    frames = []
    for index, relative in enumerate(paths):
        source = HERE / relative
        frame = cache / (source.stem + ".jpg")
        offset = current_layout[index]["previewTime"]
        if not frame.exists() or frame.stat().st_mtime < source.stat().st_mtime or previous_offsets.get(relative) != offset:
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(offset), "-i", str(source),
                "-frames:v", "1", "-vf", "scale=320:180", "-q:v", "3", "-y", str(frame)],
                check=True, capture_output=True)
        frames.append(frame)
        clips[relative]["previewIndex"] = index
        if (index + 1) % 10 == 0:
            print(f"Prepared {index + 1}/{len(paths)} clip previews.", flush=True)
    if not sheet.exists() or previous_layout != current_layout or sheet.stat().st_mtime < max(frame.stat().st_mtime for frame in frames):
        with tempfile.TemporaryDirectory(prefix="conference-previews-") as temporary:
            for index, frame in enumerate(frames):
                shutil.copy2(frame, Path(temporary) / f"frame-{index:03}.jpg")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-framerate", "1",
                "-i", str(Path(temporary) / "frame-%03d.jpg"), "-vf", f"tile={columns}x{rows}",
                "-frames:v", "1", "-q:v", "3", "-y", str(sheet)], check=True, capture_output=True)
        layout.write_text(json.dumps(current_layout), encoding="utf-8")
    # A clip may occur on several cards; give every reference its tile position.
    for card in content["cards"]:
        for clip in card["clips"]:
            clip["previewIndex"] = paths.index(clip["path"])
            clip["previewTime"] = 2 if clip["start"] < 2 else 0
    content["closingClip"]["previewTime"] = 2 if content["closingClip"]["start"] < 2 else 0
    content["clipPreviewSheet"] = {"path": "assets/clip-previews.jpg", "columns": columns, "rows": rows}


def build_content():
    board = load("story-board.json")
    stories = {story["id"]: story for story in load("story-catalog.json")["stories"]}
    talks = {talk["id"]: talk for talk in load("talks.json")}
    clips = load("clip-library.json")["clips"]
    retellings = load("story-retellings.json")
    content = {"version": 1, "title": board["title"], "topics": board["topics"], "cards": []}
    for card in board["cards"]:
        story = stories[card["storyId"]]
        talk = talks[story["talkId"]]
        related = [clip for clip in clips if clip.get("storyId") == story["id"]]
        # Present the narrative first, with companion teaching/qualification cuts available.
        related.sort(key=lambda clip: (clip["kind"] != "story", clip["start"]))
        content["cards"].append({**card, "intro": retellings[card["id"]]["intro"],
            "retelling": retellings[card["id"]]["text"],
            "takeaway": retellings[card["id"]]["takeaway"],
            "context": retellings[card["id"]]["context"], "speaker": talk["speaker"],
            "session": talk["session"], "image": talk["image"], "sourceUrl": talk["sessionSource"],
            "clips": [{"id": clip["id"], "title": clip["title"], "path": clip["path"],
                "duration": clip["duration"], "start": clip["start"], "end": clip["end"]} for clip in related]})
        if not related:
            raise ValueError(f"No prepared video for {card['id']}")
    closing = next(clip for clip in clips if clip["id"] == "oaks-closing-study-ponder-act")
    content["closingClip"] = {key: closing[key] for key in ["title", "path", "duration", "start", "end", "speaker"]}
    content["practice"] = {"title": "A kinder reply", "retelling":
        "Alfred Kyungu invited people to notice harsh or contentious expressions and replace them with words that bring peace. Respectful words can still express a disagreement or a boundary.",
        "question": "A friend makes a mistake. Replace a harsh reply with one peaceful sentence that could help.",
        "answerCriteria": ["Use respectful words that show care and offer a constructive next step.",
            "For example: Let's work out how to fix this together. Many other responses can meet the same criteria."]}
    prepare_previews(content)
    (HERE / "game-content.js").write_text("/* Generated by build_game.py from the reviewed story board and retellings. */\n"
        + "window.CONFERENCE_CONTENT = " + json.dumps(content, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    return content


def package(content):
    SITE.mkdir(exist_ok=True)
    paths = {"index.html", "app.js", "styles.css", "game-core.js", "game-content.js", "favicon.svg", content["clipPreviewSheet"]["path"]}
    for card in content["cards"]:
        paths.add(card["image"])
        paths.update(clip["path"] for clip in card["clips"])
    paths.add(content["closingClip"]["path"])
    archive = ROOT / "Conference-Story-Challenge-GitHub-Pages.zip"
    # Remove only retired files recorded in our previous publishing package.
    if archive.exists():
        with zipfile.ZipFile(archive) as previous:
            retired = set(previous.namelist()) - paths - {"README.md", ".nojekyll"}
        for relative in retired:
            destination = (SITE / relative).resolve()
            if not destination.is_relative_to(SITE):
                raise ValueError(f"Invalid retired asset path: {relative}")
            if destination.is_file():
                destination.unlink()
    for relative in sorted(paths):
        source = (HERE / relative).resolve()
        destination = (SITE / relative).resolve()
        if not source.is_relative_to(HERE) or not destination.is_relative_to(SITE):
            raise ValueError(f"Invalid asset path: {relative}")
        if not source.is_file():
            raise FileNotFoundError(source)
        if source.stat().st_size >= 25 * 1024 * 1024:
            raise ValueError(f"Asset exceeds GitHub browser upload limit: {relative}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    (SITE / "README.md").write_text("# Willowbrook Ward Conference Story Challenge\n\n"
        "This project's publish_game.py builds and publishes this folder to gh-pages; main contains the full project. "
        "See Publish to GitHub Pages.md at the project root for updates.\n\n"
        "For a separate standalone repository, upload the contents of this folder to its root. "
        "In Settings → Pages, choose Deploy from a branch → main → /(root) → Save.\n\n"
        "The game is a static site. No install or build is required. "
        "Open index.html to try it locally, or serve this folder with any static web server.\n\n"
        "Each leader runs an independent game on their own browser. Progress is saved locally; "
        "Save a backup / Load a backup transfers a session. One host screen is used at the activity.\n",
        encoding="utf-8")
    paths.update([".nojekyll", "README.md"])
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        for relative in sorted(paths):
            bundle.write(SITE / relative, relative)
    total = sum((SITE / path).stat().st_size for path in paths)
    print(f"Prepared {len(content['cards'])} clues, {len(paths)} publishing files, {total / 1e6:.1f} MB.")
    print(f"Upload folder: {SITE}")
    print(f"Ready-to-extract ZIP: {archive}")


if __name__ == "__main__":
    package(build_content())
