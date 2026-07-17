#!/usr/bin/env python3
"""B4 — fold a week of 👍/👎 GitHub-issue feedback into TASTE.md.

Zero model calls (plain heuristic), per the owner's choice. Reads a JSON list
of feedback events from stdin (produced by the taste.yml workflow's
github-script step, one entry per 'feedback' labeled issue):

    [{"story_id": "2026-07-14/ai/2", "vote": "up"}, ...]

The story id tells us the section. The renderer (site/app.js) emits feedback
ids as `<date>/<section-slug>/<tag>` (front-page/lead stories carry their
resolved home-section slug; only an unmatched lead falls back to `front`), so
the MIDDLE segment is the section. A legacy `<slug>-<hash>` id is also still
understood. Non-topic scopes (`front`, `opportunities`, `unknown`) are ignored.
Tallies votes per section over the batch, then REPLACES (never accumulates)
a single auto-generated line per section in TASTE.md's "More of"/"Less of"
sections, marked with an HTML comment so re-runs prune the old line instead
of piling up. Sections with a mixed/neutral signal get no line at all — this
is a nudge, not a rewrite of the owner's hand-written preferences (which stay
untouched above/below the auto block).

Keeps TASTE.md's line budget: only sections with a CLEAR lean (>=70% one way,
>=3 votes) get a line, and at most 5 lines total, so the file cannot grow
without bound.
"""
import json
import re
import sys
import pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
TASTE = ROOT / "TASTE.md"

AUTO_START = "<!-- AUTO-FEEDBACK:START -->"
AUTO_END = "<!-- AUTO-FEEDBACK:END -->"
MIN_VOTES = 3
LEAN_THRESHOLD = 0.7
MAX_LINES = 5


NON_TOPIC = {"front", "opportunities", "unknown", ""}


def section_of(story_id: str) -> str:
    """Section slug from a feedback id. New format `<date>/<slug>/<tag>` -> the
    middle segment; legacy `<slug>-<hash>` -> strip the hash. Non-topic scopes
    (front page with no resolved home section, opportunities) -> 'unknown'."""
    if not story_id:
        return "unknown"
    if "/" in story_id:
        parts = story_id.split("/")
        scope = parts[1] if len(parts) >= 3 else ""
        return scope if scope not in NON_TOPIC else "unknown"
    return re.sub(r"-[0-9a-f]{10}$", "", story_id)


def summarize(events):
    tally = defaultdict(lambda: {"up": 0, "down": 0})
    for e in events:
        sid = e.get("story_id", "")
        vote = e.get("vote")
        if vote not in ("up", "down"):
            continue
        tally[section_of(sid)][vote] += 1

    lines = []
    for section, counts in sorted(tally.items()):
        if section == "unknown":
            continue                      # non-topic votes: captured, not folded
        total = counts["up"] + counts["down"]
        if total < MIN_VOTES:
            continue
        up_ratio = counts["up"] / total
        if up_ratio >= LEAN_THRESHOLD:
            lines.append(f"- (feedback signal) more of **{section}** — "
                          f"{counts['up']}↑/{counts['down']}↓ this week")
        elif (1 - up_ratio) >= LEAN_THRESHOLD:
            lines.append(f"- (feedback signal) less of **{section}** — "
                          f"{counts['up']}↑/{counts['down']}↓ this week")
    return lines[:MAX_LINES]


def apply(taste_text: str, lines: list) -> str:
    block = "\n".join([AUTO_START, *lines, AUTO_END]) if lines else f"{AUTO_START}\n{AUTO_END}"
    if AUTO_START in taste_text and AUTO_END in taste_text:
        pattern = re.compile(re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END), re.S)
        return pattern.sub(block, taste_text)
    # First run: append the block under "## More of" as a clearly-marked addendum.
    marker = "## More of"
    if marker in taste_text:
        return taste_text.replace(marker, f"{marker}\n{block}", 1)
    return taste_text.rstrip() + f"\n\n{block}\n"


def main():
    raw = sys.stdin.read()
    events = json.loads(raw) if raw.strip() else []
    lines = summarize(events)
    text = TASTE.read_text() if TASTE.exists() else "# TASTE\n\n## More of\n"
    updated = apply(text, lines)
    TASTE.write_text(updated)
    print(f"Folded {len(events)} feedback event(s) into TASTE.md: {len(lines)} signal line(s).")


if __name__ == "__main__":
    main()
