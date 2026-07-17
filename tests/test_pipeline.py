#!/usr/bin/env python3
"""Plain-python (no pytest) unit tests for the v2 pipeline changes.

Run directly:  python3 tests/test_pipeline.py
Exits non-zero (and prints FAIL lines) on any failure, so it's CI-usable
without adding a pytest dependency.
"""
import datetime
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_digest as bd  # noqa: E402

FAILURES = []


def check(name, cond):
    status = "ok" if cond else "FAIL"
    print(f"[{status}] {name}")
    if not cond:
        FAILURES.append(name)


# --- A1: hash-id stability -------------------------------------------------
def test_hash_id_stable():
    url = "https://example.com/some-article-slug"
    id1 = bd.make_id("ai", url)
    id2 = bd.make_id("ai", url)
    check("hash id is deterministic for the same URL", id1 == id2)
    check("hash id carries the section slug prefix", id1.startswith("ai-"))
    id3 = bd.make_id("ai", url + "?utm_source=x")
    check("hash id differs for a different URL", id1 != id3)


# --- A5: date hygiene -------------------------------------------------------
def test_max_age_hard_cutoff():
    now = datetime.datetime(2026, 7, 14, tzinfo=datetime.timezone.utc)
    stale = {"title": "Old story", "summary": "", "published":
             (now - datetime.timedelta(hours=200)).isoformat()}
    fresh = {"title": "Fresh story", "summary": "", "published":
             (now - datetime.timedelta(hours=2)).isoformat()}
    check("a story older than max_age_hours scores -inf (hard cut)",
          bd.score(stale, now, max_age_hours=96) == float("-inf"))
    check("a fresh story within max_age_hours scores a real number",
          bd.score(fresh, now, max_age_hours=96) > 0)


def test_undated_penalized_not_dropped():
    now = datetime.datetime(2026, 7, 14, tzinfo=datetime.timezone.utc)
    undated = {"title": "No date story", "summary": ""}
    fresh = {"title": "Fresh story", "summary": "", "published": now.isoformat()}
    s_undated = bd.score(undated, now, max_age_hours=96)
    s_fresh = bd.score(fresh, now, max_age_hours=96)
    check("undated entries are NOT hard-dropped by max_age (no crash / -inf)",
          s_undated != float("-inf"))
    check("undated entries score lower than an equally-fresh dated one",
          s_undated < s_fresh)


def test_event_date_extraction_drops_past_events():
    ref_year = 2026
    now = datetime.date(2026, 7, 14)
    past = bd.extract_event_date("Join us on 12 February for the big summit", ref_year)
    future = bd.extract_event_date("Join us on 20 August for the big summit", ref_year)
    check("extract_event_date parses a past date", past == datetime.date(2026, 2, 12))
    check("extract_event_date parses a future date", future == datetime.date(2026, 8, 20))
    check("past event date is before 'now' (would be hard-dropped in shortlist)",
          past < now)
    check("future event date is not before 'now'", not (future < now))


def test_event_date_extraction_month_first_format():
    d = bd.extract_event_date("The conference runs July 20, 2026 in Delhi", 2026)
    check("extract_event_date parses 'Month D, YYYY' format", d == datetime.date(2026, 7, 20))


def test_event_date_no_match_returns_none():
    d = bd.extract_event_date("A story with no date mentioned at all", 2026)
    check("extract_event_date returns None when nothing matches", d is None)


# --- A4: cross-day dedup building blocks ------------------------------------
def test_title_key_dedup_matching():
    a = bd.title_key("OpenAI announces GPT-6 with major upgrades to reasoning")
    b = bd.title_key("OpenAI announces GPT-6 with major upgrades to reasoning capability today")
    check("title_key matches on shared first-8-word prefix", a == b)


# --- B2: buzz + source weight sanity ----------------------------------------
def test_buzz_bonus_capped():
    now = datetime.datetime(2026, 7, 14, tzinfo=datetime.timezone.utc)
    base = {"title": "x", "summary": "", "published": now.isoformat(), "_buzz": 1}
    buzzy = {"title": "x", "summary": "", "published": now.isoformat(), "_buzz": 20}
    check("higher buzz scores at least as high as no buzz",
          bd.score(buzzy, now) >= bd.score(base, now))
    # capped at min(buzz-1, 4) * 0.8 == 3.2 max bonus
    check("buzz bonus is capped (huge buzz != unbounded score)",
          bd.score(buzzy, now) - bd.score(base, now) <= 3.21)


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAILURES)} failing check(s)" if FAILURES else "\nAll checks passed.")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
