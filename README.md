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
| `sources.yaml` | Your source registry. Edit freely — the routine reads it every run. |
| `template.html` | The fixed look & feel of the paper. Routine copies its styling. |
| `seen.json` | Cross-day memory: URLs already covered + developing-story notes. |
| `site/` | Generated output. `index.html` = front page, `sections/` = section pages, `archive/` = past editions. |
| `.github/workflows/publish.yml` | Auto-publishes the routine's commits (on `claude/*` branches) to GitHub Pages. |

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
