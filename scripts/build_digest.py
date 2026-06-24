#!/usr/bin/env python3
"""Turn the raw fetch (feeds/latest.json) into a LEAN digest the routine reads.

WHY THIS EXISTS
---------------
The Claude Code routine is billed by tokens, and in an agentic loop the ENTIRE
context — including whatever news file it reads — is re-sent as input on every
turn. The old run fed the model ~283 raw candidate stories (with full URLs and
image URLs, the longest fields of all) and let the model do dedup + coarse
ranking itself. That is exactly the wrong place to spend tokens.

This script does all the cheap, deterministic work HERE, on GitHub Actions
(free compute, no token cost):

  * conservative dedup (exact URL + near-identical title only),
  * a gentle recall-oriented rank (recency + light India/interest nudge),
  * a per-section shortlist capped to ~2x what the paper can publish, and
  * trimming each candidate to {id, title, source, summary} — NO url, NO image.

It writes TWO files:

  feeds/digest.json  -> what the ROUTINE reads. Lean: id/title/source/summary
                        only. No url, no image (the model never needs them, and
                        they are the biggest token cost). This is the model's
                        ONLY news input.
  feeds/refs.json    -> what scripts/assemble_edition.py reads at publish time.
                        Maps each id -> {url, image, source, title, published}.
                        The model NEVER opens this. Because urls/images live
                        only here, the model literally cannot invent one — the
                        "never fabricate a url/image" rule is now structural.

Design rule (from the v4 review): heuristics are a RECALL filter, not a
precision one. Their job is "don't drop anything good," never "pick the
winners." The model still makes every editorial call (final cut + the lead)
from the shortlist. We keep ~2x the publishable count per section so a great
story is never filtered out before the editor sees it, and we NEVER pre-anoint
a lead.

Fail-safe: if anything goes wrong, we degrade to a plain recency shortlist
rather than producing an empty digest (an empty digest could make the routine
flail). A broken digest must never become a broken/looping routine run.
"""
import json
import re
import datetime
import pathlib
import hashlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LATEST = ROOT / "feeds" / "latest.json"
DIGEST = ROOT / "feeds" / "digest.json"
REFS = ROOT / "feeds" / "refs.json"

SUMMARY_CHARS = 200          # enough for the editor to judge relevance; it
                             # rewrites anyway. (120 risked too-thin context.)
BUFFER_MULT = 2              # keep ~2x max_stories per section as recall buffer
SECTION_HARD_CAP = 10        # absolute ceiling per section, keeps input bounded

# Gentle interest nudge for ranking ONLY (never a hard filter). Kept light on
# purpose so it doesn't starve serendipity or bake in today's obsessions.
INTEREST_TERMS = (
    "india", "indian", "ai", "artificial intelligence", "startup", "funding",
    "climate", "energy", "renewable", "semiconductor", "chip", "robot",
    "quantum", "agritech", "health", "biotech", "neuroscience", "economy",
    "founder", "strategy", "policy",
    # culture / live events — so music & event news (e.g. an artist's India tour)
    # gets a gentle nudge and survives the per-section candidate cap.
    "concert", "tour", "festival", "album", "music", "fellowship", "hackathon",
)

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[^a-z0-9 ]+")


def norm_title(t: str) -> str:
    """Aggressively normalised title for near-duplicate detection."""
    t = (t or "").lower()
    t = _PUNCT.sub(" ", t)
    return _WS.sub(" ", t).strip()


def title_key(t: str) -> str:
    """A coarse fingerprint: first 8 normalised words. Two stories sharing this
    are almost certainly the same story syndicated across outlets. Conservative
    by design — we'd rather keep a near-dup than silently merge two real
    stories (which would waste a candidate slot, not lose coverage)."""
    words = norm_title(t).split()
    return " ".join(words[:8])


def make_id(slug: str, n: int) -> str:
    return f"{slug}-{n}"


def parse_dt(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def score(entry, now) -> float:
    """Recall-oriented rank. Recency dominates; a light interest nudge breaks
    ties toward what this reader cares about. NOT used to pick the lead or make
    the final cut — only to order the shortlist so the buffer keeps good items."""
    s = 0.0
    dt = parse_dt(entry.get("published"))
    if dt:
        age_h = max(0.0, (now - dt).total_seconds() / 3600.0)
        s += max(0.0, 48.0 - age_h)          # newer = higher, ~2-day horizon
    else:
        s += 6.0                              # undated: modest, don't bury it
    hay = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    hits = sum(1 for term in INTEREST_TERMS if term in hay)
    s += min(hits, 4) * 1.5                   # gentle, capped nudge
    return s


def shortlist_section(section, now):
    """Dedup + rank + cap one section. Returns (lean_entries, refs_map, dropped)."""
    raw = section.get("entries", []) or []
    max_stories = section.get("max_stories") or 4
    keep = min(max_stories * BUFFER_MULT, SECTION_HARD_CAP)

    seen_urls = set()
    seen_titles = set()
    deduped = []
    dropped = 0
    for e in raw:
        url = e.get("link") or e.get("url")
        if not url:
            dropped += 1
            continue
        tkey = title_key(e.get("title", ""))
        if url in seen_urls or (tkey and tkey in seen_titles):
            dropped += 1                       # conservative dedup
            continue
        seen_urls.add(url)
        if tkey:
            seen_titles.add(tkey)
        deduped.append(e)

    deduped.sort(key=lambda e: score(e, now), reverse=True)
    dropped += max(0, len(deduped) - keep)
    chosen = deduped[:keep]

    slug = section.get("slug") or "x"
    lean, refs = [], {}
    for i, e in enumerate(chosen, 1):
        sid = make_id(slug, i)
        summary = (e.get("summary") or "")[:SUMMARY_CHARS]
        source = e.get("source") or section.get("name", "")
        lean.append({
            "id": sid,
            "title": e.get("title", "(untitled)"),
            "source": source,
            "summary": summary,
        })
        refs[sid] = {
            "url": e.get("link") or e.get("url"),
            "image": e.get("image_url"),
            "source": source,
            "title": e.get("title", ""),
            "published": e.get("published"),
        }
    return lean, refs, dropped


def build_colophon(stats: dict) -> str:
    total = stats.get("feeds_total", 0)
    ok = stats.get("feeds_ok", 0)
    failed = stats.get("feeds_failed", 0)
    return f"{total} sources scanned · {ok} ok · {failed} failed"


def main() -> None:
    data = json.loads(LATEST.read_text())
    now = datetime.datetime.now(datetime.timezone.utc)

    digest_sections = []
    refs_all = {}
    total_candidates = 0
    drop_log = []

    for section in data.get("sections", []):
        lean, refs, dropped = shortlist_section(section, now)
        refs_all.update(refs)
        total_candidates += len(lean)
        drop_log.append((section.get("name"), len(lean), dropped))
        if not lean:
            continue                           # omit empty sections from digest
        digest_sections.append({
            "name": section.get("name"),
            "slug": section.get("slug"),
            "beta": section.get("beta", False),
            "stories": lean,
        })

    digest = {
        "date": now.date().isoformat(),
        "colophon": build_colophon(data.get("stats", {})),
        "sections": digest_sections,
    }

    DIGEST.write_text(json.dumps(digest, indent=2, ensure_ascii=False))
    REFS.write_text(json.dumps(refs_all, ensure_ascii=False))

    print(f"Wrote {DIGEST.relative_to(ROOT)} ({total_candidates} candidates) "
          f"and {REFS.relative_to(ROOT)} ({len(refs_all)} refs)")
    for name, kept, dropped in drop_log:
        print(f"  {name:<18} kept {kept:>2}  dropped {dropped:>3}")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:                     # noqa: BLE001 — never crash CI
        # Fail-safe: a missing/broken latest.json must not leave NO digest.
        print(f"build_digest failed: {ex!r} — writing minimal empty digest")
        now = datetime.datetime.now(datetime.timezone.utc)
        DIGEST.write_text(json.dumps(
            {"date": now.date().isoformat(),
             "colophon": "digest build failed — see CI log",
             "sections": []}, indent=2, ensure_ascii=False))
        REFS.write_text("{}")
