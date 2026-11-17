#!/usr/bin/env python3
"""List the commits that CHANGELOG.md does not cover yet, grouped by date.

A commit counts as covered when its short hash appears in one of the
`<!-- commits: ... -->` markers that close each date section of the
changelog. Merge commits and commits that only touch CHANGELOG.md are
skipped: they carry no change worth describing.

Usage: python3 pending_commits.py            (run anywhere inside the repo)
Prints a plain-text report, newest date first. Standard library only.
"""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

CHANGELOG = "CHANGELOG.md"
MAX_FILES_SHOWN = 20
TRAILER = re.compile(r"^(Co-Authored-By|Signed-off-by|Reviewed-by):", re.IGNORECASE)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def covered_hashes(changelog: Path) -> set[str]:
    if not changelog.exists():
        return set()
    text = changelog.read_text(encoding="utf-8")
    hashes: set[str] = set()
    for block in re.findall(r"<!--\s*commits:([^>]*)-->", text):
        hashes.update(block.split())
    return hashes


def is_covered(full_hash: str, covered: set[str]) -> bool:
    # Markers hold abbreviated hashes, whose length git may grow over time.
    return any(full_hash.startswith(short) for short in covered)


def main() -> int:
    try:
        root = Path(git("rev-parse", "--show-toplevel").strip())
    except subprocess.CalledProcessError:
        print("Not inside a git repository.", file=sys.stderr)
        return 1

    changelog = root / CHANGELOG
    covered = covered_hashes(changelog)

    # \x1e starts a commit, \x1f separates fields, \x1d ends the message;
    # --name-only then lists the files the commit touched.
    raw = git(
        "log",
        "--no-merges",
        "--date=short",
        "--name-only",
        "--format=%x1e%H%x1f%h%x1f%ad%x1f%s%x1f%b%x1d",
        "HEAD",
    )

    by_date: dict[str, list[dict]] = defaultdict(list)
    for record in raw.split("\x1e")[1:]:
        header, _, files_part = record.partition("\x1d")
        full, short, date, subject, body = header.split("\x1f", 4)
        files = [line for line in files_part.splitlines() if line.strip()]
        if is_covered(full, covered):
            continue
        if not files or set(files) == {CHANGELOG}:
            continue
        # Trailers (Co-Authored-By, Signed-off-by) say nothing about the change.
        body = "\n".join(line for line in body.splitlines() if not TRAILER.match(line))
        by_date[date].append(
            {"short": short, "subject": subject, "body": body.strip(), "files": files}
        )

    print(f"Changelog: {CHANGELOG} {'exists' if changelog.exists() else 'does not exist yet'}")
    print(f"Branch: {git('branch', '--show-current').strip() or '(detached HEAD)'}")
    total = sum(len(commits) for commits in by_date.values())
    print(f"Commits not yet in the changelog: {total}")

    for date in sorted(by_date, reverse=True):
        print(f"\n=== {date} ===")
        # git log lists newest first; show each day oldest first, as it happened.
        for commit in reversed(by_date[date]):
            print(f"\n--- {commit['short']} {commit['subject']}")
            if commit["body"]:
                print("\n".join(f"    {line}" for line in commit["body"].splitlines()))
            files = commit["files"]
            shown = ", ".join(files[:MAX_FILES_SHOWN])
            more = f" (+{len(files) - MAX_FILES_SHOWN} more)" if len(files) > MAX_FILES_SHOWN else ""
            print(f"    files ({len(files)}): {shown}{more}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
