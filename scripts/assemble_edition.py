#!/usr/bin/env python3
"""Expand the routine's lean DRAFT into the full edition JSON the renderer reads.

WHY THIS EXISTS
---------------
The routine writes the smallest thing it possibly can: a draft of story IDs +
the prose it wrote (headline/summary/takeaway/why). It writes NO urls, NO image
links, NO source strings, NO colophon, NO edition number. This:
  * minimises the model's OUTPUT tokens, and
  * makes fabricated urls/images structurally impossible — the model never emits
    one; we inject them here, verbatim, from feeds/refs.json (built on GitHub
    Actions during the fetch).

This script runs at PUBLISH time (GitHub Actions, free compute). For every
drafts/<date>.json it produces site/editions/<date>.json in exactly the shape
site/app.js already expects, then the deploy step ships site/ to gh-pages.

Idempotent: re-running rebuilds every edition from its draft. If a draft is
malformed we FAIL LOUDLY (non-zero exit) so the deploy step does not ship a
broken paper. If the model references an unknown id, that single story is
dropped with a warning rather than crashing the whole edition.
"""
import json
import sys
import datetime
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DRAFTS = ROOT / "drafts"
REFS_FILE = ROOT / "feeds" / "refs.json"
LATEST = ROOT / "feeds" / "latest.json"
DIGEST = ROOT / "feeds" / "digest.json"
OUT_DIR = ROOT / "site" / "editions"

# Edition numbering is deterministic — no stored counter to drift or corrupt.
# Seed: 2026-06-16 == edition 1 (so 2026-06-18 == edition 3, matching history).
EPOCH = datetime.date(2026, 6, 16)


def load_json(path, default=None):
    try:
        return json.loads(path.read_text())
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


def build_story(item, refs, warnings):
    """Merge model prose with the verbatim url/image/source from refs[id]."""
    sid = item.get("id")
    ref = refs.get(sid)
    if ref is None:
        warnings.append(f"unknown story id {sid!r} — dropped")
        return None
    return {
        "headline": item.get("headline", ref.get("title", "")),
        "summary": item.get("summary", ""),
        "takeaway": item.get("takeaway", ""),
        "why": item.get("why", ""),
        "source": ref.get("source", ""),
        "url": ref.get("url"),
        "image": ref.get("image"),
        "developing": bool(item.get("developing", False)),
    }


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


def assemble_one(draft_path, refs, names, colophon):
    draft = load_json(draft_path)
    if not isinstance(draft, dict):
        raise SystemExit(f"FATAL: {draft_path} did not parse to an object")

    date = draft.get("date") or draft_path.stem
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
        sections.append({
            "name": names.get(slug, slug.replace("-", " ").title()),
            "slug": slug,
            "stories": stories,
        })

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

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{date}.json"
    out.write_text(json.dumps(edition, indent=2, ensure_ascii=False))
    n_stories = (1 if lead else 0) + len(frontpage) + sum(len(s["stories"]) for s in sections)
    print(f"  {out.relative_to(ROOT)}  edition {edition['edition']}  "
          f"{n_stories} story slots, {len(opportunities)} opps")
    for w in warnings:
        print(f"    warn: {w}")
    return out


def main():
    refs = load_json(REFS_FILE, default={}) or {}
    names = slug_to_name(load_json(DIGEST, default={}))
    digest = load_json(DIGEST, default={}) or {}
    colophon = digest.get("colophon") or ""

    drafts = sorted(DRAFTS.glob("*.json")) if DRAFTS.exists() else []
    if not drafts:
        print("No drafts to assemble — nothing to do.")
        return

    print(f"Assembling {len(drafts)} draft(s)…")
    for d in drafts:
        assemble_one(d, refs, names, colophon)


if __name__ == "__main__":
    main()
