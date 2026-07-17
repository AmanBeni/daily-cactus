# The Daily Cactus 🌵 — operational guide (v5)

A self-updating personal morning newspaper for one reader (Aman, Jaipur). A daily
Claude Code Routine curates pre-fetched RSS news into a JSON draft; GitHub Actions
publishes it to GitHub Pages.

> Keep this file SHORT. It is auto-loaded into the routine and re-sent every turn,
> so every line here costs tokens daily. Long-form history lives in `HANDOFF.md`
> (humans only — not loaded by the routine).

## Architecture (v5 — pipeline integrity + content quality)
```
fetch.yml (GitHub Actions, ~05:00 IST, full internet)
  → scripts/fetch_feeds.py   → feeds/latest.json     (raw, ~500 stories)
  → scripts/build_digest.py  → feeds/digest.json     (LEAN: id/title/source/summary/extract?/buzz? —
                                                        no urls/images — the model's only news input)
                             → feeds/refs/YYYY-MM-DD.json  (this date's id→url/image/source snapshot)
                             → feeds/refs.json        (rolling union, back-compat; model never reads either)
                             → scripts/enrich_shortlist.py (full-text extracts, called from build_digest)
  → scripts/fetch_markets.py → feeds/markets.json     (Nifty/Sensex/USD-INR/Brent/BTC/Gold/Silver)
        │
        ▼
Claude Code Routine (~06:00 IST, subscription, sandboxed — no internet)
  reads feeds/digest.json + TASTE.md  →  writes ONE file drafts/YYYY-MM-DD.json
  (story IDs + prose: headline/summary/signal/key_stat?/editors_read?/brief/also?).
  No HTML, no web search.
        │
        ▼
publish.yml (GitHub Actions)
  scripts/assemble_edition.py: for each NEW draft only (editions are IMMUTABLE —
    a date with an existing site/editions/<date>.json on gh-pages is skipped
    unless --force <date>) resolves ids against that date's refs snapshot
    (falling back to the union of all snapshots), injects url/image/source/
    colophon/edition/markets → site/editions/YYYY-MM-DD.json. Deploys site/ →
    gh-pages, then a post-deploy job rebuilds editions/index.json on gh-pages.
        │
        ▼
GitHub Pages renderer (site/index.html + app.js + style.css, committed in repo) renders the JSON
```

**Core rules that keep cost low (do not violate):**
1. The model writes **only `drafts/<today>.json`** — story IDs + prose. Never HTML,
   never urls/images (those are injected on Actions from the refs snapshot, which
   also makes fabricated links impossible).
2. The routine reads **only `feeds/digest.json` and `TASTE.md`** (2 reads total),
   writes once, and stops. No repo listing, no extra file reads, no self-verify,
   no web search. (This is the fix for the old read-before-write retry loop that
   burned ~1.5M tokens — see `HANDOFF.md`.)
3. The renderer (`site/index.html`, `app.js`, `style.css`) is committed once and
   never regenerated.
4. **Editions are immutable once published.** `assemble_edition.py` never
   rewrites a past `site/editions/<date>.json` by default — content-hash story
   ids (not positional) plus per-date refs snapshots make this safe. This is
   the fix for the "vanishing editions" bug (see `HANDOFF.md`/`V2_PLAN.md`).
5. Keep `CLAUDE.md`, `ROUTINE_PROMPT.md`, and `TASTE.md` short **and frozen**
   between runs (changing them busts the prompt cache).

## Files
| File | Role |
|---|---|
| `ROUTINE_PROMPT.md` | The routine's prompt. Paste as-is. Outputs a draft, not HTML. |
| `TASTE.md` | Short standing preferences (≤40 lines). Routine's 2nd read. Weekly feedback fold via `taste.yml`. |
| `sources.yaml` | Feed registry (15 sections incl. weekend Longform + Remainder). Edit by hand. |
| `scripts/fetch_feeds.py` | Fetch all feeds → `feeds/latest.json` (Actions only). |
| `scripts/build_digest.py` | Dedup/rank/shortlist/enrich → digest + refs snapshot + feed_stats (Actions only). |
| `scripts/enrich_shortlist.py` | Full-text extraction for shortlisted stories (trafilatura/readability). |
| `scripts/fetch_markets.py` | Markets snapshot → `feeds/markets.json` (Actions only). |
| `scripts/assemble_edition.py` | Draft + refs snapshot → full edition JSON, immutable-by-default (Actions only). |
| `scripts/recover_editions.py` | One-time: restores gutted past editions from gh-pages git history. |
| `scripts/fold_taste.py` | Weekly heuristic fold of 👍/👎 issues into `TASTE.md` (no model calls). |
| `scripts/audit_feeds.py` | Monthly per-feed hit-rate report from `feeds/feed_stats.jsonl`. |
| `feeds/digest.json` | Model-facing lean candidates. Regenerated each fetch. |
| `feeds/refs/YYYY-MM-DD.json` | That date's id→url/image lookup (kept ~30 days). Model never reads it. |
| `drafts/YYYY-MM-DD.json` | The routine's daily output (IDs + prose). |
| `site/editions/YYYY-MM-DD.json` | Assembled edition the renderer reads. Immutable once published. |
| `site/editions/index.json` | Date manifest (rebuilt by a post-deploy job in `publish.yml`, on gh-pages). |
| `site/{index.html,app.js,style.css}` | The JS renderer. MUST stay committed; routine never touches it. |
| `.github/workflows/{fetch,publish,taste,audit}.yml` | The pipeline (a gh-pages-triggered manifest workflow can't run, so the manifest rebuild is folded into publish.yml). |

## Editorial intent (full version in ROUTINE_PROMPT.md)
Signal over noise; numbers-first summaries; "why it matters" > "what happened";
India lens; no hype; honest about thin days (render fewer, never pad, never
web-search to fill, never a past-dated event, never a repeat of the last 7 days).
