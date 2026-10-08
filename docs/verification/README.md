# October 2026 verification evidence

These small reports preserve checks performed for the game used at the activity. Browser profiles, download caches, temporary files, and generated screenshots remain outside Git.

- `activity-browser-results.json`: 138 Chrome checks against the packaged game, including all 30 clues, scoring/backups, automatic timing, native seeking, and full-screen clip sequences.
- `activity-live-results.json`: 14 checks against the original live site, including matching runtime files and hosted video seeking/continuation.
- `source-archive-integrity.json`: October 7 source-archive coverage, local integrity, and GitHub attachment digests.

The original activity runtime is preserved by `october-2026-activity-live`. The source archive restore tooling has separate round-trip, timestamp, path, corruption, and overwrite checks in `conference-game/tests/test_source_archive.py`.
