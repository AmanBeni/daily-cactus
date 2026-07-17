#!/usr/bin/env python3
"""B8 — summarize feeds/feed_stats.jsonl into a per-feed hit-rate report.

Zero model cost: aggregates the fetched->shortlisted counts build_digest.py
has been appending daily, over the last N days, and prints a markdown table
(stdout) that audit.yml posts as a GitHub issue. Flags feeds with a 0%
shortlist rate over enough samples as prune candidates — evidence, not vibes.
"""
import argparse
import datetime
import json
import pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
FEED_STATS = ROOT / "feeds" / "feed_stats.jsonl"

MIN_SAMPLES_TO_FLAG = 10   # don't judge a feed on a handful of fetches


def load_rows(days: int):
    if not FEED_STATS.exists():
        return []
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    rows = []
    for line in FEED_STATS.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            d = datetime.date.fromisoformat(row.get("date", ""))
        except ValueError:
            continue
        if d >= cutoff:
            rows.append(row)
    return rows


def summarize(rows):
    agg = defaultdict(lambda: {"fetched": 0, "shortlisted": 0, "section": ""})
    for r in rows:
        key = r["feed_url"]
        agg[key]["fetched"] += r.get("fetched", 0)
        agg[key]["shortlisted"] += r.get("shortlisted", 0)
        agg[key]["section"] = r.get("section", "")
    return agg


def render_markdown(agg: dict) -> str:
    lines = ["| Section | Feed | Fetched | Shortlisted | Hit rate |",
             "|---|---|---:|---:|---:|"]
    prune_candidates = []
    for url, stats in sorted(agg.items(), key=lambda kv: kv[1]["section"]):
        fetched, shortlisted = stats["fetched"], stats["shortlisted"]
        rate = (shortlisted / fetched * 100) if fetched else 0.0
        short_url = url if len(url) < 70 else url[:67] + "..."
        lines.append(f"| {stats['section']} | {short_url} | {fetched} | {shortlisted} | {rate:.0f}% |")
        if fetched >= MIN_SAMPLES_TO_FLAG and shortlisted == 0:
            prune_candidates.append((stats["section"], url, fetched))

    out = "\n".join(lines)
    if prune_candidates:
        out += f"\n\n### Prune candidates (0% hit rate, >={MIN_SAMPLES_TO_FLAG} samples)\n"
        for section, url, fetched in prune_candidates:
            out += f"- **{section}**: {url} ({fetched} fetched, 0 ever shortlisted)\n"
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    rows = load_rows(args.days)
    if not rows:
        print(f"No feed_stats.jsonl rows in the last {args.days} days.")
        return
    agg = summarize(rows)
    print(render_markdown(agg))


if __name__ == "__main__":
    main()
