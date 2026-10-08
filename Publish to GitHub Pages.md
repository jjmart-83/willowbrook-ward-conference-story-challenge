# Publish from the complete project

The live [Willowbrook Ward Conference Story Challenge](https://jjmart-83.github.io/willowbrook-ward-conference-story-challenge/) was used successfully for the activity. The [repository](https://github.com/jjmart-83/willowbrook-ward-conference-story-challenge) now archives the full project on `main`, including planning documents, source data, prepared media, scripts, captions, tests, and review evidence.

Pages serves the `gh-pages` branch from its root, with HTTPS enforced. This separates the project archive from the prepared game while keeping the same shared URL. Git lives at the workspace root. Generated `github-pages/` and the publishing ZIP are ignored.

## Update the current game

Work from the repository root. Edit questions and answer criteria in `conference-game/story-board.json`; edit `story-retellings.json` for the short `intro`, full `text`, main `takeaway`, and expandable source `context`. Clip mappings come from the reviewed library and talk inventory.

```powershell
python .\conference-game\build_game.py
node .\conference-game\tests\game-rules.cjs
python -m unittest discover -s conference-game/tests -p test_source_archive.py
node .\conference-game\tests\browser-check.cjs

# Review and archive the source changes on main.
git status
git diff
git add .
git commit -m "Update conference game"
git push origin main

# Preview the publication, then publish the checked game.
python .\conference-game\publish_game.py
python .\conference-game\publish_game.py --push
```

`publish_game.py` rebuilds the package, runs the rule/content checks, and shows the publication diff. Its default mode makes no remote changes. With `--push`, it fetches the current publishing branch, commits the prepared game, and pushes to `gh-pages`. It uses a temporary worktree under `.qa/`, so the source checkout stays on its current branch. Source planning files, original downloads, and tool caches do not enter the publishing package. GitHub Pages deploys the updated branch automatically; a rejected push or failed deployment leaves the previous game available.

The game package contains 72 files, about 221 MB, including 40 selected excerpts, 23 speaker cards, and the preview sheet. It can be opened directly from disk. Python and FFmpeg are needed for rebuilding, Node for checks, and Git for publishing; gameplay needs only a browser.

## Reuse and preserve editions

Start with [Next Conference.md](Next%20Conference.md). Create a working branch, replace the current-edition talk review/catalog/board text, prepare new assets, then test and merge to `main`.

The exact October activity game is preserved at tag `october-2026-activity-live`. The [October project archive release](https://github.com/jjmart-83/willowbrook-ward-conference-story-challenge/releases/tag/october-2026-project-archive) preserves the complete project snapshot and original JDownloader2 download folders. Preserve those references when publishing a new edition.

Restore the full original downloads when changing clip cuts or source screenshots:

```powershell
python .\conference-game\restore_source_media.py
```

Rebuilding the existing game uses the prepared assets in Git and does not require restoring the original full talks.

## Optional Actions automation

An [Actions workflow template](docs/workflows/publish-game.yml) is archived for future use. The current GitHub CLI login has `repo`, `read:org`, and `gist` scopes, so it can upload the project but cannot add files under `.github/workflows/`. Activating the template requires a login with workflow-write permission, placing it at `.github/workflows/publish-game.yml`, and switching the repository's Pages source to GitHub Actions. The template builds and checks the game and uploads only `github-pages/`, following GitHub's [custom workflow documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages). This is optional; branch-based publishing is already configured.

## Local play and standalone copies

Double-click [Launch Conference Game.bat](Launch%20Conference%20Game.bat), or open `conference-game/index.html`. The launcher uses a local Python web server. The JSON backup controls preserve sessions when local-file storage depends on the browser.

To publish a standalone copy in another repository, build and upload **the contents** of `github-pages/` to that repository's root, then configure its Pages source to **Deploy from a branch → main → /(root)**. This applies to the separate standalone repository; the full-project repository publishes from `gh-pages`. See GitHub's [Pages source instructions](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) and [file upload guide](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository).

Each browser runs an independent host-controlled game. At the activity, one screen is shared and teams answer on paper or whiteboards. The game preserves speaker reminders, automatic timers, main takeaways, seeking, clip sequences, score corrections, backups, the printable guide, and cooperative closing.
