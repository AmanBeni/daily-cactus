#!/usr/bin/env python3
"""Option B, Stage 1.5 — full-text fetch for the SELECTED shortlist only.

WHY THIS EXISTS
---------------
The single-routine pipeline (build_digest.py -> ROUTINE_PROMPT.md) caps every
story to a ~2500-char extract because the editor sees ALL ~150 shortlisted
candidates in one read — full text for all of them would blow the token
budget. Option B splits the job in two: Routine A (ROUTINE_PROMPT_A.md) reads
the same lean digest and SELECTS ~25-40 ids worth a full read; THIS script
then fetches the FULL article text for just those, so Routine B
(ROUTINE_PROMPT_B.md) writes summaries from whole articles instead of
snippets, without re-reading hundreds of pages.

Runs on GitHub Actions (.github/workflows/select.yml), triggered by the push
of `selections/<date>.json` -- free compute, not token-billed.

REUSE, NOT REINVENT: the actual fetch (browser UA, retry, SSL context) and
the trafilatura/readability extraction live in scripts/enrich_shortlist.py
already (Fix 2/3 of RUN_AUDIT_2026-07-17). This script imports
`fetch_extract` from there with a much larger `max_chars` -- enrich_shortlist
itself is untouched apart from that one optional parameter (default
preserves its existing 2500-char behavior for the still-running single-
routine flow). `resolve_gnews.resolve` is reused too, as a safety net -- by
the time a story reaches refs/<date>.json its URL should already be resolved
(build_digest.py does that before writing refs), but a story pulled from the
UNION fallback could in principle predate that fix, so we resolve again here;
it's a no-op (returns the url unchanged) for anything that isn't a
news.google.com/rss/articles/... link.

SCHEMA NOTE (deliberate, additive extension of the brief): the task's minimum
schema for feeds/selected/<date>.json is `{"date":..., "stories": {...}}`. We
also carry the STRUCTURE fields (`lead`, `frontpage`, `sections`,
`opportunities`, `longform`) through verbatim from selections/<date>.json.
Without them, Routine B would have only a flat id->fulltext map and no way to
know which section/role each id was selected for (an id's own prefix reveals
its ORIGINAL digest section slug, e.g. "ai-xxx", but not whether Routine A
picked it as the lead, frontpage, a plain section story, an also-rail
one-liner, an opportunity, or a longform pick). Carrying the structure keeps
Routine B a genuine two-file read (feeds/selected + TASTE.md) instead of
needing to re-read selections/<date>.json itself.

Never crashes the pipeline: a story whose fetch fails still gets a `stories`
entry with `fulltext: ""` (Routine B falls back to headline/whatever prose it
can write for that one story). A missing/unparsable selections file writes a
placeholder feeds/selected/<date>.json with an empty `stories` map and exits
cleanly -- Routine B's own GUARD (see ROUTINE_PROMPT_B.md) handles that case
by falling back to feeds/digest.json.
"""
import datetime
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
SELECTIONS_DIR = ROOT / "selections"
REFS_DIR = ROOT / "feeds" / "refs"
REFS_LEGACY = ROOT / "feeds" / "refs.json"
SELECTED_DIR = ROOT / "feeds" / "selected"
DIGEST = ROOT / "feeds" / "digest.json"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from enrich_shortlist import fetch_extract   # reuse browser-UA fetch + extractors

try:
    from resolve_gnews import resolve as resolve_gnews_url   # safety net, see module docstring
except Exception:                                             # noqa: BLE001
    def resolve_gnews_url(url):
        return url

FULLTEXT_CHARS = 12_000        # generous: whole news articles, only truncates
                                # pathological longform (per the brief).
TOTAL_TIME_BUDGET = 480        # seconds, CI-friendly ceiling for the whole pass
                                # (fewer stories than enrich_shortlist.py's full
                                # shortlist, but each fetch can be a longer page).


def load_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except Exception:                                          # noqa: BLE001
        return default


def load_refs_for_date(date_str: str) -> dict:
    """Same precedence as assemble_edition.py::load_refs_for_date: legacy
    rolling union, then the union of all per-date snapshots, then THIS date's
    own snapshot taking final precedence. Hash ids make the union safe."""
    own = load_json(REFS_DIR / f"{date_str}.json", default={}) or {}
    union = {}
    if REFS_DIR.exists():
        for f in sorted(REFS_DIR.glob("*.json")):
            snap = load_json(f, default={}) or {}
            union.update(snap)
    legacy = load_json(REFS_LEGACY, default={}) or {}
    merged = {}
    merged.update(legacy)
    merged.update(union)
    merged.update(own)
    return merged


def load_digest_fallback() -> dict:
    """id -> best available snippet from the digest (the 2500-char `extract`,
    else the short RSS `summary`). Used when a full-article fetch is blocked
    (e.g. YourStory / Moneycontrol bot-block the scraper) so a PUBLISHED story
    still carries real body text instead of nothing — degraded, never empty."""
    d = load_json(DIGEST, default={}) or {}
    out = {}
    for sec in d.get("sections", []) or []:
        for st in sec.get("stories", []) or []:
            sid = st.get("id")
            if sid:
                out[sid] = st.get("extract") or st.get("summary") or ""
    return out


def collect_ids(sel: dict) -> tuple:
    """Flatten every id in the selection, de-duped and order-preserving.

    Returns (ids, lite_ids). `lite_ids` are the `also`-rail picks: they become
    ONE-LINERS in the paper, so fetching a whole article for them is wasted
    bandwidth and wasted writer context. They still get an entry (headline +
    the digest snippet) — just not the expensive full fetch. Anything that
    becomes a full card (lead, frontpage, section stories, opportunities,
    longform) still gets the whole article."""
    card_ids, also_ids, ids = set(), set(), []

    def add(i, is_also=False):
        if not i:
            return
        ids.append(i)
        (also_ids if is_also else card_ids).add(i)

    add(sel.get("lead"))
    for i in (sel.get("frontpage") or []):
        add(i)
    for sec in sel.get("sections", []) or []:
        for i in (sec.get("stories") or []):
            add(i)
        for i in (sec.get("also") or []):
            add(i, is_also=True)
    for i in (sel.get("opportunities") or []):
        add(i)
    for i in (sel.get("longform") or []):
        add(i)

    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    # lite = appears ONLY in an also rail. If the same id is also a full card
    # somewhere, it needs the whole article.
    lite = also_ids - card_ids
    return out, lite


def fetch_one(sid: str, refs: dict, fallbacks: dict, start: float, lite: bool = False) -> dict:
    """Never raises. Tries full article text; on failure degrades to the
    digest snippet (2500-char extract / RSS summary) rather than empty, so a
    published story is never left with only its headline. `text_source` records
    which won: "full" | "digest-extract" | "none"."""
    ref = refs.get(sid)
    if ref is None:
        return {"headline": "", "source": "", "url": "", "published": None,
                "image": None, "fulltext": "", "text_source": "none"}

    url = ref.get("url") or ""
    try:
        if url and "news.google.com/rss/articles" in url:
            url = resolve_gnews_url(url)
    except Exception:                                          # noqa: BLE001
        pass

    fulltext, source_kind = "", "none"
    if lite:
        # also-rail one-liner: the digest snippet is plenty, skip the fetch
        snippet = (fallbacks.get(sid) or "").strip()
        return {
            "headline": ref.get("title", ""), "source": ref.get("source", ""),
            "url": url, "published": ref.get("published"), "image": ref.get("image"),
            "fulltext": snippet, "text_source": "digest-extract" if snippet else "none",
            "lite": True,
        }
    if url and (time.time() - start) < TOTAL_TIME_BUDGET:
        try:
            fulltext = fetch_extract(url, max_chars=FULLTEXT_CHARS) or ""
        except Exception:                                      # noqa: BLE001
            fulltext = ""
    if fulltext:
        source_kind = "full"
    else:
        snippet = (fallbacks.get(sid) or "").strip()
        if snippet:
            fulltext, source_kind = snippet, "digest-extract"

    return {
        "headline": ref.get("title", ""),
        "source": ref.get("source", ""),
        "url": url,
        "published": ref.get("published"),
        "image": ref.get("image"),
        "fulltext": fulltext,
        "text_source": source_kind,
    }


def write_placeholder(date_str: str, reason: str) -> None:
    SELECTED_DIR.mkdir(parents=True, exist_ok=True)
    out = SELECTED_DIR / f"{date_str}.json"
    out.write_text(json.dumps(
        {"date": date_str, "stories": {}}, indent=2, ensure_ascii=False))
    print(f"fetch_selected: {reason} — wrote empty placeholder {out.relative_to(ROOT)}")


def main() -> None:
    date_arg = (sys.argv[1] if len(sys.argv) > 1
                else datetime.datetime.now(datetime.timezone.utc).date().isoformat())

    sel_path = SELECTIONS_DIR / f"{date_arg}.json"
    sel = load_json(sel_path, default=None)
    if not isinstance(sel, dict):
        write_placeholder(date_arg, f"no valid selections file at {sel_path.relative_to(ROOT)}")
        return

    date = sel.get("date") or date_arg
    refs = load_refs_for_date(date)
    ids, lite_ids = collect_ids(sel)

    if not ids:
        write_placeholder(date, "selections file had no ids")
        return

    fallbacks = load_digest_fallback()
    start = time.time()
    got_fulltext = got_fallback = got_none = 0
    stories = {}
    for sid in ids:
        entry = fetch_one(sid, refs, fallbacks, start, lite=(sid in lite_ids))
        if entry["text_source"] == "full":
            got_fulltext += 1
        elif entry["text_source"] == "digest-extract":
            got_fallback += 1
        else:
            got_none += 1
        stories[sid] = entry

    out = {
        "date": date,
        # structure carried through verbatim (see module docstring) so Routine
        # B knows placement without a second read.
        "lead": sel.get("lead"),
        "frontpage": sel.get("frontpage") or [],
        "sections": sel.get("sections") or [],
        "opportunities": sel.get("opportunities") or [],
        "longform": sel.get("longform") or [],
        "stories": stories,
    }

    SELECTED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SELECTED_DIR / f"{date}.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    total = len(ids)
    size_chars = len(json.dumps(out, ensure_ascii=False))
    covered = got_fulltext + got_fallback
    print(f"fetch_selected: wrote {out_path.relative_to(ROOT)} — "
          f"{got_fulltext}/{total} full text, {got_fallback} digest-extract fallback, "
          f"{got_none} headline-only ({covered}/{total} with body text); "
          f"{size_chars} chars (~{size_chars // 4} est. tokens)")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:                                    # noqa: BLE001
        print(f"fetch_selected failed: {ex!r} — writing empty placeholder")
        fallback_date = (sys.argv[1] if len(sys.argv) > 1
                          else datetime.datetime.now(datetime.timezone.utc).date().isoformat())
        try:
            write_placeholder(fallback_date, "unhandled exception")
        except Exception:                                      # noqa: BLE001
            pass
        sys.exit(1)   # non-zero exit -> select.yml can flag a health issue
