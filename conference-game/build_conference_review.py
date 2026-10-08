"""Render the clean review and its clip index from the complete talk review."""
from __future__ import annotations

import json
from pathlib import Path

GAME = Path(__file__).resolve().parent
ROOT = GAME.parent


def load(name):
    return json.loads((GAME / name).read_text(encoding="utf-8"))


def clock(seconds):
    seconds = int(round(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def ranges(items):
    return "; ".join(f"{clock(r['start'])}–{clock(r['end'])}" for r in items)


def safe(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def render():
    data = load("talk-review.json")
    talks = {t["id"]: t for t in load("talks.json")}
    reviewed = {t["talkId"]: t for t in data["talks"]}
    topics = {t["id"]: t for t in data["topics"]}
    stories = {s["id"]: s for s in load("story-catalog.json")["stories"]}
    sessions = load("sessions.json")["sessions"]
    library = load("clip-library.json") if (GAME / "clip-library.json").exists() else {"clips": []}
    clip_by_id = {c["id"]: c for c in library["clips"]}
    if set(reviewed) != set(talks):
        raise ValueError("The clean review must cover the complete address inventory.")
    if {c["talkId"] for c in library["clips"]} != set(talks):
        raise ValueError("Prepare excerpts from every address before rendering the clean review.")
    selected_stories = {c["storyId"] for c in load("story-board.json")["cards"]}
    if not selected_stories <= {c.get("storyId") for c in library["clips"]}:
        raise ValueError("The clip library is missing a selected board story.")

    lines = [
        "# Conference review and game foundation", "",
        f"**Reviewed {data['reviewedDate']}:** all **{len(reviewed)} downloaded addresses by {len({t['speaker'] for t in talks.values()})} speakers** were reread in full from their English captions and checked against the discussion notes, story catalog, and 30 proposed clues. This guide is organized by assignment and conference session.", "",
        "[Project overview](README.md) · [Activity plan](Conference%20Activity%20Plan.md) · [Story catalog](Conference%20Story%20Catalog.md) · [Play the prepared clips](conference-game/clip-library.html)", "",
        "## How to use this foundation", "",
        "Start with the six assignment guides to balance the game. Use the session entries to compare each talk's actual teaching, strongest connections, qualifications, and prepared excerpts. The story catalog supplies illustration prompts and alternative stories; the activity plan supplies the clue questions and answer criteria.", "",
        "**Direct** means the speaker explicitly teaches that assignment. **Supporting** means the passage helps a connection or application but does not fully answer the assigned question. An omitted assignment has no strong connection identified in this review.", "",
        "Summaries and host answers are paraphrases. The supplied SRTs have recognition errors and overlapping cue times; their paired copies are identical. Clip selections have been checked against the complete captions and their media streams/durations are checked during extraction. Exact spoken wording and a final listen to each edit remain separate checks; caption review is not an audio audit.", "",
        "## Find material", "",
        "| Material | Section |", "| --- | --- |",
        "| Six original assignments | [Assignments](#assignments) |",
        "| Discussion and game source selection | [Six assignment guides](#topic-guide) |",
        "| Every address | [Talks by session](#talks-by-session) |",
        "| Source limits and clip use | [Clip selection](#clip-selection) |",
        "| Corrections from the fresh pass | [Review findings](#review-findings) |", "",
        '<a id="assignments"></a>', "", "## Assigned groups and questions", "",
        "| Group | Board category | Assigned question |", "| --- | --- | --- |",
    ]
    for topic in data["topics"]:
        lines.append(f"| {topic['group']} | [{topic['label']}](#topic-{topic['id']}) | {topic['question']} |")
    lines += ["", '<a id="topic-guide"></a>', "", "## Six assignment guides", ""]
    for topic in data["topics"]:
        lines += [f'<a id="topic-{topic["id"]}"></a>', "", f"### {topic['label']} — {topic['group']}", "", f"**Assigned question:** {topic['question']}", "", topic["foundation"], "", f"**Question to build from:** {topic['applicationQuestion']}", "", f"**Keep this qualification:** {topic['qualification']}", "", "| Strong source | What it adds | Original-video window |", "| --- | --- | --- |"]
        for tid in topic["leadTalkIds"]:
            review = reviewed[tid]
            fit = next(f for f in review["topicFits"] if f["topic"] == topic["id"])
            lines.append(f"| [{talks[tid]['label']}](#talk-{tid}) | {safe(fit['reason'])} | {ranges(fit.get('sourceRanges', []))} |")
        lines.append("")

    lines += ['<a id="talks-by-session"></a>', "", "## Talks by session", "", "Session membership was checked against the official session summaries linked below. Entries are alphabetical within each session for easy lookup; this is not a claim about speaking order.", "", "| Session | Addresses | Source |", "| --- | ---: | --- |"]
    for session in sessions:
        lines.append(f"| [{session['label']}](#session-{session['id']}) | {len(session['talkIds'])} | [Official summary]({session['sourceUrl']}) |")
    lines.append("")
    for session in sessions:
        lines += [f'<a id="session-{session["id"]}"></a>', "", f"## {session['label']}", "", f"Session source: [official summary]({session['sourceUrl']}).", ""]
        for tid in session["talkIds"]:
            talk, review = talks[tid], reviewed[tid]
            lines += [f'<a id="talk-{tid}"></a>', "", f"### {talk['label']}", "", f"[Original video]({talk['video'].removeprefix('../')}) · [Captions]({talk['captions'].removeprefix('../')}) · [Speaker screenshot](conference-game/{talk['image']})", "", review["summary"], "", "| Assignment connection | Fit | Evidence / source window |", "| --- | --- | --- |"]
            for fit in review["topicFits"]:
                if fit["fit"] == "none":
                    continue
                lines.append(f"| [{topics[fit['topic']]['label']}](#topic-{fit['topic']}) | {fit['fit'].capitalize()} | {safe(fit['reason'])} {ranges(fit.get('sourceRanges', []))} |")
            lines += ["", "**Keep the context:** " + " ".join(review["qualifications"]), ""]
            useful = review.get("usefulStories", [])
            if useful:
                labels = []
                for item in useful:
                    story_id = item if isinstance(item, str) else item.get("storyId", item.get("id"))
                    if story_id in stories:
                        suitability = item.get("suitability", "") if isinstance(item, dict) else ""
                        label = f"[{stories[story_id]['title']}](Conference%20Story%20Catalog.md#{story_id})"
                        labels.append(label + (f" — {suitability}" if suitability else ""))
                if labels:
                    lines += ["**Useful story material:**", ""]
                    lines += ["- " + label for label in labels]
                    lines.append("")
            lines += ["| Prepared excerpt | Original range | Use in the game |", "| --- | --- | --- |"]
            for passage in review["passages"]:
                if passage["id"] not in clip_by_id:
                    continue
                clip = clip_by_id[passage["id"]]
                lines.append(f"| [{safe(passage['title'])}](conference-game/{clip['path']}) | {clock(clip['start'])}–{clock(clip['end'])} | {safe(passage['rationale'])} |")
            if review["corrections"]:
                lines += ["", "**Review clarification:** " + " ".join(review["corrections"])]
            lines.append("")

    lines += ['<a id="clip-selection"></a>', "", "## Clip selection and source limits", "", f"The [clip library](conference-game/clip-library.html) contains **{len(library['clips'])} prepared excerpts** linked to their source addresses, six assignments, and story IDs where applicable. It covers every reviewed address and every story used by the 30-clue sample board. Long story excerpts are reference material: use a short retelling or a chosen passage during a timed clue.", "", "- Play an excerpt or read its context before asking for a detail the audience otherwise has no opportunity to know.", "- Keep the essential limitation with an analogy or promise. If a long source is split into two clips, use both for a clue that depends on both, or give the missing qualification in the host retelling.", "- Some images make a recall answer visible. Use those intentionally on an easy clue, save the image for reveal, or ask about meaning/application.", "- Higher values should test explanation and application. Accept supported topic connections and equivalent wording; do not turn names, painful experiences, or exact quotations into the difficulty.", "- A clip's media check establishes playable audio/video and duration. Listen to final selections on the event equipment before presenting exact wording or relying on an edit's first/last sentence.", "", 'The [full screenshot contact sheet](conference-game/assets/speakers/review/full-conference-review.jpg) was visually reviewed: all 37 name/title cards are present and readable, including distinct sources for both Oaks addresses. The [media audit](conference-game/media-audit.json) records each video, paired caption hash, and image dimension/status.', "", '<a id="review-findings"></a>', "", "## Review findings", ""]
    for finding in data["findings"]:
        lines += ["- " + finding]
    if (GAME / "speech-audit" / "analysis.json").exists():
        lines += ["", "The [browser speech inspection report](conference-game/clip-speech-review.html) and [Markdown copy](conference-game/Clip%20Speech%20Review.md) compare independent audio transcripts with the intended content and source captions, including the earlier prototype clips. Use their priorities and the clip library's inspection filter to choose what to listen to first. The report is a machine screen and transcript review; it does not certify exact wording or final edit boundaries."]
    lines += ["", "The [structured review](conference-game/talk-review.json) records a rating for every talk against all six assignments, caption hashes/cue counts, suggested excerpts, and review corrections. It is the editable source for this guide. Regenerate with `python .\\conference-game\\build_conference_review.py` after updating the data and clip library.", ""]
    (ROOT / "Conference Review.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    render()
