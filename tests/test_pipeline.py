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


# --- P1: cross-day dedup via published editions -----------------------------
def test_load_published_urls_graceful_on_network_failure():
    import datetime as _dt
    old_url = bd.EDITIONS_BASE_URL
    bd.EDITIONS_BASE_URL = "https://this-domain-should-not-resolve.invalid/editions"
    try:
        urls, keys = bd.load_published_urls(_dt.datetime.now(_dt.timezone.utc))
        check("load_published_urls degrades to empty sets on network failure "
              "(never raises)", urls == set() and keys == set())
    finally:
        bd.EDITIONS_BASE_URL = old_url


# --- P2(e): same-event clustering --------------------------------------------
def test_event_signature_clusters_same_event():
    a = bd.event_signature("India-AI Impact Summit Kicks Off in New Delhi")
    b = bd.event_signature("PM Modi Inaugurates India-AI Impact Summit With 20 World Leaders")
    c = bd.event_signature("Day 2 of India-AI Impact Summit Focuses on AI Safety")
    check("differently-worded headlines about the same event share a signature",
          a == b == c and a != "")


def test_event_signature_distinct_for_unrelated_stories():
    sig1 = bd.event_signature("India-AI Impact Summit Kicks Off in New Delhi")
    sig2 = bd.event_signature("Sarvam AI Becomes Newest Unicorn With $234M Round")
    check("unrelated stories get a distinct (or empty) signature", sig1 != sig2)


def test_event_cap_caps_flooding_without_collapsing_unrelated():
    now = datetime.datetime(2026, 7, 18, tzinfo=datetime.timezone.utc)
    raw = [
        {"title": "India-AI Impact Summit Kicks Off in New Delhi", "link": "https://a.com/1", "source": "A", "summary": "", "published": now.isoformat()},
        {"title": "PM Modi Inaugurates India-AI Impact Summit With 20 World Leaders", "link": "https://a.com/2", "source": "B", "summary": "", "published": now.isoformat()},
        {"title": "Day 2 of India-AI Impact Summit Focuses on AI Safety", "link": "https://a.com/3", "source": "C", "summary": "", "published": now.isoformat()},
        {"title": "India-AI Impact Summit Closes With AI Commons Proposal", "link": "https://a.com/4", "source": "D", "summary": "", "published": now.isoformat()},
        {"title": "OpenAI Raises $40B At $300B Valuation", "link": "https://b.com/1", "source": "E", "summary": "", "published": now.isoformat()},
        {"title": "Sarvam AI Becomes Newest Unicorn With $234M Round", "link": "https://b.com/2", "source": "F", "summary": "", "published": now.isoformat()},
    ]
    section = {"slug": "ai", "name": "AI", "max_stories": 10, "window_hours": 96, "entries": raw}
    lean, refs, dropped, cross_day, feed_stats = bd.shortlist_section(section, now, set(), set(), 2026)
    kept_titles = {s["title"] for s in lean}
    check("4 same-event stories capped to EVENT_CAP_PER_SECTION",
          sum(1 for t in kept_titles if "India-AI Impact Summit" in t) == bd.EVENT_CAP_PER_SECTION)
    check("unrelated stories in the same batch are untouched",
          "OpenAI Raises $40B At $300B Valuation" in kept_titles and
          "Sarvam AI Becomes Newest Unicorn With $234M Round" in kept_titles)


# --- P2(c): article-date trust over feed date --------------------------------
def test_stale_article_date_drops_story():
    now = datetime.datetime(2026, 7, 18, tzinfo=datetime.timezone.utc)
    refs_today = {"india-x": {"url": "https://example.com/x", "published": now.isoformat(),
                               "source": "example.com", "title": "Old event, fresh feed date"}}
    digest_sections = [{"slug": "india", "stories": [
        {"id": "india-x", "title": "Old event, fresh feed date", "article_date": "2026-02-14"}
    ]}]
    dropped = bd.apply_article_date_corrections(digest_sections, refs_today, {"india": 96}, now)
    check("a story whose article_date is >7d older than the feed date, and now "
          "past the section's max-age cutoff, is dropped",
          dropped == 1 and digest_sections == [])
    check("the dropped story's ref is also removed (no dangling link)",
          "india-x" not in refs_today)


def test_fresh_article_date_agreement_keeps_story():
    now = datetime.datetime(2026, 7, 18, tzinfo=datetime.timezone.utc)
    refs_today = {"india-y": {"url": "https://example.com/y", "published": now.isoformat(),
                               "source": "example.com", "title": "Fresh story"}}
    digest_sections = [{"slug": "india", "stories": [
        {"id": "india-y", "title": "Fresh story", "article_date": now.date().isoformat()}
    ]}]
    dropped = bd.apply_article_date_corrections(digest_sections, refs_today, {"india": 96}, now)
    check("a story whose article_date agrees with the feed date is kept",
          dropped == 0 and len(digest_sections[0]["stories"]) == 1)
    check("article_date is stripped from the surviving story (not part of the "
          "lean digest contract the model reads)",
          "article_date" not in digest_sections[0]["stories"][0])


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAILURES)} failing check(s)" if FAILURES else "\nAll checks passed.")
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
