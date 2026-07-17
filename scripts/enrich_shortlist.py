#!/usr/bin/env python3
"""B1 — full-text enrichment of shortlisted candidates.

Runs AFTER build_digest.py has already deduped, ranked, and shortlisted (so we
fetch at most a few dozen–~100 pages, never all ~280 raw candidates). For each
survivor, fetches the article page and extracts the main body text with
`trafilatura` (fallback: `readability-lxml` + a crude tag-stripper). The result
is capped to ~700 chars and attached as `extract` on the digest entry so the
editor can write numbers-first summaries instead of working from a bare
headline + 200-char RSS blurb.

Never blocks the digest: any fetch/parse failure for a given story simply
means it keeps its RSS `summary` and gets no `extract` field. A slow or dead
site cannot break the pipeline; a per-story timeout and an overall time budget
cap the worst case.
"""
import re
import ssl
import time
import pathlib

EXTRACT_CHARS = 700
PER_REQUEST_TIMEOUT = 8          # seconds
TOTAL_TIME_BUDGET = 240          # seconds — CI-friendly ceiling for the whole pass

_TAG = re.compile(r"<[^>]+>")

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = None


def _strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub(" ", html or "")).strip()


def _extract_trafilatura(url: str) -> str | None:
    import trafilatura
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    text = trafilatura.extract(downloaded, include_comments=False,
                                include_tables=False, favor_recall=True)
    return text


def _extract_readability(url: str) -> str | None:
    import urllib.request
    from readability import Document
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; DailyCactusBot/1.0)"})
    with urllib.request.urlopen(req, timeout=PER_REQUEST_TIMEOUT, context=_SSL_CTX) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    doc = Document(raw)
    return _strip_html(doc.summary())


def fetch_extract(url: str) -> str | None:
    if not url:
        return None
    for fn in (_extract_trafilatura, _extract_readability):
        try:
            text = fn(url)
            if text and text.strip():
                return text.strip()[:EXTRACT_CHARS]
        except Exception:
            continue
    return None


def enrich_sections(digest_sections, refs_today):
    """Mutates and returns digest_sections, adding `extract` where possible.
    Time-boxed across the whole call so a run of dead/slow sites degrades
    gracefully instead of stalling the pipeline."""
    start = time.time()
    fetched = skipped = failed = 0
    for section in digest_sections:
        for story in section.get("stories", []):
            if time.time() - start > TOTAL_TIME_BUDGET:
                skipped += 1
                continue
            ref = refs_today.get(story.get("id"), {})
            url = ref.get("url")
            extract = fetch_extract(url)
            if extract:
                story["extract"] = extract
                fetched += 1
            else:
                failed += 1
    print(f"enrich_shortlist: {fetched} extracted, {failed} fell back to RSS "
          f"summary, {skipped} skipped (time budget)")
    return digest_sections


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.bbc.com/news"
    print(fetch_extract(url))
