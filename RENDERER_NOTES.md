# Renderer Notes — Phase 3 (Cactus Craft v2)

> The Phase 3 agent rewrote site/{index.html,app.js,style.css} to the locked
> Cactus Craft design, then was interrupted before writing the test fixture +
> these notes. The supervising agent built site/dev-fixture.json and completed
> validation (below). Code was verified complete, valid, and correct.

## Verified against the real pipeline
- `assemble_edition.py` emits brief items as `{line, id, url}` (id→url resolved
  from refs, line 253) and story objects carry `url` but NO id. The renderer
  therefore anchors brief "↓ jump" links by URL-match (story url == brief url),
  which is correct for real editions. Confirmed live: both anchored brief items
  resolved to their story cards.
- `also` rail items are emitted as `{line, source, url}` — rendered as a compact
  list after a section's cards. Verified.
- `markets` injected verbatim as `{quotes:[{label,value,change_pct}], fetched_at}`
  — renders as the stamp-face stat bar, ink values, colored ▲/▼ only. 7/7 shown.
- `key_stat` → stat chip; `editors_read` → single red-tinted block (lead + any
  frontpage story that has it). Both verified.
- Legacy `takeaway`/`why` (old editions, no `signal`) → restyled fallback block.
  Verified against the real site/editions/2026-06-18.json.

## Test evidence (browser pane)
- Fixture (all new fields) at ?fixture=1: no console errors; masthead (Option B
  serif + red swash + pot-cactus), markets bar, 2-min brief w/ working jump
  links, lead w/ key_stat + editors_read, frontpage 2-col, AI section + also
  rail, climate legacy-fallback, opportunities — all render.
- Back-compat: real 2026-06-18 edition renders in the new style, date picker
  works, no errors.
- Mobile 375px: no horizontal scroll (docW==winW==375), single column, markets
  bar wraps.
- Feedback thumbs generate correct prefilled GitHub issue URLs
  (labels=feedback, title "👍 <derived-id>", body headline+date), open in new
  tab, mark "sent" once.
- Image policy: lead with no image → drawn-cactus "no photo" placeholder;
  non-lead with no image → figure hidden. (External image URLs hang in the test
  sandbox — they load or fall back correctly against a real network.)

## One real follow-up (interface gap, non-blocking)
The thumb issue-title id is derived as `<date>/<scope>/<idx>` (story objects
carry no stable id to reuse). `scripts/fold_taste.py` (Phase 2) tallies votes by
**section slug prefix** of the id. For section-story votes the scope IS the slug
(e.g. `2026-07-14/ai/0`), so those fold correctly; for lead/frontpage the scope
is `front`, which fold_taste can't map to a topic. Feedback is still fully
captured as issues either way — only the automatic per-section tallying misses
front-page votes. Fix later by teaching fold_taste to read `<scope>` as the
section (a small Phase-2 script tweak), or have the editor keep front-page
stories attributed to their home section. Flagged, not fixed here.

## Notes
- No dark mode by design — the paper world is deliberately light (commented in
  style.css).
- site/dev-fixture.json ships to the live site but is never linked (only reached
  via ?fixture=1); harmless. Delete before deploy if you prefer a clean site/.
- Textures are small base64 PNG tiles; pencil SVG filters only on tiny one-off
  elements (never page-wide — that hangs the renderer).
