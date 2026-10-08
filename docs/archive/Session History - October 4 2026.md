# Session history: October 2026 General Conference Mutual activity

**Archived October 5, 2026:** this preserves the October 4 handoff and review history. For current planning and remaining work, start with the [project overview](../../README.md); for technical continuation, use the [current handoff](../../HANDOFF.md). Statements below describe the archived session.

Source links in this archive were adjusted after the October 5 move of downloaded address folders into `talks/`. Historical references to downloads at the workspace root describe the previous layout.

**Updated:** October 4, 2026  
**Workspace:** `General_Conference_Activity_Planning`

This is the project handoff for a new session. It summarizes the current files, workflow, key implementation choices, and remaining work. It records decision-level rationale and evidence; it is not a private internal reasoning transcript.

## Goal and current state

Prepare a youth Mutual activity around October 2026 General Conference for **30–50 participants**. Ages and activity duration are still unconfirmed. The workspace has reviewed discussion notes for the six assigned groups and a local browser prototype called **Conference Connections**. The prototype plays an excerpt, asks participants to identify the speaker, then shows the speaker card and group discussion prompts. The user considers this a placeholder and has requested a stronger game concept.

**Latest direction:** the user requested a review of every talk for memorable stories, story-type tags, and image-generation prompts, and suggested a Jeopardy-style category/value game with ordinary answers. That review and a concrete sample board are complete. [Story Board Proposal.md](Story%20Board%20Proposal.md) is now the recommended planning direction; the earlier six-mission proposal remains an alternative. The actual browser redesign is still unimplemented.

### October 4 planning review

- Initially read all 18 Saturday talks in full from their supplied captions and revised [Conference Discussion Notes.md](Conference%20Discussion%20Notes.md) around the actual six assignment questions. Subsequent Sunday reviews below bring the current reviewed total to 37 addresses.
- Added [Saturday Caption Review.md](Saturday%20Caption%20Review.md), with source links and an audit of all 20 existing excerpt cards. Every talk's two SRT files are identical; overlapping cue times and transcription errors require audio review for final wording/cuts. Several current clips appear to end before their displayed excerpts finish.
- Added [Conference Game Proposal.md](Conference%20Game%20Proposal.md): six teams play six simultaneous missions involving listening evidence, varied card tasks, topic connections, and fictional youth scenarios. Default 50-minute plan, with 40/60-minute options. All six assignments anchor a mission; two optional broader challenges use Christofferson and Sikahema.
- The proposal is a host outline with sample tasks, answer keys, scoring, and room logistics. **The browser redesign has not been implemented.** Existing `activity.json`, clips, and runtime files still represent the original prototype; finalize content and update clips/metadata together when implementing the new design.
- Next step: settle duration/ages if supplied, choose final passages from the complete caption review, verify clip wording/boundaries against audio, and implement the selected game format. Keep the existing ingestion and speaker-still workflow below.

### October 4 Sunday asset ingestion

- Workspace checks found **12 new complete Sunday talk folders**, for **30 total**. The user subsequently confirmed that 12 was the correct new-talk count. No talk shortfall or incomplete video/caption folders remain from this ingestion request.
- Ran the existing `prepare_assets.py` workflow successfully. It refreshed `talks.json`, `clips.json`, the speaker probe report, **30 speaker stills**, and the existing **20 excerpt clips**. Twenty-nine stills have OCR-confirmed names/titles; Hutch U. Fale retains the manual 0:10 override.
- Visually reviewed all 12 new speaker cards. Names and titles are visible; no new manual override was needed. The [new-speaker contact sheet](../../conference-game/assets/speakers/review/new-talks-ingestion.jpg) records that review.
- Verified all source/asset paths, unique talk IDs, all 30 JPEGs at 1280×720, and audio/video streams and matching durations for all 20 registered clips. The two SRT copies are also identical for each new talk.
- New speakers: Alfred Kyungu, Ciro Schmeil, Dallin H. Oaks, David A. Bednar, Dieter F. Uchtdorf, Edward Dube, Gary E. Stevenson, Henry B. Eyring, James G. O. Fantone, Neil L. Andersen, Quentin L. Cook, and Rosemary K. Chibota.
- This step ingested assets; a subsequent review, documented below, covers the Sunday content. New excerpt-card selection and implementation remain to be done.

### October 4 Sunday content review

- Read all 12 Sunday talks in full against [Fireside topics.docx.md](Fireside%20topics.docx.md). The substantive caption review now covers all 30 downloaded talks.
- Updated [Conference Discussion Notes.md](Conference%20Discussion%20Notes.md) with Sunday passages in all six group sections, a six-group starting-point table, and a complete Sunday talk map alongside the Saturday map.
- Added [Sunday Caption Review.md](Sunday%20Caption%20Review.md): per-talk direct/supporting connections, original-video search windows, qualifications, and links to all 12 exact caption files reviewed.
- Updated the game proposal with Sunday source alternatives and the evidence questions that would need to change with each source. Chibota is especially useful for identity, noticing unseen people, and acting on promptings; Schmeil directly covers the sacrament and temple preparation; Oaks adds the strained-faith discussion; Kyungu provides peaceful-language tasks.
- Review remains caption-based. Audio verification, new quote cards/clips, and the browser redesign are still implementation work; the original 20-card prototype deck has not changed.

### October 4 additional seven-address ingestion and review

- Found and ingested **seven additional Sunday afternoon addresses**: Andrea Muñoz Spannaus, Clark G. Gilbert, President Oaks's closing/temple address, Gabriel W. Reid, Moisés Villanueva, Paul H. Sinclair, and Thabo Lebethoa. The collection now has **37 addresses by 36 speakers**: 18 Saturday and 19 Sunday.
- Read all seven captions in full against the original fireside questions. Added [Additional Talk Review.md](Additional%20Talk%20Review.md), with direct/supporting matches, qualifications, original-video search windows, and seven exact caption links. Updated all six group sections and the address map in the discussion notes, plus source alternatives in the game proposal.
- Oaks's closing address includes a useful **00:32–00:56 study → ponder prayerfully → act in faith** invitation. Use it for the game's private closing. The central temple section concerns the Salt Lake Temple celebration and resources; the supplied captions contain no list of newly announced temple locations. His earlier address remains the stronger source about doubts and strained faith.
- New activity candidates include Sinclair's help-before-judging story, Gilbert's listening/prompting example, Lebethoa's scripture-to-action example, and Spannaus's identity and inadequacy passages. Reid supports personal care in teaching; Villanueva addresses blessings that differ from expectations. No new quote cards were added to the prototype deck.
- Fixed ingestion of two addresses by one speaker: existing folder IDs are preserved; new duplicate-speaker addresses receive a folder-derived suffix. Oaks's original `dallin-h-oaks` remains intact, and the separate address is `dallin-h-oaks-temples`. Video/caption paths, probe results, and stills stay distinct. `label` identifies the closing address in the inventory/report. In `activity.json`, the legacy `speakerId` field refers to the address ID.
- Updated the prototype's answer choices to deduplicate speaker names, and its inventory message to distinguish addresses from speakers. Checked ID uniqueness/stability across repeated and reordered inputs, plus 100 mocked renders using both Oaks addresses.
- Preparation completed with **37 stills and 20 existing clips**: 35 name/title OCR matches, Hutch's existing manual override, and one Spannaus partial-name OCR result. Visually checked all seven new cards in the [latest contact sheet](../../conference-game/assets/speakers/review/additional-talks-ingestion.jpg). Spannaus's name and title are clear; OCR misread “Muñoz” as “Mufioz”. Retain that automated status and this visual-review record; no new timestamp override is needed.
- Verified the final 37-address inventory: unique IDs/folders, 36 distinct speaker names, 19 Sunday sources, all source/asset paths, identical paired SRTs, 1280×720 stills, distinct Oaks references, and Hutch's 0:10 override. All 20 registered clips contain audio/video and match requested durations within 0.25 seconds. Local links in the updated planning documents resolve.

The workspace currently contains **37 talk folders**, each with an MP4 and English SRT, plus prepared assets for **20 quote cards**. The latest preparation run produced 37 speaker stills and 20 clips. All stills are 1280×720. Both Oaks addresses have separate source and asset references. Caption content has been reviewed for every address; final quote wording and clip edits still need audio review.

### October 4 story catalog and category/value board

- Read every address's complete caption again for stories. Created [Conference Story Catalog.md](../../Conference%20Story%20Catalog.md) with **133 entries** across **36 addresses**, plus an explicit no-developed-story finding for Oaks's closing/temple address. The 133 includes narrative episodes, brief accounts/references, analogies, and fictional/imagined illustrations; it is not a count of unique historical events.
- Each entry includes a stable ID, original-video search windows, material kind, overlapping tags (**About the speaker; Speaker's family; About others; History; Scripture**), primary/supporting fireside connections, a paraphrase, recall question/answer, and a standalone image-generation prompt. Recurring-story keys help avoid selecting duplicate scripture episodes. All prompts are supplied; **no images were generated**.
- The editable source is [story-catalog.json](../../conference-game/story-catalog.json). Run `python .\conference-game\build_story_catalog.py` to regenerate the readable catalog. This data is separate from the original `activity.json` deck.
- Added [Story Board Proposal.md](Story%20Board%20Proposal.md) and [story-board.json](../../conference-game/story-board.json): a complete **six-column × five-value board**, **100–500 points**, **30 different story entries from 23 speakers**, and questions with answer criteria for every square. Columns follow the actual six assignments. Story-type tags are filters, not the main categories. Higher values test explanation and application rather than obscure facts.
- Recommended play: six balanced teams; selection rotates; **every team answers every clue**; full/half/zero scoring with no negative points. A 50-minute plan uses about 18 selections with deliberate topic coverage; completing all 30 needs a longer session. Ordinary answers are accepted. Multiple supported topic connections can be correct.
- Oaks's study/ponder/act passage remains the unscored closing. The existing 20 clips and speaker-identification browser remain available; the story board, new clips, and image assets are **not implemented/prepared yet**. The earlier six-mission document is retained as an alternative, with links to the latest direction.
- Validated all 37 sources/coverage rows, 133 unique story IDs, tags and topics, source-window bounds against every video's duration, the complete 6×5 board, all clue-to-story links, and local Markdown file/anchor links. The board values are editorial judgments and still need a brief playtest; source cuts and exact wording need audio review.

## Assigned groups

The assignment source is [Fireside topics.docx.md](Fireside%20topics.docx.md). The game data and discussion notes use these groups:

| Group | Topic |
| --- | --- |
| Deacons | Following Jesus Christ |
| Builders of Faith | Our identity and worth as children of God |
| Teachers | Recognizing the Holy Ghost and receiving personal revelation |
| Messengers of Hope | Finding strength in Christ through challenges |
| Priests | Covenants, the sacrament, and temple preparation |
| Gatherers of Light | Loving, serving, and inviting others to Christ |

The game prompts are in `conference-game/activity.json`; the fuller speaker connections, approximate timestamps, and notes are in [Conference Discussion Notes.md](Conference%20Discussion%20Notes.md).

## What is built

- **Prep kit:** `conference-game/prepare_assets.py` discovers talk folders at the workspace root, prepares speaker stills, extracts the selected excerpts, and refreshes `talks.json` and `clips.json`.
- **Speaker-card OCR:** `conference-game/Probe-SpeakerFrames.ps1` uses Windows OCR. The method and per-speaker results are documented in [speaker_probe_report.md](../../conference-game/speaker_probe_report.md).
- **Local game:** `conference-game/index.html`, `app.js`, and `styles.css` implement the browser experience. The host can choose a topic set and round count, name two teams, play excerpts, reveal speaker cards, and award points.
- **Launchers:** Double-click the root `Launch Conference Game.bat`. It starts the local Python web server and opens the game. The PowerShell and game-folder launchers are under `conference-game/`.
- **Assets:** Original talk files remain in their speaker folders. Prepared speaker images and short MP4 clips are in `conference-game/assets/speakers/` and `conference-game/assets/clips/`.

## Speaker still selection: method and rationale

The videos do not always show the speaker name/title at the same timestamp. A fixed timestamp produced blank or incorrect speaker cards, so the prep script now searches for each speaker's lower-third:

1. Sample the first 90 seconds of each talk at one frame per second.
2. Use Windows OCR and fuzzy name matching to find likely frames containing the full speaker name and additional title text.
3. Rescan likely title-card moments at four frames per second.
4. Select the middle frame from the longest repeated OCR match. Repeated detections favor a settled title card over a brief fade-in/out match.
5. Save the exact sampled frame OCR reviewed. This avoids seeking back to a whole-second timestamp and accidentally capturing a different frame.

The method is intentionally about text recognition and persistence. It does **not** judge facial expressions. Visual review remains available for choosing a more flattering or otherwise preferred frame.

Current manual settings in `prepare_assets.py`:

- `STILL_OVERRIDES = {"hutch-u-fale": 10.0}`: intentional user choice at 0:10 after visual review.
- `STILL_HINTS = {"vaiangina-sikahema": 29}`: fallback only if OCR cannot read the lower-third. OCR currently detects Sikahema at about 0:28, so the hint is not the selected time in the current report.
- Directly extracted fallback images are scaled to 1280×720 so image dimensions remain consistent with the probe frames.

If a card still looks wrong, inspect its image and nearby frames, then add/update a one-speaker override. Do not generalize that user's visual preference into a rule for other speakers.

## Important limitations and checks

- English SRT captions contain speech-recognition errors and overlapping cue times. Both caption copies are identical for each of the 37 ingested addresses, and the substantive review covers all 37. Treat quote text and timestamps as draft material and verify the actual audio before presenting wording as an exact quotation or finalizing cuts. The Saturday caption review records the existing card issues; the prototype wraps all card text in quotation marks regardless of verification status.
- OCR text can contain typos even when the selected image is correct. The report is a useful index, not a substitute for looking at the image when a result is uncertain.
- `speaker_probe_report.md` marks manual overrides and any uncertain OCR matches. For uncertain matches, the script creates contact sheets in `conference-game/assets/speakers/review/`.
- Windows PowerShell 5.1 may display UTF-8 accented names as mojibake in its console. Check the files in a UTF-8-aware editor before changing names.
- The root folder is not a Git repository; treat the workspace files as the source of truth.

## How to continue when talks are added

1. Add each downloaded talk folder beside the existing speaker folders. It needs an MP4 and an English `.srt` caption file.
2. From the workspace root, run `python .\conference-game\prepare_assets.py`. Requirements: Python, FFmpeg on `PATH`, Windows PowerShell, and a Windows OCR language pack. The run rescans the current set, refreshes stills and clips, and can take a few minutes.
3. Review `conference-game/speaker_probe_report.md` and any candidate contact sheets. Visually inspect chosen cards that appear faded or otherwise unsuitable; add a per-speaker `STILL_OVERRIDES` entry when needed.
4. Review the new SRTs for strong passages related to the six assignments. Add quote cards to `conference-game/activity.json` (speaker ID, group ID, start/end seconds, excerpt, prompt), and update the group notes in `Conference Discussion Notes.md`.
5. Run the launcher and review the full game on the target laptop/TV. The game is served locally at `http://127.0.0.1:8765/conference-game/`.

## Suggested next-session checklist

- Start with the story catalog and Story Board Proposal, then read the discussion notes and caption audit. The latest recommended activity is a six-topic category/value board for 30–50 youth; the earlier simultaneous-mission proposal is an alternative.
- Use the complete 37-address review, including both distinct Oaks sources. The earlier Sunday batch contained 12 talks and the latest batch contained seven; neither has outstanding ingestion work.
- If more folders are added, regenerate the inventory and assets using the steps above.
- Verify quote wording and excerpt boundaries against the actual videos, especially where SRT wording is uncertain.
- Review discussion coverage across all six groups; add or adjust quote cards and notes where the complete talk set suggests stronger matches.
- Review the 30 sample clues, adjust values after a short playtest, and implement the category/value board with six teams, answer criteria, and deliberate topic coverage. Use the story tags and recurring-story keys when changing sources. The current two-team random deck does not provide that flow.
- Play through the completed game from the root launcher on the target laptop/TV.

## File map

- [This handoff](../../HANDOFF.md): project state and rationale.
- [Conference Discussion Notes.md](Conference%20Discussion%20Notes.md): group notes, topic connections, approximate timestamps, and speaker map.
- [Saturday Caption Review.md](Saturday%20Caption%20Review.md): all 18 reviewed sources, content qualifications, and audit of the original 20 excerpt cards.
- [Sunday Caption Review.md](Sunday%20Caption%20Review.md): the first 12 Sunday sources, assignment connections, and candidate passages.
- [Additional Talk Review.md](Additional%20Talk%20Review.md): the seven latest Sunday addresses, including Oaks's closing/temple source, and their fireside connections.
- [Conference Story Catalog.md](../../Conference%20Story%20Catalog.md): full 37-address narrative review, tags, questions, and 133 image prompts.
- [Story Board Proposal.md](Story%20Board%20Proposal.md): recommended category/value activity, complete 30-clue sample board, rules, timing, and host keys.
- [conference-game/story-catalog.json](../../conference-game/story-catalog.json): editable structured story data.
- [conference-game/story-board.json](../../conference-game/story-board.json): structured 6×5 sample board and answer criteria.
- [conference-game/build_story_catalog.py](../../conference-game/build_story_catalog.py): renders the catalog Markdown from its JSON source.
- [Conference Game Proposal.md](Conference%20Game%20Proposal.md): earlier simultaneous-mission alternative, timing, sample tasks, and host keys.
- [Fireside topics.docx.md](Fireside%20topics.docx.md): original group assignments.
- [conference-game/README.md](../../conference-game/README.md): launch and prep instructions.
- [conference-game/prepare_assets.py](../../conference-game/prepare_assets.py): asset preparation, OCR selection, and manual timestamp settings.
- [conference-game/Probe-SpeakerFrames.ps1](../../conference-game/Probe-SpeakerFrames.ps1): Windows OCR helper.
- [conference-game/speaker_probe_report.md](../../conference-game/speaker_probe_report.md): current speaker-card results.
- [conference-game/activity.json](../../conference-game/activity.json): six group prompts and 20 quote cards.
