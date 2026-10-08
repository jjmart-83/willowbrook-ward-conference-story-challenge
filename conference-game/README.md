# Willowbrook Ward Conference Story Challenge

A local browser game, reviewed clip library, and preparation kit for the October 2026 General Conference activity.

**Archived October 7:** the published game was used successfully at the activity. The complete project is now on repository `main`, with [reuse instructions](../Next%20Conference.md). The organizer used **JDownloader2** to download the YouTube talks. Original download folders are backed up in the [October archive release](https://github.com/jjmart-83/willowbrook-ward-conference-story-challenge/releases/tag/october-2026-project-archive); run `python conference-game/restore_source_media.py` from the project root when the full sources are needed. Captions, prepared media, and review evidence remain in Git.

**Current status, October 5:** the complete six-topic game is playable and packaged for GitHub Pages. It has 30 clues, one to six teams, balanced topic coverage, rotating selection, story retellings, optional clips, timers, full/half/zero scoring, score corrections, undo, save/resume, JSON backups, a printable host guide, and the cooperative final and closing. See [publish and share](../Publish%20to%20GitHub%20Pages.md). The original speaker game is preserved at [prototype.html](prototype.html).

The [story-board plan](../Conference%20Activity%20Plan.md#board) supplies 30 clues and host keys. The [story catalog](../Conference%20Story%20Catalog.md) supplies source windows, recall questions, topic connections, and image prompts. The [clean conference review](../Conference%20Review.md) organizes all 37 addresses by four verified sessions and rates their fit to each assignment. Story images remain to be prepared.

Structured content is in `story-catalog.json`, `story-board.json`, and `talk-review.json`. The prototype uses its original `activity.json` and `clips.json`; the reviewed excerpt library uses `clip-library.json`. Edit source data and regenerate the corresponding document/media together.

For maintenance details and implementation constraints, see the [technical handoff](../HANDOFF.md). The ordered production checklist is in the [project overview](../README.md#remaining-work).

All 37 speaker screenshots were checked and visually reviewed in the [full contact sheet](assets/speakers/review/full-conference-review.jpg). Spannaus's name/title is clear despite the OCR error in “Muñoz”; Hutch's 0:10 override remains. The [media audit](media-audit.json) records source streams, paired caption hashes, and image dimensions.

## Open the game

1. Double-click `Launch Conference Game.bat` in the workspace root (or use `conference-game\Launch-ConferenceGame.bat` / run `Start-ConferenceGame.ps1` in PowerShell).
2. The game opens at `http://127.0.0.1:8765/conference-game/`. Connect the laptop to the TV. This launches the new story game; its full-screen button and **How to play** guide are in the top bar.

Open the separate clip library at `http://127.0.0.1:8765/conference-game/clip-library.html` to inspect the broader collection. Search by speaker/story and filter by session, assignment, or material type. The game's clue page shows a short reminder and the speaker's picture. The question page starts its timer automatically, with pause/reset and optional hints. Each answer displays a reviewed main takeaway, expandable full story/source context, and video previews. Clicking a preview starts full-screen playback and remaining clips autoplay in order; the native timeline supports seeking forward and backward. Excerpts from the opening of a talk use a 0:02 preview while playing from zero. Gong's 300-point excerpt now focuses on the gift and years of worship. Longer clips can support preparation.

To rebuild game content and the standalone upload folder/ZIP, run `python .\conference-game\build_game.py` from the workspace root. Python and FFmpeg are required for rebuilding. Clues come from `story-board.json`; introductions (`intro`), complete retellings (`text`), main lessons (`takeaway`), and source notes (`context`) come from `story-retellings.json`; clips and speaker cards come from the reviewed library and inventory. The builder caches preview frames and offsets in `assets/clip-frames` and packages one `assets/clip-previews.jpg` image. It removes retired published assets recorded in the previous ZIP. The generated `game-content.js` is bundled into the static app, which also runs directly from disk. Tests are in `tests/` and require Node; gameplay does not require Node or Python. Each browser has an independent host-controlled session.

## Refresh the review and its clips

On a fresh clone, restore original downloads before extracting new source cuts or rerunning speaker OCR. The game build itself uses the committed prepared assets and does not require the full talks. The [source manifest](source-media-manifest.json) records exact hashes and source timestamps, and [source-youtube-links.txt](source-youtube-links.txt) preserves the links originally downloaded with JDownloader2.

From the workspace root:

```powershell
# After reviewing captions and editing talk-review.json:
python .\conference-game\prepare_review_clips.py
python .\conference-game\build_conference_review.py

# After editing story-catalog.json:
python .\conference-game\build_story_catalog.py
```

Review extraction uses two FFmpeg workers, preserves the original videos and existing prototype clips, and caches clips by source file metadata and selected range. It checks audio/video streams and requested durations before replacing the library. It refuses to use captions that changed after the recorded review. Final listening and exact spoken wording remain separate from these technical checks.

`talk-review.json` is the editable source for the assignment guides, talk summaries, all six assignment ratings, context limits, and excerpts. `sessions.json` records verified session membership and official source URLs. Changed source files require fresh caption review and a renewed media audit before updating their recorded hashes.

The existing assets are already prepared. Run `python .\conference-game\prepare_assets.py` from the workspace root when source folders, prototype excerpt selections, or still settings change. It samples the first 90 seconds at one frame per second, rescans likely title-card moments at four frames per second, and uses Windows OCR to find the speaker's name and title. It saves the exact middle frame of the longest repeated match, extracts selected quote clips, and refreshes `talks.json` and `clips.json`.

Python and FFmpeg need to be installed and available on PATH. The speaker-frame probe uses Windows PowerShell and the Windows OCR language pack. The original videos stay in their current folders; the game uses the prepared short clips.

The selected frame and OCR result for every talk are listed in [the speaker probe report](speaker_probe_report.md). If OCR cannot confirm both name and title, the report links to a candidate contact sheet for manual review. `STILL_HINTS` in `prepare_assets.py` provides a fallback time for a speaker whose title card OCR misses; `STILL_OVERRIDES` sets a deliberate per-speaker timestamp when you prefer another frame after visual review.

## Inspect speech and boundaries

The [browser speech inspection report](clip-speech-review.html) and [Markdown copy](Clip%20Speech%20Review.md) cover all 104 reviewed excerpts and the 20 original prototype clips. [Whisper.cpp](https://github.com/ggml-org/whisper.cpp) transcribed their actual audio locally without an expected-wording prompt. The comparison checks source captions, essential concepts, prototype quotations, recognition confidence, and openings/endings. Each machine transcript was also read against its intended content. Suspect recognition results receive larger-model rechecks.

Use **Inspection** in the library to find flagged excerpts. Expand **Speech screen**, then use **Play opening** or **Play last 10 seconds**. The browser report has the same buttons for all clips, including the original prototype selections. Start with its high-priority items. A missing keyword may be an ASR error; a trailing fragment may follow a fully complete target passage. Listen before deciding whether to change a clip, quotation, or host explanation.

From the workspace root:

```powershell
python .\conference-game\run_clip_whisper.py
python .\conference-game\run_clip_whisper.py --prototype
python .\conference-game\compare_clip_speech.py

# Recheck a selected clip with the installed large-v3 model:
python .\conference-game\run_clip_whisper.py --cpu --model "$env:USERPROFILE\.cache\whisper\ggml-large-v3.bin" --recheck --clips chigbundu-prayer-and-burdens
python .\conference-game\compare_clip_speech.py
```

The runner defaults to the installed CUDA executable and project-local base.en weights. Use `--engine`, `--model`, or `--cpu` for another local setup. It extracts temporary mono 16 kHz audio and caches transcripts against clip/model hashes. Larger-model rechecks are preferred when their metadata matches the current clip. Raw transcripts and model provenance are in `speech-audit/`; they remain machine results, with human listening unverified.

`clip-playback.js` supports both inspection pages. When the local server does not offer seeking by byte range, it caches the selected clip in a browser Blob before playing its ending. A newer playback choice or hiding the clip cancels pending end playback. Original files and download links remain the sources.

Edit `clip-expectations.json` for changed intended content. `speech-audit/transcript-triage.json` stores interpretation of base and selected larger-model transcripts, preserves initial assessments, and rejects stale transcript hashes. If a preferred recheck changes, refresh that row's interpretation, `transcriptPath`, and `transcriptSha256` before comparing again. Keep `speech-audit/prototype-input.json` synchronized with changes to `activity.json` or its clip selections. Refresh expectations and transcript interpretation when audio changes, then rerun the comparison. Generated report and library priorities must not be manually treated as permanent approvals.

## Add or update source material

Place each additional address folder inside the workspace's [talks/](../talks) folder, with its MP4 and English SRT inside. Run `prepare_assets.py` again to create its speaker card and add it to the inventory. Verify its session against the official roster in `sessions.json`, review the full SRT, and update `media-audit.json`, `talk-review.json`, and any new catalog entries. Prepare the reviewed clips and regenerate the notes/catalog with the commands above. Edit the structured sources because the Markdown review and catalog are generated.

For an additional card in the speaker prototype, edit `activity.json` under `quotes`. Each card uses an address `id` from `talks.json` in the legacy `speakerId` field, a group ID from `groups`, start and end times in seconds, a short excerpt, and a discussion prompt. Rerun `prepare_assets.py` for that deck's clips.

Multiple addresses by one speaker need separate folders. The prep script preserves existing IDs and adds a folder-derived suffix for a new address by the same speaker. President Oaks's earlier talk remains `dallin-h-oaks`; the folder ending in `¦ Temples` becomes `dallin-h-oaks-temples`, with its own source files and still. The optional `label` field distinguishes addresses in the inventory/report. The prototype shows each speaker name only once among the answer choices.

The inventory's `folder` field is the address folder's name within `talks/`. Source URLs include `../talks/`; prepared speaker images and clips remain under `conference-game/assets/`.

The available captions have a few speech-recognition errors. Check the actual video before using wording as an exact quotation. When new talks are added, rerun the script and check their results in the [speaker probe report](speaker_probe_report.md).
