#!/usr/bin/env python3
"""Expand the routine's lean DRAFT into the full edition JSON the renderer reads.

WHY THIS EXISTS
---------------
The routine writes the smallest thing it possibly can: a draft of story IDs +
the prose it wrote (headline/summary/signal). It writes NO urls, NO image
links, NO source strings, NO colophon, NO edition number. This:
  * minimises the model's OUTPUT tokens, and
  * makes fabricated urls/images structurally impossible — the model never emits
    one; we inject them here, verbatim, from a refs snapshot (built on GitHub
    Actions during the fetch).

This script runs at PUBLISH time (GitHub Actions, free compute).

A2 — per-date refs. Each draft resolves against ITS OWN date's
`feeds/refs/<date>.json` snapshot first. If an id isn't found there (e.g. the
snapshot has aged out, or a very old draft predates the refs/ directory), it
falls back to the UNION of all available snapshots (safe because ids are
content-hash based — same id always means the same URL — see build_digest.py
`make_id`), then to the legacy rolling `feeds/refs.json`.

A3 — editions are immutable. By default this script assembles ONLY drafts
that do not already have a published edition (checked against
`EXISTING_EDITIONS_DIR`, a checkout of gh-pages' `editions/` the workflow
provides). A never-before-seen draft is written for the first time; a draft
whose edition already exists is left untouched. Pass `--force <date>` (one or
more, or `--force all`) to deliberately rebuild specific dates — the only way
past editions change.

Idempotent within its own rules: re-running with the same inputs and the same
`--force` set produces the same output. If a draft is malformed we FAIL LOUDLY
(non-zero exit) so the deploy step does not ship a broken paper. If the model
references an unknown id, that single story is dropped with a warning rather
than crashing the whole edition.
"""
import argparse
import json
import re
import sys
import datetime
import pathlib
import os

ROOT = pathlib.Path(__file__).resolve().parent.parent
DRAFTS = ROOT / "drafts"
REFS_DIR = ROOT / "feeds" / "refs"                     # A2 per-date snapshots
REFS_FILE_LEGACY = ROOT / "feeds" / "refs.json"        # legacy rolling union
LATEST = ROOT / "feeds" / "latest.json"
DIGEST = ROOT / "feeds" / "digest.json"
MARKETS_FILE = ROOT / "feeds" / "markets.json"         # B5, optional
OUT_DIR = ROOT / "site" / "editions"

# A3: where the workflow checks out gh-pages' editions/ before we run, so we
# can tell which dates are already published. Override via env for testing.
EXISTING_EDITIONS_DIR = pathlib.Path(
    os.environ.get("EXISTING_EDITIONS_DIR", str(ROOT / "existing_editions" / "editions")))

# Edition numbering is deterministic — no stored counter to drift or corrupt.
# Seed: 2026-06-16 == edition 1 (so 2026-06-18 == edition 3, matching history).
EPOCH = datetime.date(2026, 6, 16)

# Wrong-link guard: if the editor's card shares NO significant word with the
# source title behind its id, the id was almost certainly mismatched — drop it.
#
# The check deliberately reads the WHOLE card (headline + summary + key_stat),
# not the headline alone. The prompt requires rewriting the outlet's clickbait
# into plain language, so a headline-only comparison punishes correct work: on
# 2026-07-22 it dropped the edition's entire lead because the editor's
# "Skyroot's Vikram-1 puts India in the private orbital-launch club" shares no
# 4+-letter non-stopword with SCMP's "SpaceX took 4 attempts. India's space
# start-up needed just 1" ("india" being a stopword here). A correct card
# always names the article's entities somewhere in its prose, so the wider
# comparison keeps the guard's real job — catching a mismatched id — while
# ending the false positives.
_WORD = re.compile(r"[a-z0-9]{4,}")
_STOP = {"with", "that", "this", "from", "have", "will", "into", "amid", "over",
         "after", "says", "said", "than", "then", "when", "what", "your", "their",
         "about", "more", "most", "also", "been", "could", "would", "year", "years",
         "india", "indian", "news", "report", "first", "global"}


def sig_tokens(s):
    return {w for w in _WORD.findall((s or "").lower()) if w not in _STOP}


def coerce_points(v):
    """v6 bullet summaries. A list of 3-5 short strings; anything else becomes
    an empty list so an older draft (summary-only) still assembles cleanly."""
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return []


# --- v6.1: derive hook + points server-side when the draft didn't supply them.
#
# The routine prompt lives in the Claude Code Routine's own configuration, NOT
# in this repo, so editing ROUTINE_PROMPT_B.md changes nothing until a human
# re-pastes it. That dependency silently produced two consecutive old-format
# editions (29 Jul, 01 Aug 2026). The format must not hinge on a manual step.
#
# So: if a story arrives with a `summary` and no `points`, split it here. A
# model-written hook/points is better prose and still wins when the prompt IS
# current — this is the floor, not the ceiling.
# Mirrors _SRC_FLAG_RE in site/app.js — the editor's provenance flags.
_SRC_FLAG_RE = re.compile(
    r"\((?:source unreachable[^)]*|summary from limited source text)\)\s*$", re.I)

_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z"“‘])')
# Deliberately not splitting on "$1.5B" or "Rs. 5" — the lookahead requires a
# capital letter or quote after the space, so a decimal or digit never splits.

_NUM_PHRASE = re.compile(
    r"(?:[$₹€£]\s?\d[\d,.]*\s?(?:bn|billion|million|trillion|crore|lakh|k|m|b)?"
    r"|\d[\d,.]*\s?%"
    r"|\d[\d,.]*\s?(?:bn|billion|million|trillion|crore|lakh|GW|MW|km|kg|tonnes?|x))",
    re.I)

MIN_POINTS = 2          # below this a bullet list is sillier than a paragraph
MAX_POINTS = 5

# Counts stories whose bullets this script had to derive. A non-zero count at
# the end of a run is the signal that Routine B is running a stale prompt.
DERIVED = {"count": 0, "total": 0}


def split_summary(summary: str):
    """(hook, points) from a single-paragraph summary, or (None, []) if it is
    too short or too thin to be worth splitting."""
    text = (summary or "").strip()
    if not text or _SRC_FLAG_RE.search(text):
        # Provenance-flagged summaries ("source unreachable — headline only")
        # are one honest sentence by design. Never bullet them.
        return None, []
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]
    if len(parts) < MIN_POINTS + 1:
        return None, []
    hook, rest = parts[0], parts[1:]
    if len(rest) > MAX_POINTS:
        # Fold the tail into the last bullet rather than dropping any of it —
        # never silently lose text the editor wrote.
        rest = rest[:MAX_POINTS - 1] + [" ".join(rest[MAX_POINTS - 1:])]
    return hook, rest


def auto_highlight(text: str) -> str:
    """Wrap the first number-bearing phrase in ==markers== so the yellow pen
    appears even when the editor didn't mark anything. No-op if the editor
    already marked this field, or if there is no number to point at."""
    t = str(text or "")
    if not t or "==" in t:
        return t
    m = _NUM_PHRASE.search(t)
    if not m:
        return t
    return f"{t[:m.start()]}=={m.group(0)}=={t[m.end():]}"


def coerce_signal(v):
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def load_json(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text())
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as ex:
        raise SystemExit(f"FATAL: {path} is not valid JSON: {ex}")


def edition_number(date_str: str) -> int:
    try:
        d = datetime.date.fromisoformat(date_str)
        return max(1, (d - EPOCH).days + 1)
    except ValueError:
        return 1


def slug_to_name(refs_digest):
    m = {}
    for s in (refs_digest or {}).get("sections", []) or []:
        if s.get("slug"):
            m[s["slug"]] = s.get("name", s["slug"].title())
    return m


def load_refs_for_date(date_str: str) -> dict:
    """A2: this date's own snapshot, falling back to the union of every other
    available snapshot, then the legacy rolling refs.json. Hash ids make the
    union safe — an id collision across dates would mean the same URL."""
    own = load_json(REFS_DIR / f"{date_str}.json", default=None)
    union = {}
    if REFS_DIR.exists():
        for f in sorted(REFS_DIR.glob("*.json")):
            snap = load_json(f, default={}) or {}
            union.update(snap)
    legacy = load_json(REFS_FILE_LEGACY, default={}) or {}
    merged = {}
    merged.update(legacy)
    merged.update(union)
    if own:
        merged.update(own)   # own-date snapshot takes precedence when present
    return merged


def build_story(item, refs, warnings):
    """Merge model prose with the verbatim url/image/source from refs[id]."""
    sid = item.get("id")
    ref = refs.get(sid)
    if ref is None:
        warnings.append(f"unknown story id {sid!r} — dropped")
        return None
    headline = item.get("headline", ref.get("title", ""))
    card_text = " ".join(str(x) for x in (
        headline,
        item.get("summary", ""),
        " ".join(coerce_points(item.get("points"))),
        item.get("hook", ""),
        item.get("key_stat", ""),
    ) if x)
    ctok, rtok = sig_tokens(card_text), sig_tokens(ref.get("title", ""))
    # WARN, never drop. Replayed against 221 real story items from the five
    # editions of 19-28 Jul 2026, this check fired 6 times and was wrong all 6
    # — its precision on real data is zero, because an abstract source title
    # ("AI monetization, model efficiency, and India's infrastructure gap")
    # legitimately shares no token with a plain-language rewrite ("AI earnings
    # season shows real revenue"). Silently deleting a correct story — once an
    # entire edition's lead — is a far worse failure than shipping a warning.
    # The link itself is still safe by construction: urls come from the refs
    # snapshot, never from the model, so the worst case here is a card whose
    # id was mistyped, which this warning surfaces for a human to check.
    if ctok and len(rtok) >= 2 and not (ctok & rtok):
        warnings.append(f"id {sid!r}: card shares no word with its source title "
                        f"— CHECK THE LINK ({headline[:50]!r} vs "
                        f"{ref.get('title','')[:50]!r})")
    story = {
        "headline": headline,
        "summary": item.get("summary", ""),
        "signal": coerce_signal(item.get("signal")),
        "badge": (item.get("badge") or "").strip(),
        # legacy fields kept for older drafts that still send them
        "takeaway": item.get("takeaway", ""),
        "why": item.get("why", ""),
        "source": ref.get("source", ""),
        "url": ref.get("url"),
        "image": ref.get("image"),
        "developing": bool(item.get("developing", False)),
    }
    # v6 bullet summary — additive. `hook` is the one-line numbers-first
    # opener, `points` the 3-5 bullets under it. The renderer falls back to
    # `summary` whenever `points` is absent, so every already-published
    # edition keeps rendering exactly as it does today.
    hook = (item.get("hook") or "").strip()
    points = coerce_points(item.get("points"))
    if not points:
        # v6.1 fallback: the editor sent an old-format single-paragraph
        # summary. Split it here rather than shipping a wall of text.
        derived_hook, derived_points = split_summary(story["summary"])
        if derived_points:
            hook = hook or derived_hook
            points = derived_points
            story["summary"] = ""      # the bullets now carry it; don't double up
            DERIVED["count"] += 1
    # The yellow pen should not depend on a hand-pasted prompt either.
    hook = auto_highlight(hook)
    story["headline"] = auto_highlight(story["headline"])
    if hook:
        story["hook"] = hook
    if points:
        story["points"] = points

    # B3 optional fields — additive, renderer must degrade gracefully if absent.
    if item.get("key_stat"):
        story["key_stat"] = str(item["key_stat"]).strip()
    if item.get("editors_read"):
        story["editors_read"] = str(item["editors_read"]).strip()
    rail = build_also_rail(item.get("also"), refs, warnings)
    if rail:
        story["also"] = rail
    return story


def build_also_rail(also, refs, warnings):
    """Resolve a list of {id, line} one-liners into rail entries with urls.
    Used for both the section-level rail (the shape the prompt asks for) and
    the legacy story-level one."""
    if not isinstance(also, list) or not also:
        return []
    out = []
    for a in also:
        aid = a.get("id") if isinstance(a, dict) else None
        aref = refs.get(aid) if aid else None
        if not aref:
            warnings.append(f"'also' id {aid!r} unknown — dropped from rail")
            continue
        line = (a.get("line") or "").strip()
        if not line:
            warnings.append(f"'also' id {aid!r} has no line — dropped from rail")
            continue
        out.append({
            "line": line,
            "source": aref.get("source", ""),
            "url": aref.get("url"),
        })
    return out


def build_opp(item, refs, warnings):
    sid = item.get("id")
    ref = refs.get(sid, {})
    if sid and ref == {}:
        warnings.append(f"unknown opportunity id {sid!r} — using draft fields only")
    return {
        "name": item.get("name", ref.get("title", "")),
        "when": item.get("when", ""),
        "summary": item.get("summary", ""),
        "source": ref.get("source", ""),
        "url": ref.get("url"),
    }


def existing_edition_dates() -> set:
    if not EXISTING_EDITIONS_DIR.exists():
        return set()
    return {f.stem for f in EXISTING_EDITIONS_DIR.glob("*.json") if f.stem != "index"}


def assemble_one(draft_path, names, colophon, markets, warnings_out=None):
    draft = load_json(draft_path)
    if not isinstance(draft, dict):
        raise SystemExit(f"FATAL: {draft_path} did not parse to an object")

    date = draft.get("date") or draft_path.stem
    refs = load_refs_for_date(date)
    warnings = []

    lead = None
    if draft.get("lead"):
        lead = build_story(draft["lead"], refs, warnings)

    frontpage = [s for s in (
        build_story(x, refs, warnings) for x in draft.get("frontpage", []) or []
    ) if s]

    sections = []
    for sec in draft.get("sections", []) or []:
        slug = sec.get("slug", "")
        stories = [s for s in (
            build_story(x, refs, warnings) for x in sec.get("stories", []) or []
        ) if s]
        if not stories:
            continue
        out_sec = {
            "name": names.get(slug, slug.replace("-", " ").title()),
            "slug": slug,
            "stories": stories,
        }
        # The draft carries `also` at SECTION level (see the schema in
        # ROUTINE_PROMPT_B.md) and site/app.js renders `sec.also`. Until v6
        # this loop never copied it across, so every also-rail the editor
        # wrote was silently discarded here — 49 of 49 over the five editions
        # audited on 2026-07-29, despite the full text having been fetched for
        # each one. build_story()'s story-level `also` handling is kept for
        # older drafts that put the rail on a story instead.
        rail = build_also_rail(sec.get("also"), refs, warnings)
        if rail:
            out_sec["also"] = rail
        sections.append(out_sec)

    opportunities = [build_opp(x, refs, warnings)
                     for x in draft.get("opportunities", []) or []]

    edition = {
        "date": date,
        "edition": edition_number(date),
        "colophon": colophon,
        "lead": lead,
        "frontpage": frontpage,
        "sections": sections,
        "opportunities": opportunities,
    }
    brief = draft.get("brief")
    if isinstance(brief, list) and brief:
        brief_out = []
        for b in brief:
            bid = b.get("id") if isinstance(b, dict) else None
            bref = refs.get(bid) if bid else None
            if not bref:
                warnings.append(f"brief id {bid!r} unknown — dropped")
                continue
            brief_out.append({"line": (b.get("line") or "").strip(), "id": bid,
                               "url": bref.get("url")})
        if brief_out:
            edition["brief"] = brief_out
    if markets:
        edition["markets"] = markets   # B5, injected verbatim, optional

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{date}.json"
    out.write_text(json.dumps(edition, indent=2, ensure_ascii=False))
    n_stories = (1 if lead else 0) + len(frontpage) + sum(len(s["stories"]) for s in sections)
    print(f"  {out.relative_to(ROOT)}  edition {edition['edition']}  "
          f"{n_stories} story slots, {len(opportunities)} opps")
    if DERIVED["count"]:
        print(f"    !! {DERIVED['count']} of {n_stories} stories arrived WITHOUT "
              f"hook/points — bullets were derived from the paragraph summary.")
        print(f"    !! That means Routine B is running a STALE PROMPT. Re-paste "
              f"ROUTINE_PROMPT_B.md into the WRITE routine to get model-written "
              f"bullets and highlights instead of derived ones.")
    for w in warnings:
        print(f"    warn: {w}")
    if warnings_out is not None:
        warnings_out.extend(warnings)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", nargs="*", default=[],
                         help="Date(s) YYYY-MM-DD to rebuild even if already "
                              "published, or 'all' to rebuild every draft.")
    args = parser.parse_args()
    force_all = "all" in args.force
    force_dates = set(args.force)

    names = slug_to_name(load_json(DIGEST, default={}))
    digest = load_json(DIGEST, default={}) or {}
    colophon = digest.get("colophon") or ""
    markets = load_json(MARKETS_FILE, default=None)

    drafts = sorted(DRAFTS.glob("*.json")) if DRAFTS.exists() else []
    if not drafts:
        print("No drafts to assemble — nothing to do.")
        return

    published = existing_edition_dates()
    skipped = []
    to_run = []
    for d in drafts:
        date = d.stem
        if date in published and not force_all and date not in force_dates:
            skipped.append(date)
            continue
        to_run.append(d)

    if skipped:
        print(f"Skipping {len(skipped)} already-published edition(s) "
              f"(immutable by default — use --force <date> to rebuild): "
              f"{', '.join(skipped)}")
    if not to_run:
        print("Nothing new to assemble.")
        return

    print(f"Assembling {len(to_run)} draft(s)…")
    for d in to_run:
        assemble_one(d, names, colophon, markets)


if __name__ == "__main__":
    main()
