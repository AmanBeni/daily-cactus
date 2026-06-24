# The Daily Cactus 🌵 — Full Handoff & History

> The long-form story of this project: why it's built the way it is, what was
> tried, and what broke. `CLAUDE.md` holds the short operational version that the
> routine loads each run — keep THIS file out of the routine's context (it's
> reference for humans / dev sessions, not the daily run).

---

## Mission
A self-updating personal morning newspaper: a scheduled Claude Code **Routine**
curates RSS news into a multi-section paper published to GitHub Pages, read by the
owner (Aman "Cactus", Jaipur, India) with morning chai.

## The token problem that drove v4 (READ THIS)
A routine run on **21 Jun 2026 consumed ~1.5 MILLION tokens** — economically
absurd for a personal paper. The output (a ~5KB JSON) was never the cost. The
cost was the **agent tax**: in an agentic routine the ENTIRE context — the big
`feeds/latest.json` (~283 stories, with long url/image fields), the Claude Code
system prompt, tool defs, and a ~10KB `CLAUDE.md` — is re-sent as INPUT tokens on
EVERY turn. A "read-before-write" retry loop spun this for dozens of turns, and
web-search backfill dumped large results into context. Large per-turn context ×
many turns = quadratic blow-up.

**v4 is the fix.** See `CLAUDE.md` for the resulting architecture. The design
review (with a critic agent, "Agent Zero") concluded:
- The loop fix is ~80% of the saving; everything else is refinement.
- Slim + freeze `CLAUDE.md`/`ROUTINE_PROMPT.md` (they ride every turn).
- Kill web-search backfill (turn-multiplier + context-bomb).
- Move all dedup/ranking/trimming to GitHub Actions (free compute).
- Have the model emit only **story IDs + prose**; reassemble the full edition
  JSON on Actions, injecting url/image/source verbatim — this both cuts output
  tokens AND makes fabricated URLs structurally impossible.
- Stripping url/image from the model-facing digest means we can send a generous
  candidate buffer for a tiny token cost (resolves the "fewer candidates vs
  editorial quality" tension).
- Rejected: tiered output (dropping "why it matters" from section stories) — it
  trades the reader's #1 stated value for ~2% of the bill.

## History / past runs (the saga)
- **v1:** routine generated HTML pages directly. Discovered all RSS feeds 403'd
  inside the sandbox; the paper was secretly running on web-search fallback only.
- GitHub setup pain: App write-permission, `gh-pages` branch creation, a
  misplaced `.github/workflows` path, Pages pointing at the wrong branch. Resolved.
- **v2 (feeds fix):** moved fetching to GitHub Actions (`fetch.yml` +
  `fetch_feeds.py`) → `feeds/latest.json`. Last good fetch: **44/48 feeds ok, 283
  stories**. Failures: Analytics India, Entrackr, Import AI (bot-block/HTML not
  XML), HBR (transient SSL) — all covered via Google News backstop.
- **v2 editorial:** added Key Takeaway + Why It Matters, lead+grid layout, nav
  separators, Opportunities (beta), source diversity.
- **Layout fix:** widened 1040px → 2200px auto-fit grid.
- **v3:** re-architected to JSON-data + JS renderer (model writes one JSON, not
  HTML). Correct in spirit but still paid the agent tax → the 1.5M-token loop.
- **v4 (current):** server-side digest + ID-based draft + server-side reassembly.
  See `CLAUDE.md`.

## Why each older decision stands
- **Fetch on GitHub Actions, not in the routine:** the sandbox 403s on publisher
  domains. Non-negotiable.
- **`keep_files: true` in publish.yml:** otherwise each deploy wipes past
  `editions/*.json` off gh-pages.
- **manifest.yml:** the date picker needs a list of editions; building it on
  runners costs zero model tokens.
- **Google News RSS feeds in `sources.yaml`:** Reuters/AP killed public RSS;
  Google News search feeds are a per-section diversity backstop (real publisher in
  a `<source>` tag, parsed out by the fetcher).
- **Cross-day memory (`seen.json`) removed on purpose:** reliable "no repeats"
  needs editions to accumulate on `main` (a fragile auto-merge). Not worth it for
  a light personal paper. Each edition is independent; dedupe within a day only.

## Owner preferences
Direct, no sugarcoating; honest "this is a 30% fit" over flattery. Business-trained
generalist pivoting to AI-generalist / founder's-office roles — "why it matters"
should connect to that when genuinely relevant, never forced.

## Debug protocol (owner's standing rule)
Web-search before trusting memory about any external service's behavior.

## Gotchas
- GitHub cron is best-effort and can lag a few minutes; keep fetch ~1h before the
  routine.
- `manifest.yml` is loop-guarded (`!editions/index.json`).
- v4 styling changes appear on refresh without a routine run (CSS is live in
  `style.css`, loaded by the browser).
- Owner is on a MacBook Air M4 (16GB) + external monitor; test layout at both widths.
