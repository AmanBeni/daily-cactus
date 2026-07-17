#!/usr/bin/env python3
"""B1 — full-text enrichment of shortlisted candidates.

Runs AFTER build_digest.py has already deduped, ranked, and shortlisted (so we
fetch at most a few dozen–~100 pages, never all ~280 raw candidates). For each
survivor, fetches the article page and extracts the main body text with
`trafilatura` (fallback: `readability-lxml` + a crude tag-stripper). The result
is capped to ~2500 chars and attached as `extract` on the digest entry so the
editor can write numbers-first summaries instead of working from a bare
headline + 200-char RSS blurb. 2500 chars comfortably covers the lede + key
numbers of a typical news article (raised from 700 — see RUN_AUDIT).

Never blocks the digest: any fetch/parse failure for a given story simply
means it keeps its RSS `summary` and gets no `extract` field. A slow or dead
site cannot break the pipeline; a per-request timeout (with one retry) and an
overall time budget cap the worst case.

Fix 2 (RUN_AUDIT_2026-07-17): both extractors were sending a bot-flavoured UA
(the raw `trafilatura.fetch_url` default, and an explicit `DailyCactusBot/1.0`
string). Several publishers (verified: Indian Express) bot-block that and
serve nothing/a stub, so extraction silently failed for those sources even
though the site was perfectly reachable. Fetching is now centralised in
`_fetch_html`: a real current-Chrome User-Agent, one retry on failure, then
BOTH trafilatura and readability parse that same already-fetched HTML (no
second network round-trip on the common path).
"""
import re
import ssl
import time
import urllib.request

EXTRACT_CHARS = 2500          # Fix 3: raised from 700 — captures lede + numbers
PER_REQUEST_TIMEOUT = 8       # seconds, per attempt
FETCH_RETRIES = 1             # Fix 2: one retry on a failed fetch
TOTAL_TIME_BUDGET = 240       # seconds — CI-friendly ceiling for the whole pass

# A full, current, realistic Chrome UA — several publishers (e.g. Indian
# Express) bot-block a generic/absent UA but let a browser-shaped one through.
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

_TAG = re.compile(r"<[^>]+>")

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = None


def _strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub(" ", html or "")).strip()


def _fetch_html(url: str) -> str | None:
    """Fetch a page's HTML with a real browser UA. One retry on any failure
    (network error, timeout, non-2xx). Returns None (never raises) if both
    attempts fail — callers degrade to the RSS summary."""
    headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    for attempt in range(FETCH_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=PER_REQUEST_TIMEOUT, context=_SSL_CTX) as resp:
                raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
        except Exception:
            if attempt < FETCH_RETRIES:
                continue
            return None
    return None


def _extract_trafilatura(html: str) -> str | None:
    import trafilatura
    return trafilatura.extract(html, include_comments=False,
                                include_tables=False, favor_recall=True)


def _extract_readability(html: str) -> str | None:
    from readability import Document
    doc = Document(html)
    return _strip_html(doc.summary())


def fetch_extract(url: str) -> str | None:
    if not url:
        return None
    html = _fetch_html(url)
    if not html:
        return None
    for fn in (_extract_trafilatura, _extract_readability):
        try:
            text = fn(html)
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
