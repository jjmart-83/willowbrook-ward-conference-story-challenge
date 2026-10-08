"""Render the reviewed story data as a readable planning document."""
from collections import Counter
from datetime import date
import json
from pathlib import Path


GAME = Path(__file__).resolve().parent
ROOT = GAME.parent


def clock(second):
    return f"{second // 60:02d}:{second % 60:02d}"


def render():
    data = json.loads((GAME / "story-catalog.json").read_text(encoding="utf-8"))
    stories = data["stories"]
    reviewed = date.fromisoformat(data["reviewedDate"])
    reviewed_label = f"{reviewed.strftime('%B')} {reviewed.day}, {reviewed.year}"
    topics = {t["id"]: t for t in data["topics"]}
    inventory = {t["id"]: t for t in json.loads((GAME / "talks.json").read_text(encoding="utf-8"))}
    sessions = json.loads((GAME / "sessions.json").read_text(encoding="utf-8"))["sessions"]
    session_order = {session["id"]: i for i, session in enumerate(sessions)}
    reviewed_talks = sorted(data["reviewedTalks"], key=lambda talk: (session_order[inventory[talk["talkId"]]["sessionId"]], talk["speaker"]))
    lines = [
        "# Conference story catalog",
        "",
        "**Project navigation:** [Overview and remaining work](README.md) · [Activity plan](Conference%20Activity%20Plan.md#board) · [Discussion guide](Conference%20Review.md#topic-guide)",
        "",
        f"**Reviewed {reviewed_label}:** all **{len(data['reviewedTalks'])} addresses**, read in full from the supplied English captions. This catalog contains **{len(stories)} story and illustration entries**. These are occurrences in talks, not a count of unique historical events: some scripture stories recur, and brief references and analogies are included separately from developed narratives.",
        "",
        "The [fireside assignments](Conference%20Review.md#assignments) remain the topic framework. See the [activity plan](Conference%20Activity%20Plan.md#board) for the recommended category-and-value game and a complete sample board. The existing browser game is still the speaker-identification prototype.",
        "",
        "## How to use the catalog",
        "",
        "- **Story tags overlap:** About the speaker; Speaker's family; About others; History; Scripture. History marks an explicitly historical account, not every memory merely because it happened in the past. Scripture also includes parables, visions, and quoted scriptural episodes; it does not mean every entry describes a historical event.",
        "- **Kind describes the material:** personal/reported experiences, historical accounts, scripture accounts/parables, brief vignettes, analogies, and fictional or imagined illustrations. A scripture-reference entry names a familiar story without retelling it. Use substantial narratives first; the short entries provide optional imagery or supporting clues. Ordinary doctrinal quotations and lists without a story or visual example are not individually cataloged.",
        "- **Topic connections:** the lead topic is the strongest suggested use. Other topics are possible supporting uses, not proof that the excerpt fully answers that group's assignment. A connection question needs a specific detail and an explanation; more than one answer can earn credit.",
        "- **Source windows:** times are search ranges in the original video, sometimes separated by intervening teaching. The [prepared clip library](conference-game/clip-library.html) contains selected excerpts with talk qualifications and related context. Captions contain errors and overlapping cues; listen to final edits before using exact quotations. Paraphrased answers are sufficient.",
        "- **Image prompts:** each is ready to copy and produces a representative illustration. All requested prompts are supplied; no images have been generated. Visual setting details are illustrative choices, not additional factual claims about the account. An image may reveal the recall answer; use it as an intentional easy clue, ask about its meaning, or display it on the answer reveal.",
        "- **Recurring stories:** matching recurring-story keys identify related accounts so a board can avoid testing the same episode twice. A speaker's personal experience and the comparison drawn from it stay together when they form one narrative.",
        "",
        "## Fireside categories",
        "",
        "| Board category | Assigned group | Main question |",
        "| --- | --- | --- |",
    ]
    for topic in data["topics"]:
        lines.append(f"| {topic['label']} | {topic['group']} | {topic['question']} |")
    lines += ["", "## Coverage of every address", "", "Session membership follows the [verified conference review](Conference%20Review.md#talks-by-session). Entries are alphabetical within each session.", "", "| Address | Session | Entries | Caption source |", "| --- | --- | ---: | --- |"]
    for talk in reviewed_talks:
        caption = talk["caption"].removeprefix("../")
        lines.append(f"| [{talk['label']}](#{talk['talkId']}) | {inventory[talk['talkId']]['session']} | {talk['entryCount']} | [English SRT]({caption}) |")
    lines += ["", "## Entries by session", ""]
    last_session = None
    for talk in reviewed_talks:
        session_id = inventory[talk["talkId"]]["sessionId"]
        if session_id != last_session:
            lines += [f'<a id="session-{session_id}"></a>', "", f"## {inventory[talk['talkId']]['session']}", ""]
            last_session = session_id
        caption = talk["caption"].removeprefix("../")
        video = talk["video"].removeprefix("../")
        lines += [f"<a id=\"{talk['talkId']}\"></a>", "", f"### {talk['label']}", "", f"Source: [captions]({caption}) · [original video]({video})", ""]
        entries = [s for s in stories if s["talkId"] == talk["talkId"]]
        if not entries:
            lines += [talk["reviewNote"], "", "**Useful non-story closing:** 00:32–00:56, study conference, ponder prayerfully, and act in faith. Keep this distinct from the morning Oaks address. No story image prompt is needed for this address.", ""]
        for s in entries:
            windows = "; ".join(f"{clock(w['start'])}–{clock(w['end'])}" for w in s["sourceRanges"])
            tag_names = "; ".join(data["tags"][tag] for tag in s["tags"])
            connections = topics[s["primaryTopic"]]["label"]
            if s["otherTopics"]:
                connections += " (lead); also " + ", ".join(topics[t]["label"] for t in s["otherTopics"])
            lines += [f"<a id=\"{s['id']}\"></a>", "", f"#### {s['title']}", "", f"**ID:** `{s['id']}` · **Window:** {windows} · **Kind:** {s['kind']}", "", f"**Tags:** {tag_names}. **Fireside connections:** {connections}.", "", s["summary"], "", f"**Recall clue:** {s['question']}  ", f"**Answer:** {s['answer']}", "", "**Connection clue:** Choose a fireside topic and explain how one detail from this story helps answer its assigned question. Use the connections above as starting points; accept other well-supported answers.", "", f"**Image prompt:** {s['imagePrompt']}", ""]
            if s["recurringStory"]:
                lines += [f"**Recurring story key:** `{s['recurringStory']}`.", ""]
    lines += ["## Data and maintenance", "", "The structured source is [conference-game/story-catalog.json](conference-game/story-catalog.json), kept separate from the original `activity.json` prototype deck. Regenerate this document with `python .\\conference-game\\build_story_catalog.py` after editing the catalog. New downloads need a fresh caption review before being added.", ""]
    (ROOT / "Conference Story Catalog.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Rendered {len(stories)} entries across {len(data['reviewedTalks'])} addresses.")
    print("Kinds:", dict(Counter(s["kind"] for s in stories)))


if __name__ == "__main__":
    render()
