"""Build/check the game and preview or push only its files to gh-pages."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ARCHIVE = ROOT / "Conference-Story-Challenge-GitHub-Pages.zip"


def run(args, cwd=ROOT, **kwargs):
    return subprocess.run(args, cwd=cwd, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--push", action="store_true", help="Commit and publish the checked game to origin/gh-pages.")
    args = parser.parse_args()
    run([sys.executable, str(HERE / "build_game.py")])
    run(["node", str(HERE / "tests" / "game-rules.cjs")])
    if args.push:
        run(["git", "fetch", "origin", "gh-pages"])
    qa = ROOT / ".qa"
    qa.mkdir(exist_ok=True)
    worktree = Path(tempfile.mkdtemp(prefix="publish-game-", dir=qa)).resolve()
    if not worktree.is_relative_to(qa.resolve()):
        raise ValueError("Publishing worktree must stay inside .qa/.")
    added = False
    try:
        run(["git", "worktree", "add", "--detach", str(worktree), "origin/gh-pages"])
        added = True
        tracked = run(["git", "ls-files", "-z"], cwd=worktree, capture_output=True).stdout.decode("utf-8").split("\0")
        with zipfile.ZipFile(ARCHIVE) as bundle:
            expected = set(bundle.namelist())
            if "index.html" not in expected or bundle.testzip() is not None:
                raise ValueError("Invalid game publishing package")
            for relative in expected:
                destination = (worktree / relative).resolve()
                if not destination.is_relative_to(worktree) or ".git" in Path(relative).parts:
                    raise ValueError(f"Invalid publishing path: {relative}")
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(relative) as source, destination.open("wb") as target:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        target.write(chunk)
            for relative in tracked:
                if relative and relative not in expected:
                    destination = (worktree / relative).resolve()
                    if not destination.is_relative_to(worktree):
                        raise ValueError("Retired file escapes the temporary publishing worktree")
                    destination.unlink(missing_ok=True)
        run(["git", "add", "--all"], cwd=worktree)
        run(["git", "diff", "--cached", "--stat"], cwd=worktree)
        changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=worktree).returncode
        if changed not in (0, 1):
            raise RuntimeError("Could not compare the prepared publishing tree")
        if not args.push:
            print("Preview complete. No remote changes. Run with --push to publish this game.")
        elif changed:
            run(["git", "commit", "-m", "Publish conference game"], cwd=worktree)
            run(["git", "push", "origin", "HEAD:gh-pages"], cwd=worktree)
            print("Published to gh-pages. GitHub Pages will deploy the updated game.")
        else:
            print("The published game already matches the prepared package.")
    finally:
        if added:
            # Only this generated, validated QA worktree is removed. Source files
            # and the main working tree are never switched or replaced.
            if not worktree.is_relative_to(qa.resolve()):
                raise ValueError("Refusing to remove a worktree outside .qa/.")
            run(["git", "worktree", "remove", "--force", str(worktree)])
        elif worktree.exists():
            worktree.rmdir()  # worktree add failed; only an empty task-created folder


if __name__ == "__main__":
    main()
