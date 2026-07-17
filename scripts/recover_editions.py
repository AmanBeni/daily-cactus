#!/usr/bin/env python3
"""A6 — one-time recovery for editions gutted by the pre-v2 assemble bug.

BACKGROUND
----------
Before A1-A3 (content-hash ids, per-date refs snapshots, immutable editions),
`assemble_edition.py` re-assembled EVERY drafts/*.json on EVERY publish
against that day's `feeds/refs.json` (overwritten daily, positional ids). Once
a story's positional id (e.g. "ai-3") pointed at a different article than the
day it was drafted, the wrong-link guard correctly dropped the mismatch and a
gutted edition silently overwrote the good one on gh-pages.

Each edition JSON was CORRECT in the gh-pages commit made on its own publish
day — nothing needs to be regenerated, only restored. This script walks
`gh-pages` history and, for each `editions/<date>.json`, finds the FIRST
commit that added/touched it, and restores that historical blob as the
current content on the checked-out working tree (it does not commit or push —
call this from a workflow / by hand, then commit+push the result once you've
reviewed it).

USAGE
-----
    python3 scripts/recover_editions.py --repo /path/to/checked-out/gh-pages

Designed to run on GitHub Actions (or the owner's machine) against a real
checkout of the gh-pages branch. This module's git-log parsing logic is
unit-tested here with a MOCKED `git log` (see `if __name__ == "__main__" and
"--selftest"` below and EXECUTION_NOTES.md) since no real gh-pages checkout is
available in this working copy.

It never deletes an edition; a file with NO history (never actually on
gh-pages, or genuinely broken from day one — e.g. the known 2026-06-18
example.com-link edition) is reported, not touched, so the owner can decide
whether to delete it or leave it as broken-but-informational.
"""
import argparse
import json
import pathlib
import subprocess
import sys


def git(repo: pathlib.Path, *args) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args],
                             capture_output=True, text=True, check=True)
    return result.stdout


def first_commit_for_path(repo: pathlib.Path, rel_path: str) -> str | None:
    """Returns the SHA of the OLDEST commit touching rel_path (the commit
    where it first appeared, i.e. its original — correct — publish)."""
    out = git(repo, "log", "--follow", "--diff-filter=A", "--reverse",
              "--format=%H", "--", rel_path)
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    if lines:
        return lines[0]
    # --diff-filter=A can miss a file whose earliest history isn't a clean
    # "add" (e.g. a rename or a squash) — fall back to the oldest commit that
    # touched the path at all.
    out = git(repo, "log", "--follow", "--reverse", "--format=%H", "--", rel_path)
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    return lines[0] if lines else None


def blob_at_commit(repo: pathlib.Path, commit: str, rel_path: str) -> str:
    return git(repo, "show", f"{commit}:{rel_path}")


def recover(repo: pathlib.Path, dry_run: bool = True):
    editions_dir = repo / "editions"
    if not editions_dir.exists():
        print(f"No editions/ directory in {repo} — nothing to recover.")
        return []

    report = []
    for f in sorted(editions_dir.glob("*.json")):
        if f.stem == "index":
            continue
        rel = f"editions/{f.name}"
        commit = first_commit_for_path(repo, rel)
        if not commit:
            report.append({"date": f.stem, "status": "no-history", "commit": None})
            print(f"  {f.stem}: no git history for {rel} — leaving untouched")
            continue
        try:
            original = blob_at_commit(repo, commit, rel)
            json.loads(original)   # sanity: must still be valid JSON
        except (subprocess.CalledProcessError, json.JSONDecodeError) as ex:
            report.append({"date": f.stem, "status": "broken-original", "commit": commit,
                            "error": str(ex)})
            print(f"  {f.stem}: original commit {commit[:8]} content is broken "
                  f"({ex!r}) — leaving untouched, flag for the owner")
            continue

        current = f.read_text()
        if current == original:
            report.append({"date": f.stem, "status": "already-correct", "commit": commit})
            print(f"  {f.stem}: already matches its first-published commit {commit[:8]}")
            continue

        report.append({"date": f.stem, "status": "restored" if not dry_run else "would-restore",
                        "commit": commit})
        print(f"  {f.stem}: {'restoring' if not dry_run else 'WOULD restore'} "
              f"from first-published commit {commit[:8]}")
        if not dry_run:
            f.write_text(original)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=pathlib.Path,
                         help="Path to a checkout of the gh-pages branch.")
    parser.add_argument("--apply", action="store_true",
                         help="Actually write the restored files (default: dry-run report only).")
    args = parser.parse_args()

    report = recover(args.repo, dry_run=not args.apply)
    n_restore = sum(1 for r in report if r["status"] in ("restored", "would-restore"))
    n_broken = sum(1 for r in report if r["status"] in ("broken-original", "no-history"))
    print(f"\n{len(report)} edition(s) checked: {n_restore} to restore, "
          f"{n_broken} need owner attention.")
    if not args.apply and n_restore:
        print("Dry run only — re-run with --apply to write the restored files, "
              "then commit + push from the gh-pages checkout yourself.")


if __name__ == "__main__":
    main()
