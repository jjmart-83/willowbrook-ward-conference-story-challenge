# Build the next conference game

The October 2026 game was published and used successfully at the Willowbrook Ward activity. Its final format is the reusable starting point: six categories, 30 clues, one host screen, written answers from every team, rotating selection, automatic question timers, full/half/zero awards, speaker reminders, full-screen clip sequences, and reviewed takeaways.

The organizer downloaded the original talks posted on YouTube using **JDownloader2**. This was the acquisition step before caption review and FFmpeg preparation; JDownloader2 did not write the questions or perform the content review. The exact downloader settings were not recorded. The preserved output includes 1080p H.264/AAC MP4s, M4A audio, two English SRT caption files per talk, thumbnails, and description files. [JDownloader2's official page](https://jdownloader.org/jdownloader2) is the starting point for installing it on another machine.

## What is archived

| Material | Location |
| --- | --- |
| Current complete project | Repository `main`: plans, notes, structured sources, scripts, tests, prepared media, and speech-review evidence |
| Exact game used at the activity | Tag `october-2026-activity-live`; the original static game tree is also retained on `gh-pages` |
| October project snapshot and complete source downloads | [October 2026 project archive release](https://github.com/jjmart-83/willowbrook-ward-conference-story-challenge/releases/tag/october-2026-project-archive) |
| Source file paths, hashes, timestamps, and release URLs | [source-media-manifest.json](conference-game/source-media-manifest.json) |
| Original individual YouTube links | [source-youtube-links.txt](conference-game/source-youtube-links.txt), also recorded per talk in the manifest |
| Live game | [Willowbrook Ward Conference Story Challenge](https://jjmart-83.github.io/willowbrook-ward-conference-story-challenge/) |

The original source downloads total about 4.4 GB and are stored as one release ZIP per address. Git contains the captions and descriptions, all 104 reviewed excerpts, the prototype media, speaker images, and small audit files. Generated publishing packages, browser profiles, model weights, temporary audio, and preview-frame caches are rebuildable or machine-specific outputs and are ignored.

## Open the archived project on another machine

Clone the repository, then work from its root:

```powershell
git clone https://github.com/jjmart-83/willowbrook-ward-conference-story-challenge.git
cd willowbrook-ward-conference-story-challenge
python .\conference-game\build_game.py
node .\conference-game\tests\game-rules.cjs
```

Building uses Python and FFmpeg; the Python preparation scripts use the standard library. The rules check uses Node. Playing the prepared game requires only a browser. Double-click `Launch Conference Game.bat`, or open `conference-game/index.html` directly. The launcher's local web server requires Python. Full browser checks currently use Chrome on Windows.

To restore the full talk downloads when changing excerpts or source images:

```powershell
python .\conference-game\restore_source_media.py
# Or restore just one address:
python .\conference-game\restore_source_media.py --talks patrick-kearon
# Verify the downloaded files already on disk without changing them:
python .\conference-game\restore_source_media.py --verify-only
```

The restore script downloads from the release, verifies each ZIP and extracted file with SHA-256, restores the original folder names and timestamps, and refuses to replace differing existing files. It reuses matching captions from a clone. `--destination` supports restoring beneath another workspace root; `--archive-dir` supports already-downloaded ZIPs. Preserving timestamps matters because prepared clip fingerprints include the source video's timestamp.

## Start the next edition

1. **Create a new working branch or clone.** For example, use `git switch -c conference/april-2027`. The October release and activity tag remain the reference editions. A fresh clone has captions but no full source videos, which makes it easy to keep new downloads separate from the old conference.
2. **Download the new individual talks with JDownloader2.** Put each address in its own folder under `talks/`, with its video and English captions together. Keep the source YouTube URL. Preserve distinct folders for two addresses by the same speaker. Full session recordings are less convenient for this project's per-address inventory.
3. **Prepare the new inventory and speaker cards.** Run `python .\conference-game\prepare_assets.py`. This tool scans address folders containing MP4s, preserves known address IDs, selects speaker title frames, and maintains inventory/prototype assets. Its OCR probe requires Windows PowerShell and the Windows OCR language pack; FFmpeg and FFprobe must be on PATH. Review the resulting stills. Update `sessions.json` for the new conference and verify session membership using the official session summaries.
4. **Review the new talks and catalog the stories.** Replace the current-edition rows in `talk-review.json` and `story-catalog.json` with the new material while preserving their schema. Record caption hashes, source ranges, topic fit, actual reported details, main teaching, and qualifications. The archived October data shows the expected level of detail. Regenerate `Conference Review.md` and `Conference Story Catalog.md` using their build scripts.
5. **Choose the board and write the text.** Edit `story-board.json` for six categories and five values each, then `story-retellings.json` for the same 30 card IDs. Keep names, years, and sad circumstances from being the source of difficulty. Easy clues ask for recall; higher values ask for explanation and application. The current scoring, selection, and timer rules can be reused.
6. **Prepare and check the excerpts.** Edit each talk's passage selections, run `prepare_review_clips.py`, and inspect the resulting clip library. Listen to openings, endings, and anything used as an exact quotation. Keep necessary companion teachings with an analogy. The Whisper scripts and preserved comparison data support machine screening; rerunning them requires installing Whisper.cpp and model weights on the new machine.
7. **Build, test, and rehearse.** Run the commands below, then try several easy and hard questions with a leader and check the actual activity display and sound. Change the ward/event heading or conference date when needed; the October labels are in `index.html`, `app.js`, `story-board.json`, and the generated package README text in `build_game.py`.
8. **Publish and archive the new edition.** Review and merge the working branch into `main` to archive the project. Run `python .\conference-game\publish_game.py` to preview the game publication, then add `--push` to publish it to `gh-pages` at the existing link. The script uses a temporary worktree and leaves the source checkout on its current branch. Make a release/tag for the new event and back up its source downloads with `archive_source_media.py`, using a new conference name and release tag. Preserve the previous release.

## Fine details already resolved

| Area | Keep this behavior |
| --- | --- |
| Clue text | Supply concrete reminders without giving away the recall answer. Higher-value applications need enough story context to be meaningful. |
| Story fields | `intro` is shown before the question; `text` is the full account; `takeaway` is the main lesson; `context` is a separate expandable source note. |
| Speaker and video placement | Speaker picture on the clue page; optional hint on the question page; titled video previews and the full story on the answer page. |
| Takeaways | Lead with the main teaching, rather than a source caution. Source limits still belong in the answer when required for accuracy. |
| Timers | Start when the question appears, allow pause/resume, and restart on reset. A video hint pauses the answer countdown. |
| Preview frames | Opening-talk excerpts use clip time 0:02 to avoid a fade from black; playback still begins at zero. |
| Video playback | Native controls allow seeking in both directions. Clicking a reveal preview enters full screen, and remaining clips autoplay in sequence in the same player. |
| Source limits | Keep essential qualifications with their examples, especially the passport analogy. Machine transcription is not a human listening certification. |
| Game sessions | One host runs the shared screen. Each browser has independent scores and saved progress; JSON backups transfer a session. |

## Commands to reuse

```powershell
# Review and catalog documents
python .\conference-game\build_conference_review.py
python .\conference-game\build_story_catalog.py

# Prepared excerpts after changing reviewed source ranges
python .\conference-game\prepare_review_clips.py

# Static game and publishing ZIP
python .\conference-game\build_game.py

# Preview a game update, then publish when ready
python .\conference-game\publish_game.py
python .\conference-game\publish_game.py --push

# Rule/content checks, restore integrity checks, and full browser checks
node .\conference-game\tests\game-rules.cjs
python -m unittest discover -s conference-game/tests -p test_source_archive.py
node .\conference-game\tests\browser-check.cjs

# Create source bundles and a manifest for the next conference
python .\conference-game\archive_source_media.py --conference "April 2027" --tag april-2027-project-archive
```

Upload the resulting `.qa/source-archive/source-*.zip` files and `source-media-manifest.json` to the matching release. The script also refreshes the committed manifest and YouTube link list. Keep those changes with the corresponding edition's project snapshot.

An optional [GitHub Actions workflow template](docs/workflows/publish-game.yml) is preserved for future automation. Activating it requires a GitHub login with permission to write workflow files and changing the repository's Pages source to GitHub Actions. Current publishing uses the tested local script and the `gh-pages` branch.
