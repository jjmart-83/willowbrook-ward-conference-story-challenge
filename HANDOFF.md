# Technical handoff — General Conference activity

**Updated October 7, 2026.** The **Willowbrook Ward Conference Story Challenge** was published and used successfully at the activity, as reported by the organizer. The full project is now archived for reuse after the next conference. Start with [Next Conference.md](Next%20Conference.md). The game retains its single-line 24 px desktop ward heading, larger supporting text, automatic question timers with pause/reset, reviewed takeaways, and automatic full-screen clip sequences. Game validation includes 1,862 rule/content checks and 138 real-Chrome checks. See [publishing instructions](Publish%20to%20GitHub%20Pages.md).

**Published:** [live game](https://jjmart-83.github.io/willowbrook-ward-conference-story-challenge/) · [public repository](https://github.com/jjmart-83/willowbrook-ward-conference-story-challenge). `main` archives the full project; GitHub Pages serves `gh-pages` from `/` with HTTPS enforced. [publish_game.py](conference-game/publish_game.py) builds/tests the standalone game and previews or pushes its files using an isolated temporary worktree. The exact activity game is preserved by tag `october-2026-activity-live` at commit `b4481f20382f701b16e4c7bbbebf542944a77eee`. The original live verification included 14 checks for matching runtime assets, all 30 clues, automatic timing, video playback/seeking, and automatic continuation.

The local Git repository is now **at the planning workspace root**, tracking `origin/main`. Edit the project normally, rebuild and test, then commit/push when publishing is within the requested scope. `github-pages/` and the publishing ZIP are generated and ignored. Git metadata was moved from that generated folder, copied under the desktop account so ordinary Git/IDE access works, and the original metadata was retained under ignored `.qa/` as a migration backup. No global trust settings were changed. GitHub CLI is authenticated as `jjmart-83` outside the process sandbox. Sandbox Git commands may need a command-scoped `safe.directory` for this exact workspace root. The local commit identity uses `266604661+jjmart-83@users.noreply.github.com`. The current GitHub OAuth login lacks `workflow` scope; an Actions template is archived under `docs/workflows/`, but publishing currently uses `publish_game.py` and the legacy `gh-pages` Pages source. Do not represent the template as an active workflow.

**Source acquisition and complete backup:** the organizer reported using **JDownloader2** to download the original talks posted on YouTube. Preserve this fact in the reuse guide; exact downloader settings were not recorded. [source-youtube-links.txt](conference-game/source-youtube-links.txt) contains all 37 source URLs recovered from the downloaded MP4 metadata. [source-media-manifest.json](conference-game/source-media-manifest.json) records every original source path, size, SHA-256, timestamp, and release asset URL. The [October source release](https://github.com/jjmart-83/willowbrook-ward-conference-story-challenge/releases/tag/october-2026-project-archive) preserves all 37 complete talk folders: 222 files, about 4.4 GB. Full MP4/M4A/thumbnail files use release attachments because some videos exceed Git's individual-file limit. Captions and descriptions are tracked in Git. `archive_source_media.py` creates the bundles/manifest; `restore_source_media.py` restores or verifies them and rejects differing local files. Restore before extracting new source clips or rerunning speaker OCR; rebuilding the existing game uses committed prepared assets and does not need full talk downloads. Source captions and speech-audit files are marked `-text` in `.gitattributes` to preserve the exact bytes used by stored hashes.

## Current implementation and reviewed foundation

All **37 addresses by 36 speakers** have been reread in full from their supplied English captions and compared with the notes, story catalog, and proposed clues. The [clean review](Conference%20Review.md) is organized by [assignment](Conference%20Review.md#topic-guide) and [session/address](Conference%20Review.md#talks-by-session). Official session membership is verified: 8 Saturday morning, 10 Saturday afternoon, 9 Sunday morning, and 10 Sunday afternoon.

The [clip library](conference-game/clip-library.html) contains **104 newly prepared excerpts**, covering all 37 addresses and all 30 stories selected for the board. All **37 speaker screenshots** have readable name/title cards, confirmed on the [full contact sheet](conference-game/assets/speakers/review/full-conference-review.jpg). The 133-entry catalog remains the story source.

`index.html`, `app.js`, and `styles.css` now run the complete story board. `game-core.js` owns the scoring, selection, undo, and backup-validation rules; `game-content.js` bundles the reviewed board with authored retellings and media mappings. `build_game.py` regenerates content and copies only needed assets to `github-pages`, then creates the upload ZIP. The existing launcher opens this game. The speaker prototype is preserved as `prototype.html`, `prototype.js`, and `prototype.css`, with its original 20 clips. Six drawn topic icons and reviewed speaker cards supply the visuals.

The runtime has no server or package dependencies. It works at a repository subpath and can be opened directly from disk. Browser-local storage and JSON backups preserve completed and in-progress clues. Each leader runs an independent session; one host controls the activity screen. The publishing package excludes source talk downloads, preparation scripts, audit data, and browser profiles. Run `node conference-game/tests/game-rules.cjs` and `node conference-game/tests/browser-check.cjs` after changing game behavior. The Chrome checks serve the publishing package and save evidence to `.qa`.

Keep clue introductions separate from complete accounts: `story-retellings.json` has `intro` (before the question), `text` (full retelling at reveal), `takeaway` (the main lesson), and `context` (an expandable source note). All 30 answer keys and takeaways were reviewed against the supplied talk reviews and source accounts. Introductions and reread dialogs withhold requested recall answers while retaining memorable context for application questions. Cook uses the supplied inscription, Runia identifies the Lego set, Schmeil includes the unfinished temple and bag with holes, and Farnes includes the temple setting and forced smile. Renlund 400 asks a natural two-part application; Dunn 500 leads with the hydration pack and two water bottles. The clue page shows the speaker photo and no media controls. The question page starts the timer and retains optional hints with generic numbered labels. The reveal shows every clip's preview and descriptive title; clicking starts full-screen playback from the clip's beginning. Remaining clips autoplay in the displayed order using the same player, exiting full screen after the last. The cooperative final can show the complete race story because it asks for connections. The host guide includes the main takeaway and separate source context.

`build_game.py` uses FFmpeg to cache preview frames, then combines them into one sheet (`assets/clip-previews.jpg`) to keep the upload below 100 files. Excerpts starting within the first two seconds of a talk use a preview at clip time 0:02; other excerpts use their opening frame. The preview cache includes the offset, so changing it invalidates the image. `game-content.js` records each clip's tile index and `previewTime`; playback always begins at zero. Gong 300 is now a focused 20-second gift excerpt (source 591.5–611.5), ending after her years of worship and before the burial account. Its new independent machine transcript and interpretation are current. `playGameClip` requests full screen during the click's user activation and checks server range support. A server returning a full file instead of a byte range uses a browser Blob so the timeline can seek. Pending loads are canceled when navigating or choosing another clip, and Blob URLs are released when changing screens. Browser checks drag the native timeline in both directions, exercise the server fallback, and verify real ended events advance all four Kearon clips under Chrome's normal autoplay policy. The publishing builder removes retired assets only when they were recorded in the previous ZIP.

## Files and source ownership

| File | Role / edit rule |
| --- | --- |
| [talk-review.json](conference-game/talk-review.json) | Canonical complete review: summaries, all six topic ratings, qualifications, caption hashes/cue counts, corrections, and passage selections |
| [Next Conference.md](Next%20Conference.md) | Reuse workflow, JDownloader2 acquisition, archive/restore instructions, and resolved game details |
| [source-media-manifest.json](conference-game/source-media-manifest.json), [source-youtube-links.txt](conference-game/source-youtube-links.txt) | Original download integrity/provenance and GitHub release locations |
| [archive_source_media.py](conference-game/archive_source_media.py), [restore_source_media.py](conference-game/restore_source_media.py) | Standard-library source archive and restore tooling, covered by `test_source_archive.py` |
| [publish_game.py](conference-game/publish_game.py), [optional workflow template](docs/workflows/publish-game.yml) | Current branch-based publishing with an explicit `--push`; optional future Actions automation |
| [build_conference_review.py](conference-game/build_conference_review.py) | Generates root `Conference Review.md` from the review, session data, catalog, and clip index |
| [sessions.json](conference-game/sessions.json) | Verified official session membership and source links; alphabetical entries do not claim speaking order |
| [media-audit.json](conference-game/media-audit.json) | Source video/stream/duration evidence, paired caption hashes, and screenshot dimensions/status |
| [prepare_review_clips.py](conference-game/prepare_review_clips.py) | Extracts caption-reviewed passages into `assets/review-clips/`, checks streams/durations, and updates the library |
| [clip-library.json](conference-game/clip-library.json) | Generated excerpt index: source addresses, sessions/topics, ranges, rationale, story IDs, and media-check status |
| [clip-library.html](conference-game/clip-library.html) | Playback page with search, session, assignment, material, and inspection filters; companions include shared stories and explicit context links |
| [clip-playback.js](conference-game/clip-playback.js) | Shared opening/ending playback for the library and speech report; supports seeking through the local launcher's server |
| [Browser speech report](conference-game/clip-speech-review.html), [Clip Speech Review.md](conference-game/Clip%20Speech%20Review.md), [speech-audit/analysis.json](conference-game/speech-audit/analysis.json) | Generated inspection priorities and evidence for all 104 reviewed excerpts plus 20 prototype clips |
| [run_clip_whisper.py](conference-game/run_clip_whisper.py), [compare_clip_speech.py](conference-game/compare_clip_speech.py) | Independent local Whisper transcription, hash-verified caches, content/caption comparison, and inspection report generation |
| [clip-expectations.json](conference-game/clip-expectations.json), [transcript-triage.json](conference-game/speech-audit/transcript-triage.json) | Intended content checks and interpretation of machine transcripts; neither is supplied as a Whisper prompt |
| [speech-audit/prototype-input.json](conference-game/speech-audit/prototype-input.json) | Separate source/quotation expectations for the original 20 clips; synchronize with changes to the prototype deck |
| [Speech verification](conference-game/speech-audit/verification.json), [browser verification](conference-game/speech-audit/browser-verification.json) | Clip/transcript/model integrity, complete comparison coverage, and real Chrome inspection/playback checks; human listening remains unverified |
| [story-catalog.json](conference-game/story-catalog.json) | Editable story source: 133 entries with stable IDs, tags, topic connections, summaries, source windows, prompts, and recurring-story keys |
| [build_story_catalog.py](conference-game/build_story_catalog.py) | Generates root `Conference Story Catalog.md` from catalog JSON |
| [story-board.json](conference-game/story-board.json) | Proposed 6×5 board, story references, questions, and answer criteria; keep synchronized with the host proposal |
| [talks.json](conference-game/talks.json) | Generated inventory and source URLs with stable address IDs and verified session metadata |
| [activity.json](conference-game/activity.json), [clips.json](conference-game/clips.json) | Existing six-group, 20-excerpt speaker deck and media mapping; `speakerId` contains an address ID |
| [prepare_assets.py](conference-game/prepare_assets.py) | Discovers sources under `talks/` and maintains the existing speaker stills, prototype clips, and inventory |
| [Probe-SpeakerFrames.ps1](conference-game/Probe-SpeakerFrames.ps1), [speaker_probe_report.md](conference-game/speaker_probe_report.md) | OCR helper and generated still-selection records |

Board topic IDs are `following`, `identity`, `revelation`, `hope`, `covenants`, and `serving`. Prototype group IDs are `deacons`, `builders`, `teachers`, `hope`, `priests`, and `gatherers`. Use the board's topic definitions for the new implementation.

## Launch and regeneration

Double-click the root [Launch Conference Game.bat](Launch%20Conference%20Game.bat). It starts a hidden Python server bound to localhost and opens `http://127.0.0.1:8765/conference-game/`. Open the clip library at `http://127.0.0.1:8765/conference-game/clip-library.html`. Full operating instructions are in the [game README](conference-game/README.md).

Run from the workspace root:

```powershell
# After editing the complete review or its passage selections:
python .\conference-game\prepare_review_clips.py
python .\conference-game\build_conference_review.py

# After editing story-catalog.json:
python .\conference-game\build_story_catalog.py

# When deliberately refreshing the speaker prototype's sources/media:
python .\conference-game\prepare_assets.py
```

Reviewed-clip preparation requires Python and FFmpeg/FFprobe on PATH. Speaker preparation also uses Windows PowerShell and the Windows OCR language pack. Assets are already prepared; regeneration is needed when their source selections or settings change.

## Speaker stills and identity handling

Still preparation samples the first 90 seconds, uses fuzzy OCR matching, rescans likely moments, and selects a frame from the longest repeated name/title match. It saves the exact frame at 1280×720. Visual review establishes whether the text and chosen image are suitable.

Preserve these settings and distinctions:

- `STILL_OVERRIDES = {"hutch-u-fale": 10.0}` records the user's preferred 0:10 frame.
- `STILL_HINTS = {"vaiangina-sikahema": 29}` is a fallback; the recorded OCR selection is about 0:28.
- Spannaus's screenshot is visually readable despite OCR misreading “Muñoz.” Keep its `partial-name-review` OCR status alongside the confirmed visual result.
- Oaks's morning address (`dallin-h-oaks`) and closing/temple address (`dallin-h-oaks-temples`) have distinct sources and assets. The speaker prototype deduplicates names in answer choices.

Downloaded addresses live under `talks/`. Inventory `folder` values contain each source folder's basename; `video` and `captions` URLs are relative to `conference-game/` and start with `../talks/`. Preserve source folder names, original filenames, and stable IDs because the review, catalog, and prepared media depend on them.

## Content and validation constraints

The substantive review uses captions. Paired SRTs are identical and contain recognition errors and overlapping cue times. Summaries and host answers are paraphrases. Catalog windows remain source-search ranges, and prepared excerpts remain caption-reviewed selections: **exact spoken wording and first/last edit boundaries still need listening before live use**. Audio/video stream and duration checks do not establish a content listening audit.

Retain essential limitations with the associated teaching. Some board stories use separated passages, including Bednar's passport story, its adversity limit, and later authorized-stamp explanation. A clue depending on several passages needs those clips or the missing context in the host retelling. The [clip-selection notes](Conference%20Review.md#clip-selection) and [review findings](Conference%20Review.md#review-findings) record the relevant constraints.

Oaks's closing source has no developed story entry. Its prepared study/ponder/act passage is the planned unscored closing. The supplied captions describe Salt Lake Temple celebration/resources and contain no new-temple-location list.

When changing content, check stable IDs, current caption hashes, all six topic fits, source ranges against media duration, selected board-story coverage, clip streams/durations, screenshot paths, and Markdown links. Keep the review JSON, generated notes, catalog, board answers, and library synchronized. Rehearse final selections on the event equipment.

Windows PowerShell 5.1 can display UTF-8 accented names incorrectly; inspect UTF-8 file contents before changing spellings based on console output. The workspace is not a Git repository; local files are the project record.

Whisper.cpp is installed at `C:\whisper-work\cuda\Release\whisper-cli.exe`, with the original large-v3 model in the user's `.cache\whisper` folder. Screening uses the project-local `speech-audit/models/ggml-base.en.bin`; selected suspects are rechecked with large-v3. Raw JSON, text, SRT, metadata, and logs live under `speech-audit/`. Metadata records actual clip/model hashes, backend, language, version, and the absence of a transcription prompt. Keep `audioContentVerified` and `humanAudioVerified` false until actual listening establishes the content. See the [speech workflow](conference-game/README.md#inspect-speech-and-boundaries) for regeneration commands.

Earlier documents and technical history are preserved in the [archive](docs/archive/README.md).
