# The Daily Cactus 🌵 — operational guide (v4)

A self-updating personal morning newspaper for one reader (Aman, Jaipur). A daily
Claude Code Routine curates pre-fetched RSS news into a JSON draft; GitHub Actions
publishes it to GitHub Pages.

> Keep this file SHORT. It is auto-loaded into the routine and re-sent every turn,
> so every line here costs tokens daily. Long-form history lives in `HANDOFF.md`
> (humans only — not loaded by the routine).

## Architecture (v4 — token-lean)
```
fetch.yml (GitHub Actions, ~05:00 IST, full internet)
  → scripts/fetch_feeds.py   → feeds/latest.json   (raw, ~280 stories)
  → scripts/build_digest.py  → feeds/digest.json   (LEAN: id/title/source/summary, no urls/images — the model's only input)
                             → feeds/refs.json      (id → url/image/source; model never reads this)
        │
        ▼
Claude Code Routine (~06:00 IST, subscription, sandboxed — no internet)
  reads feeds/digest.json  →  writes ONE file drafts/YYYY-MM-DD.json
  (story IDs + prose only: headline/summary/takeaway/why). No HTML, no web search.
        │
        ▼
publish.yml (GitHub Actions)
  scripts/assemble_edition.py  drafts/*.json + feeds/refs.json → site/editions/YYYY-MM-DD.json
    (injects url/image/source/colophon/edition), deploys site/ → gh-pages, then a
    post-deploy job rebuilds editions/index.json on gh-pages (manifest)
        │
        ▼
GitHub Pages renderer (site/index.html + app.js + style.css, committed in repo) renders the JSON
```

**Core rules that keep cost low (do not violate):**
1. The model writes **only `drafts/<today>.json`** — story IDs + prose. Never HTML,
   never urls/images (those are injected on Actions from `refs.json`, which also
   makes fabricated links impossible).
2. The routine reads **only `feeds/digest.json`**, writes once, and stops. No
   repo listing, no extra file reads, no self-verify, no web search. (This is the
   fix for the old read-before-write retry loop that burned ~1.5M tokens — see
   `HANDOFF.md`.)
3. The renderer (`site/index.html`, `app.js`, `style.css`) is committed once and
   never regenerated.
4. Keep `CLAUDE.md` and `ROUTINE_PROMPT.md` short **and frozen** between runs
   (changing them busts the prompt cache).

## Files
| File | Role |
|---|---|
| `ROUTINE_PROMPT.md` | The routine's prompt. Paste as-is. Outputs a draft, not HTML. |
| `sources.yaml` | Feed registry (12 sections). Read by the fetcher. Edit by hand. |
| `scripts/fetch_feeds.py` | Fetch all feeds → `feeds/latest.json` (Actions only). |
| `scripts/build_digest.py` | Lean digest + refs from latest.json (Actions only). |
| `scripts/assemble_edition.py` | Draft + refs → full edition JSON (Actions only). |
| `feeds/digest.json` | Model-facing lean candidates. Regenerated each fetch. |
| `feeds/refs.json` | id→url/image lookup for assembly. Model never reads it. |
| `drafts/YYYY-MM-DD.json` | The routine's daily output (IDs + prose). |
| `site/editions/YYYY-MM-DD.json` | Assembled edition the renderer reads. |
| `site/editions/index.json` | Date manifest (rebuilt by a post-deploy job in `publish.yml`, on gh-pages). |
| `site/{index.html,app.js,style.css}` | The JS renderer. MUST stay committed; routine never touches it. |
| `.github/workflows/{fetch,publish}.yml` | The pipeline (a gh-pages-triggered manifest workflow can't run, so it's folded into publish.yml). |

## Editorial intent (full version in ROUTINE_PROMPT.md)
Signal over noise; "why it matters" > "what happened"; India lens; no hype;
honest about thin days (render fewer, never pad, never web-search to fill).
