# The Daily Cactus 🌵 — Personal Morning Newsletter via Claude Code Routines

A self-updating, personally-curated daily newspaper. A Claude Code Routine runs every
morning on Anthropic's cloud, reads your curated RSS sources, edits them into a
multi-page HTML newspaper, and publishes it to GitHub Pages. You open one URL with
your morning chai. No laptop required.

---

## Repo contents

| File | What it is |
|---|---|
| `ROUTINE_PROMPT.md` | The editorial instruction manual. Paste this as the routine's prompt. |
| `sources.yaml` | Your source registry. Edit freely — both the fetcher and the routine read it. |
| `scripts/fetch_feeds.py` | Fetches all RSS feeds on GitHub's runners and writes `feeds/latest.json`. |
| `feeds/latest.json` | The morning's pre-fetched news. Produced by the fetch workflow, read by the routine. |
| `scripts/build_digest.py` | (v4) Turns the raw fetch into a lean `feeds/digest.json` + `feeds/refs.json`. Runs on Actions. |
| `scripts/assemble_edition.py` | (v4) Expands the routine's draft into the full edition JSON. Runs on Actions. |
| `feeds/digest.json` | (v4) The lean, model-facing candidate list (no urls/images). |
| `feeds/refs.json` | (v4) id → url/image/source lookup, used only at publish time. |
| `drafts/YYYY-MM-DD.json` | (v4) The routine's daily output: story IDs + prose. |
| `site/` | Renderer (`index.html` + `app.js` + `style.css`) + `editions/*.json` (data). |
| `.github/workflows/fetch.yml` | Cron job that fetches feeds + builds the digest ~1h before the routine. |
| `.github/workflows/publish.yml` | Assembles the draft and publishes to GitHub Pages. |
| `.github/workflows/manifest.yml` | Rebuilds the date-picker manifest on gh-pages. |

> Removed in v3/v4: `template.html`, `seen.json` (no longer used).

---

## One-time setup (~15 minutes)

### Step 1 — Create the repo
1. Create a new GitHub repo (private is fine), e.g. `daily-cactus`.
2. Push this entire starter kit to the `main` branch.

### Step 2 — Enable GitHub Pages
1. Repo → Settings → Pages.
2. Source: **Deploy from a branch** → branch `gh-pages` → folder `/ (root)`.
   (The `gh-pages` branch will appear automatically after the first routine run,
   created by the publish workflow.)
3. Note your URL: `https://<your-username>.github.io/daily-cactus/`
   — bookmark it on your phone. That's your newspaper.

### Step 3 — Create the Routine
1. Go to **claude.ai/code** → Routines (or type `/schedule` in the Claude Code CLI).
2. New routine:
   - **Prompt:** paste the full contents of `ROUTINE_PROMPT.md`.
   - **Repository:** connect `daily-cactus`.
   - **Trigger:** Scheduled → Daily → pick your time (e.g. 6:00 AM IST so it's
     ready by 6:30–7:00).
   - **Connectors:** remove any you don't need (Slack, Drive, etc.) — this routine
     only needs the repo + web fetch. Smaller access footprint = safer.
3. Save. Optionally hit "Run now" to test immediately instead of waiting for morning.

### Step 4 — Calibrate (first week)
Read the first 2–3 editions critically. When something's off, fix it at the source:
- Bad/boring stories from an outlet → edit `sources.yaml` (remove or swap the feed).
- Wrong ranking/tone/length → edit the routine's prompt (the editorial charter section).
- Section too thin/fat → adjust `max_stories` in `sources.yaml`.

This is the fun part: you are now the publisher, Claude is your editor-in-chief,
and the prompt is your standing editorial memo.

---

## How the news actually gets in (important)
Claude Code routines run in a sandboxed cloud VM whose outbound network is locked
to a small allowlist. Fetching news feeds **from inside the routine returns 403
for every publisher** — so the routine can't fetch its own news. (If your early
editions said "all feeds failed, gathered via web search," this is exactly why.)

The fix: **GitHub Actions fetches the feeds, not the routine.**
1. `fetch.yml` runs on a daily cron (~05:00 IST), on GitHub's runners which have
   full internet. `scripts/fetch_feeds.py` reads `sources.yaml`, fetches every
   feed, extracts headline + summary + link + a thumbnail image, and commits
   `feeds/latest.json`.
2. Your routine (~06:00 IST) clones the repo — `feeds/latest.json` is already
   sitting there — and just **reads** it. No network needed inside the sandbox.
3. The routine edits, summarizes, lays out the paper (now with side photos), and
   commits `site/`. `publish.yml` deploys it to Pages.

GitHub does the dumb reliable plumbing; Claude does only the editing. Web search
stays on as a *backfill* for any section that comes up thin — the exception, not
the rule.

### Setup additions for the feeds pipeline
1. Add three things to your repo (web UI is fine): `scripts/fetch_feeds.py`,
   `.github/workflows/fetch.yml`, and the placeholder `feeds/latest.json`.
2. Make sure the fetch cron runs **before** your routine. Default is 05:00 IST
   (`30 23 * * *` UTC). If your routine isn't ~06:00 IST, adjust the cron so
   there's a comfortable 30–60 min gap (GitHub cron can lag a few minutes).
3. Test it now without waiting for the cron: Actions tab → **Fetch RSS Feeds** →
   **Run workflow**. When it's green, open `feeds/latest.json` in the repo and
   eyeball it — you'll see which feeds succeeded and which 403'd at the publisher
   level. Swap any persistently-dead feeds in `sources.yaml`.

### About the photos
Thumbnails are hotlinked straight from each publisher's CDN (pulled from the
feed's `media:thumbnail` / `media:content` / `enclosure` / inline `<img>`). They
load in your browser when you read the paper. If a story has no image, it renders
text-only; if a publisher blocks hotlinking, that one image quietly hides itself.
No images are downloaded or stored in the repo.

---

## How memory works
- `seen.json` stores every URL covered in the last 7 days → no repeats.
- It also stores short "developing story" notes → the paper can say
  *"Update on Tuesday's story: …"* like a real editor with object permanence.
- It's committed back to the repo every run, so memory survives between sessions
  for free.

## Costs & limits (as of June 2026 — research preview, may change)
- Routines consume your Claude subscription usage like a normal session.
- Pro plan: up to 5 routine runs/day. One newsletter run/day fits easily.
- One run of this routine ≈ one moderately long Claude Code session.

## Troubleshooting
- **No new edition this morning?** Check the routine's run history at claude.ai/code
  → Routines. Most common cause: a feed timing out — the prompt tells Claude to
  skip dead feeds, not crash, but check the run log.
- **Pages not updating?** Check the Actions tab — the publish workflow must be green.
- **Want to change schedule/frequency?** Edit the trigger in the routine settings;
  for custom cron expressions use `/schedule update` in the CLI.

---

## v2 update — what changed

**Sources (diversity fix).** Rebuilt `sources.yaml`: repaired/replaced the dead
feeds, added The Guardian, SCMP, New Scientist, HBR, Analytics India, Pitchfork,
Mongabay (nature), and a **Google News diversity backstop per section** so no
section is ever stuck on a single outlet (Reuters/AP killed their public RSS —
Google News replaces them). Dropped the noisy Hacker News feed that was polluting
the AI section. Added an **Opportunities (beta)** section and nature coverage in
Other Interests.

**Editorial.** "Why it matters" is now **Key Takeaway + Why It Matters** — a sharp
one-line takeaway plus 2–3 lines of real second-order thinking, with a framework in
the prompt so it stops being mush.

**Layout.** Front page is now a **lead story + two-column grid** (desktop) that
collapses to a single column on phones — kills the dead space. Nav has visible `·`
separators and an **Archive** link.

**Date navigation.** Each edition is snapshotted to `archive/YYYY-MM-DD/` (written
once, kept forever) and listed on a new `archive/index.html` — your date-toggle.

## Token usage — read before optimizing
Don't optimize blind. First see the real per-run cost: open the routine in
**claude.ai/code → Routines → run history** (and the usage indicator). Decide based
on that number, not a guess.

What this update already did, safely: trimmed each candidate story's summary in
`feeds/latest.json` (lighter input) **without** dropping any candidates — the feed
still carries up to 8 stories each, so no good story is filtered out before the
editor sees it. The dated archive snapshots are kept deliberately: they're what make
date-browsing work, so they are NOT a place to cut. If a real cost problem shows up
later, the next lever is making the homepage a redirect to the latest dated edition
(removes one full-page write per run) — but only if the numbers justify it.

---

## v3 update — JSON architecture (token fix + working dates)

**What changed and why.** Previously the routine hand-wrote ~25 HTML pages every
run (front page + 12 sections + a full dated archive copy). That markup repetition
was burning tokens. Now the routine writes **one small JSON file per day**
(`site/editions/YYYY-MM-DD.json`) — pure editorial content, no markup. A fixed
renderer (`site/index.html` + `site/app.js` + `site/style.css`, committed once,
never regenerated) turns that JSON into the paper in the browser. Expect a large
drop in per-run tokens.

**How dates work now.** Each day is its own JSON file. Past editions accumulate on
the published site automatically (`keep_files: true` in publish.yml). A tiny
`manifest.yml` workflow rebuilds `editions/index.json` (the date-picker list) on
GitHub's runners — zero model tokens. The date picker in the masthead loads any
past edition.

**Cross-day memory: removed, on purpose.** Making "no repeats" persist reliably
needs editions to accumulate on `main` (an auto-merge workflow — another fragile
moving part). For a light personal paper that wasn't worth it, so each edition is
now independent. Dedup happens within a day only.

### Files in the new model
- `site/index.html`, `site/app.js`, `site/style.css` — the renderer. Commit once.
- `site/editions/YYYY-MM-DD.json` — one per day, written by the routine.
- `site/editions/index.json` — date manifest, maintained by `manifest.yml`.
- `.github/workflows/manifest.yml` — rebuilds the manifest on gh-pages (free).
- `scripts/fetch_feeds.py`, `.github/workflows/fetch.yml` — unchanged (RSS fetch).
- `sources.yaml` — unchanged (feed registry).
- Removed: `template.html`, `seen.json` (no longer used).

### One-time setup for v3
1. Add the three renderer files: `site/index.html`, `site/app.js`, `site/style.css`.
2. Add `site/editions/2026-06-18.json` (seed) and `site/editions/index.json` (seed).
3. Add `.github/workflows/manifest.yml`.
4. Replace `ROUTINE_PROMPT.md` (now outputs JSON, not HTML) in the routine's prompt.
5. Delete the obsolete `template.html` from the repo (optional but tidy).
6. Pages already serves `gh-pages` root — no change. `keep_files` already set.
7. Run the routine once to produce the first real edition.

---

## v4 update — drastic token cut (the 1.5M-token fix)

**The problem.** A v3 routine run on 21 Jun 2026 burned **~1.5 million tokens**.
The output JSON was tiny; the cost was the *agent tax* — in an agentic routine the
entire context (the big `feeds/latest.json`, the system prompt, tool defs, the
~10KB `CLAUDE.md`) is re-sent as input on **every turn**, and a read-before-write
retry loop spun that for dozens of turns, with web-search backfill piling on.

**The v4 fix — push everything cheap to GitHub Actions, shrink what the model
touches, and make the run un-loopable.** What changed:

1. **Server-side digest.** A new `scripts/build_digest.py` (in `fetch.yml`) does
   all dedup/ranking/trimming on free runners and emits a lean `feeds/digest.json`
   — `id`/`title`/`source`/`summary` only, **no urls or images** (the longest
   fields). That's the model's *only* news input. A parallel `feeds/refs.json`
   keeps the urls/images for later.
2. **The model writes a tiny draft.** It reads one file, writes
   `drafts/YYYY-MM-DD.json` (story **IDs + the prose it wrote**), and stops. No
   urls, no images, no HTML, no web search, no repo exploring.
3. **Server-side assembly.** `scripts/assemble_edition.py` (in `publish.yml`)
   expands the draft into the full `site/editions/YYYY-MM-DD.json`, injecting
   url/image/source/colophon/edition deterministically. **Because the model never
   writes a URL, it can't fabricate one** — the old "never invent a link" rule is
   now structural, not a hope.
4. **Loop-proof prompt.** Date-based output filename never pre-exists (kills the
   read-before-write loop); one read → one write → stop.
5. **Slim + frozen prompts.** `CLAUDE.md` is now a short operational guide (the
   long saga moved to `HANDOFF.md`); `ROUTINE_PROMPT.md` is tightened. Both ride
   every turn, so keeping them small and unchanged (prompt-cache friendly) matters.
6. **Web-search backfill removed.** Thin days render thin — on-charter, and it
   kills a turn-multiplier.

Net: the model's per-run footprint drops from ~1.5M to an estimated low-tens-of-
thousands of tokens. The renderer and `sources.yaml` are unchanged.

### One-time setup for v4
1. Add `scripts/build_digest.py` and `scripts/assemble_edition.py`.
2. Replace `.github/workflows/fetch.yml` and `publish.yml` (digest + assemble steps).
3. Add `drafts/` (with `.gitkeep`) and seed `feeds/digest.json` + `feeds/refs.json`.
4. Replace `ROUTINE_PROMPT.md` in the routine with the new (draft-output) version.
5. Replace `CLAUDE.md`; add `HANDOFF.md`.
6. Confirm exactly **one** routine exists and it uses the new prompt; then run
   `fetch.yml` manually, run the routine once, and open the site.
