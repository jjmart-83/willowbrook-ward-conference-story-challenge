# General Conference activity — reusable project archive

**Updated October 7, 2026.** The October 2026 game was published and used successfully at the Willowbrook Ward activity. This repository now preserves the full project so the same interface, rules, media tools, and review process can be reused after the next conference. It was designed for **30–50 youth**. All **37 downloaded addresses by 36 speakers** were reviewed from their supplied English captions, and their membership in the **four morning/afternoon sessions** was verified against official summaries.

Start with [Next Conference.md](Next%20Conference.md) to reuse the project. The original YouTube talks were downloaded using **JDownloader2**, as reported by the organizer. Original download folders are preserved in the [October source archive release](https://github.com/jjmart-83/willowbrook-ward-conference-story-challenge/releases/tag/october-2026-project-archive), with file hashes, source links, and a restore script. Captions, prepared assets, source data, review evidence, plans, scripts, and tests are committed on `main`.

The [conference review](Conference%20Review.md) provides clean notes by assignment, session, and address. The [clip library](conference-game/clip-library.html) provides **104 newly prepared excerpts**, covering every address and every story selected for the 30-clue board. All **37 speaker name/title screenshots** were checked visually.

**Willowbrook Ward Conference Story Challenge is now playable:** six topic columns, 30 clues, one to six teams, rotating selection, story retellings, all-team scoring, save/resume, and a cooperative closing. The larger ward heading stays on one line. Question timers start automatically, with pause and reset controls. Each answer has a reviewed main takeaway, and multi-clip answers continue automatically in full screen. Double-click [Launch Conference Game.bat](Launch%20Conference%20Game.bat) to try it. The [GitHub Pages publishing guide](Publish%20to%20GitHub%20Pages.md) explains how to upload the ready-made folder and share a link tonight. The original speaker prototype is preserved separately.

**Live game:** [Willowbrook Ward Conference Story Challenge](https://jjmart-83.github.io/willowbrook-ward-conference-story-challenge/) · [GitHub repository](https://github.com/jjmart-83/willowbrook-ward-conference-story-challenge). Git lives at the project root. `main` archives the full project; Pages serves `gh-pages`. The [publishing script](conference-game/publish_game.py) builds and checks the game, previews changes, and can publish only the generated game files. The exact game used at the activity is preserved by the `october-2026-activity-live` tag.

## Start here

| To do this | Open this |
| --- | --- |
| Reuse the complete project after the next conference | [Next Conference.md](Next%20Conference.md) |
| Restore original downloaded talk files | [Source manifest](conference-game/source-media-manifest.json), [restore script](conference-game/restore_source_media.py) |
| Review the activity, rules, timing, and all 30 host keys | [Story-board plan](Conference%20Activity%20Plan.md#board) |
| Prepare a discussion using the six assignments | [Six assignment guides](Conference%20Review.md#topic-guide) |
| Compare every talk's teaching, qualifications, and passages | [Talks by session](Conference%20Review.md#talks-by-session) |
| Filter and play the prepared excerpts | [Clip library](conference-game/clip-library.html) |
| Prioritize speech and boundary checks | [Browser inspection report](conference-game/clip-speech-review.html), [Markdown report](conference-game/Clip%20Speech%20Review.md) |
| Choose a story; find sources, tags, and an image prompt | [Conference Story Catalog](Conference%20Story%20Catalog.md) |
| Play or publish the complete game | [Publishing guide](Publish%20to%20GitHub%20Pages.md), [game instructions](conference-game/README.md) |
| Continue technical work | [HANDOFF.md](HANDOFF.md) |

## Six assignments and board categories

The [assigned groups and questions](Conference%20Review.md#assignments) are preserved in the review. Each category has a guide with source choices, an application question, and a qualification to retain.

| Assigned group | Board category | Main discussion question |
| --- | --- | --- |
| Deacons | [Follow Christ](Conference%20Review.md#topic-following) | What blessings or results can we expect by following Him every day? |
| Builders of Faith | [Know Your Worth](Conference%20Review.md#topic-identity) | How does knowing who we are change how we see ourselves and treat others? |
| Teachers | [Find Guidance](Conference%20Review.md#topic-revelation) | How can we seek, recognize, and act on guidance from the Spirit? |
| Messengers of Hope | [Find Strength](Conference%20Review.md#topic-hope) | What can we do when life is hard or our faith is strained? |
| Priests | [Keep Promises](Conference%20Review.md#topic-covenants) | How do our covenants connect us to Jesus Christ and help us become more like Him? |
| Gatherers of Light | [Help Others](Conference%20Review.md#topic-serving) | How can we help others feel the Savior's love? |

## What we have

| Material | Current state | Location |
| --- | --- | --- |
| Downloaded sources | 37 addresses by 36 speakers; video and English captions for each | [talks/](talks), [inventory](conference-game/talks.json) |
| Original download backup | 37 complete talk-folder ZIPs containing 222 files; about 4.4 GB; SHA-256 hashes and original timestamps recorded | [Archive release](https://github.com/jjmart-83/willowbrook-ward-conference-story-challenge/releases/tag/october-2026-project-archive), [YouTube links](conference-game/source-youtube-links.txt) |
| Complete review | Every address reread; all six topic connections rated; summaries, qualifications, useful stories, and excerpts recorded | [Clean notes](Conference%20Review.md), [canonical review JSON](conference-game/talk-review.json) |
| Verified sessions | Saturday morning: 8; Saturday afternoon: 10; Sunday morning: 9; Sunday afternoon: 10 | [Session notes](Conference%20Review.md#talks-by-session), [sessions.json](conference-game/sessions.json) |
| Story catalog | 133 entries across 36 addresses; Oaks's closing address has no developed story | [Readable catalog](Conference%20Story%20Catalog.md), [editable JSON](conference-game/story-catalog.json) |
| Proposed board | 30 selected stories, six columns × values 100–500, questions and answer criteria | [Host plan](Conference%20Activity%20Plan.md#board), [board JSON](conference-game/story-board.json) |
| Reviewed excerpts | 104 new clips covering all 37 addresses and all 30 selected board stories; audio/video streams and durations checked | [Playable library](conference-game/clip-library.html), [clip index](conference-game/clip-library.json) |
| Speaker screenshots | All 37 name/title cards visually verified, including both Oaks addresses | [Contact sheet](conference-game/assets/speakers/review/full-conference-review.jpg), [media audit](conference-game/media-audit.json) |
| Playable story game | Six categories, 30 clues, one to six teams, rotating selection, full/half/zero scoring, timers, backups, print guide, final and closing | [Game](conference-game/index.html), [launcher](Launch%20Conference%20Game.bat) |
| GitHub Pages package | Standalone publishing folder and ZIP with selected clips and speaker cards; no build or backend required | [Publishing instructions](Publish%20to%20GitHub%20Pages.md) |
| Original browser prototype | Two-team speaker game and its 20 clips preserved | [Prototype](conference-game/prototype.html) |
| Visuals | Six topic illustrations and reviewed speaker cards; individual story illustration prompts remain available | [Story catalog](Conference%20Story%20Catalog.md) |
| Activity alternative | Six simultaneous missions with scenarios and a separate five-point rubric | [Mission alternative](Conference%20Activity%20Plan.md#missions) |

The catalog includes developed stories, brief references, analogies, scripture accounts, and imagined illustrations. Some scripture episodes recur; 133 entries is not a count of distinct historical events.

Oaks's morning address (`dallin-h-oaks`) and closing/temple address (`dallin-h-oaks-temples`) remain distinct sources. His closing **study → ponder prayerfully → act in faith** invitation is prepared for the activity's private next step.

Content review is based on the supplied captions. Paired SRT files are identical, with recognition errors and overlapping cues. **Exact spoken wording and final edit boundaries still need listening before live use.** Stream/duration checks establish usable media; they do not establish an audio content review. Keep companion qualifications with their stories, particularly when a clue uses separated passages. See [clip selection and source limits](Conference%20Review.md#clip-selection) and [review findings](Conference%20Review.md#review-findings).

## Proposed activity at a glance

Use six balanced teams, one shared screen with sound, and written responses or whiteboards. Selection rotates, and **every team answers every clue**. Begin with each team selecting its assigned category, then ensure every category has been played twice before opening selection across the board.

Award full value for a complete correct answer, half for a substantially correct incomplete multi-part answer, and zero for an incorrect or unsupported answer. Accept equivalent wording and supported applications. Higher values test reasoning and application; speaker names and exact quotations are not required.

| Minutes | 50-minute planning default |
| --- | --- |
| 0–5 | Form teams, explain rules, and try a practice clue |
| 5–41 | About 18 selections, with at least two from each category |
| 41–46 | Cooperative final: support two topic connections to one familiar story |
| 46–50 | Scores and a private next step using Oaks's study/ponder/act invitation |

The [proposal](Conference%20Activity%20Plan.md#board) also provides a 40-minute version with 12 selections and a 60–70-minute option that can attempt all 30. Ages and available minutes can be refined when supplied; 50 minutes remains the planning default. Longer clips are reference material for a retelling or a chosen passage, rather than a requirement to play every full excerpt.

## Reuse for the next activity

The October game has been published and used. The [next-conference guide](Next%20Conference.md) explains downloading with JDownloader2, preparing new sources, replacing the current board content, testing, publishing, and preserving another edition. Independent Whisper transcripts cover the October edition's 104 reviewed excerpts and 20 prototype clips. The [speech inspection report](conference-game/clip-speech-review.html) supports listening checks; machine transcription does not establish human listening verification.

1. **Start the next edition.** Follow [Next Conference.md](Next%20Conference.md), keeping the October tags and source release as references.
2. **Refine the event selections.** Choose opening clues and substitutions, check difficulty, and briefly playtest a few values. Adjust the target number of clues if ages or available minutes are supplied.
3. **Listen to the final selections.** Check exact wording, meaning, and first/last sentences on the clips chosen for live use. Preserve essential qualifications and all passages needed for a multi-part clue.
4. **Prepare activity materials.** Use the game's **Print host guide** for all questions and answer keys, and assemble response sheets or whiteboards. Individual story illustrations remain optional.
5. **Rehearse on event equipment.** Check audio, readability, pacing, scoring, resume, and a retelling backup on the laptop/TV.

## Where to make changes

- **Rules and host outline:** [Story-board plan](Conference%20Activity%20Plan.md#board). Update [story-board.json](conference-game/story-board.json) alongside changed questions or answer criteria.
- **Talk notes and source evidence:** edit [talk-review.json](conference-game/talk-review.json), then run `python .\conference-game\build_conference_review.py`. The root review is generated from this canonical data.
- **Reviewed excerpts:** edit the review's passage selections, then run `python .\conference-game\prepare_review_clips.py`. [clip-library.json](conference-game/clip-library.json) and the [library page](conference-game/clip-library.html) provide playback and source mappings.
- **Story content:** edit [story-catalog.json](conference-game/story-catalog.json), then run `python .\conference-game\build_story_catalog.py`.
- **Session and media evidence:** [sessions.json](conference-game/sessions.json) records official membership; [media-audit.json](conference-game/media-audit.json) records source media, caption hashes, and screenshot checks.
- **Speaker prototype:** [activity.json](conference-game/activity.json), [clips.json](conference-game/clips.json), and [prepare_assets.py](conference-game/prepare_assets.py) maintain its existing deck and media. Its group IDs differ from the board's topic IDs.
- **Downloaded sources:** preserve folder names and stable address IDs under [talks/](talks). Follow the [maintenance instructions](conference-game/README.md) for inventory changes.

Earlier documents and project history are preserved in the [archive](docs/archive/README.md).
