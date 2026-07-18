#!/usr/bin/env python3
"""P7 — real event/opportunity sources -> feeds/opportunities.json.

WHY THIS EXISTS
---------------
The Opportunities & Events section used to be fed entirely by Google News
queries. Verified live (2026-07-18): those queries return only RETROSPECTIVE
coverage ("... Summit concludes ...") and exam-prep recaps — zero forward-
dated items with a registration link, because news feeds structurally can't
supply upcoming events. Three consecutive editions published zero
opportunities as a result (see ISSUES_BACKLOG.md P7).

This script queries four REAL event/opportunity sources instead and writes
feeds/opportunities.json in the same candidate shape build_digest.py already
understands (title/link/source/published/summary/image_url), PLUS structured
`event_date`/`deadline` ISO fields so build_digest.py can hard-drop anything
already expired on a REAL date rather than a title-regex guess:

  1. Unstop  (primary) — JSON API, no key. India's dominant opportunity board.
  2. 10times.com — HTML scrape of two category pages (city pages are
     Cloudflare-403'd — do not use those).
  3. Lu.ma — the __NEXT_DATA__ JSON embedded in each city's discover page.
  4. Devpost — JSON API, requires a desktop Chrome UA or it 403s.

Runs on GitHub Actions (.github/workflows/fetch.yml), before build_digest.py.

ALL FOUR ARE UNDOCUMENTED / REVERSE-ENGINEERED ENDPOINTS EXCEPT DEVPOST'S
PUBLIC API — they WILL break eventually. Every source fetch is wrapped so one
source's failure can never affect another's, or crash the pipeline; per-source
counts are always printed so breakage is visible immediately instead of
silently going to zero (exactly how the all-Google-News version's zero-
opportunity days went unnoticed for 3 runs).
"""
import datetime
import html as htmllib
import json
import pathlib
import re
import ssl
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "feeds" / "opportunities.json"

TIMEOUT = 15
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = None


def _get(url, headers=None, timeout=TIMEOUT):
    """Never raises: returns the decoded response body, or None on any error."""
    h = {"User-Agent": BROWSER_UA, "Accept": "*/*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def _get_json(url, headers=None, timeout=TIMEOUT):
    body = _get(url, headers=headers, timeout=timeout)
    return json.loads(body) if body else None


def _iso(dt_str):
    """Best-effort coercion of a source's date string to a bare ISO date
    (YYYY-MM-DD). Returns None rather than raising on anything unparseable."""
    if not dt_str:
        return None
    s = str(dt_str).strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return None
    try:
        datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    return m.group(0)


# ---------------------------------------------------------------------------
# 1. Unstop
# ---------------------------------------------------------------------------
UNSTOP_TYPES = ("hackathons", "competitions")
UNSTOP_SEARCH_TERMS = ("AI", "deep tech", "drone", "quantum", "climate", "startup")

# Quality filter (backlog: "require a meaningful prize, a credible organizer,
# or a domain-matching title") — Unstop's own corpus skews heavily toward
# college quiz/contest noise, so this is a real gate, not a formality.
_NOISE_TITLE_TERMS = ("quiz", "trivia", "general knowledge", "rangoli",
                      "poster making", "essay writing", "treasure hunt",
                      "meme making", "reel making", "photography contest")
_CREDIBLE_ORG_TERMS = ("iit", "iim", "nit ", "bits ", "government", "ministry",
                       "aicte", "isro", "drdo", "startup india", "nasscom",
                       "google", "microsoft", "amazon", "meta", "nvidia",
                       "ieee", "unesco", "world bank", "niti aayog")
_DOMAIN_TITLE_TERMS = ("ai", "artificial intelligence", "machine learning",
                       "deep tech", "deeptech", "drone", "quantum", "climate",
                       "startup", "genai", "gen ai", "agentic", "robotics",
                       "space tech", "semiconductor")


# P11 (2026-07-19 review): the first cut of this filter kept 74% of Unstop and
# the section filled with school/campus contests — "U-19 AI Olympics", "AI
# Hackathon For Schools", "Newgen x AI Club IITM", "Freshers Party Planning
# Challenge". Cause: a bare `domain_match` (title contains "ai") was enough to
# pass on its own, and virtually every one of these has "AI" in the title.
# The reader is a professional pivoting to founder's-office / AI-generalist
# roles — student competitions are noise for him. Two changes: a HARD reject
# for campus/student framing, and domain-match alone no longer passes.
_STUDENT_NOISE_TERMS = (
    "school", "freshers", "fresher", "u-19", "u19", "u-16", "u16",
    "class 9", "class 10", "class 11", "class 12", "11th", "12th",
    "intra-college", "inter-college", "intra college", "inter college",
    "college club", "student chapter", "campus ambassador", "olympiad",
    "cultural fest", "college fest", "annual fest",
    # student bodies that run campus events under a professional-sounding name
    "ai club", "coding club", "tech club", "robotics club", "e-cell",
    "entrepreneurship cell", "student council",
)
MIN_MEANINGFUL_PRIZE = 25_000      # INR — below this it's a campus giveaway

# P11: 10times' India pages carry a long tail of near-identical "International
# Conference on <two buzzwords>" listings — the WASET-style academic mill
# circuit (three landed in the 2026-07-18 digest at once). They are not events
# this reader would ever attend. The genuinely useful 10times items are named
# industry events (DataHack Summit, Automation & Robotics Expo, BFSI Innovation
# Summit), which this pattern leaves untouched.
_CONFERENCE_MILL_RE = re.compile(
    r"^\s*(international|world|global)\s+(conference|congress|symposium)\s+on\b", re.I)


def _is_conference_mill(title: str) -> bool:
    return bool(_CONFERENCE_MILL_RE.match(title or ""))


def _unstop_quality_ok(title, prizes, organisation):
    tl = (title or "").lower()
    org = organisation or {}
    org_name = (org.get("name") or "").lower()
    blob = f"{tl} {org_name}"
    if any(t in tl for t in _NOISE_TITLE_TERMS):
        return False
    if any(t in blob for t in _STUDENT_NOISE_TERMS):
        return False                                   # hard reject, no appeal
    best_prize = max((p.get("cash") or 0)
                     for p in (prizes or []) if isinstance(p, dict)) if prizes else 0
    meaningful_prize = best_prize >= MIN_MEANINGFUL_PRIZE
    credible_org = any(t in org_name for t in _CREDIBLE_ORG_TERMS)
    domain_match = any(t in tl for t in _DOMAIN_TITLE_TERMS)
    # domain_match is a BONUS, never a pass on its own: it must be backed by
    # real money or a credible (non-campus) organiser.
    return meaningful_prize or credible_org or (domain_match and best_prize > 0)


def fetch_unstop():
    items, seen_ids = [], set()
    fetched = kept = 0
    for opp_type in UNSTOP_TYPES:
        for term in UNSTOP_SEARCH_TERMS:
            url = ("https://unstop.com/api/public/opportunity/search-result"
                   f"?opportunity={opp_type}&page=1&per_page=30"
                   f"&searchTerm={urllib.parse.quote(term)}")
            try:
                data = _get_json(url)
            except Exception as ex:                        # noqa: BLE001
                print(f"fetch_opportunities: unstop [{opp_type}/{term}] failed: {ex!r}")
                continue
            rows = ((data or {}).get("data") or {}).get("data") or []
            fetched += len(rows)
            for it in rows:
                oid = it.get("id")
                if oid is None or oid in seen_ids:
                    continue
                title = (it.get("title") or "").strip()
                if not title:
                    continue
                if not _unstop_quality_ok(title, it.get("prizes"), it.get("organisation")):
                    continue
                seo_url = it.get("seo_url") or (
                    f"https://unstop.com/{it['public_url']}" if it.get("public_url") else None)
                if not seo_url:
                    continue
                regn = it.get("regnRequirements") or {}
                deadline = _iso(regn.get("end_regn_dt"))
                festival = it.get("festival") or {}
                event_date = _iso(festival.get("start_date")) if isinstance(festival, dict) else None
                org_name = (it.get("organisation") or {}).get("name", "")
                when_bits = []
                if event_date:
                    when_bits.append(f"runs {event_date}")
                if deadline:
                    when_bits.append(f"register by {deadline}")
                when_txt = "; ".join(when_bits) or "dates on registration page"
                summary = f"{opp_type.rstrip('s').title()} hosted by {org_name or 'organizer TBC'}. {when_txt}."
                items.append({
                    "title": title,
                    "link": seo_url,
                    "source": "Unstop",
                    "published": None,
                    "summary": summary,
                    "image_url": None,
                    "feed_url": f"opportunities:unstop:{opp_type}:{term}",
                    "event_date": event_date,
                    "deadline": deadline,
                })
                seen_ids.add(oid)
                kept += 1
    print(f"fetch_opportunities: unstop — {fetched} fetched, {kept} kept after quality filter")
    return items


# ---------------------------------------------------------------------------
# 2. 10times.com
# ---------------------------------------------------------------------------
TENTIMES_PAGES = (
    ("https://10times.com/india/technology", "10times (India Tech)"),
    ("https://10times.com/india/artificial-intelligence", "10times (India AI)"),
)


def _parse_10times(html_text):
    """Each event lives inside one 'event-card event_<id>' block. We bound
    each block from its own marker to the NEXT marker so we never pick up
    matches from an unrelated 'related events' widget elsewhere on the page
    (verified live: that widget carries its own date/url/label triples with
    no 'event-card event_' wrapper at all)."""
    events = []
    starts = [m.start() for m in re.finditer(r"event-card event_\d+", html_text)]
    starts.append(len(html_text))
    for i in range(len(starts) - 1):
        block = html_text[starts[i]:starts[i + 1]]
        date_m = re.search(r'data-start-date="([\d/]+)"', block)
        url_m = re.search(r"onclick=\"window\.open\('([^']+)'\)\"", block)
        label_m = re.search(r'data-ga-label="To ([^"]+)"', block)
        if not (date_m and url_m and label_m):
            continue
        events.append({
            "title": htmllib.unescape(label_m.group(1)),
            "link": url_m.group(1),
            "event_date": date_m.group(1).replace("/", "-"),
        })
    return events


def fetch_10times():
    items = []
    fetched = kept = 0
    for url, label in TENTIMES_PAGES:
        try:
            html_text = _get(url)
        except Exception as ex:                            # noqa: BLE001
            print(f"fetch_opportunities: 10times [{url}] failed: {ex!r}")
            continue
        if not html_text:
            print(f"fetch_opportunities: 10times [{url}] returned empty body")
            continue
        events = _parse_10times(html_text)
        fetched += len(events)
        for e in events:
            if _is_conference_mill(e["title"]):
                continue          # P11: skip predatory/no-name academic mills
            ed = _iso(e["event_date"])
            items.append({
                "title": e["title"],
                "link": e["link"],
                "source": label,
                "published": None,
                "summary": f"Listed on 10times. {'Runs ' + ed if ed else 'Date on event page'}.",
                "image_url": None,
                "feed_url": f"opportunities:10times:{url}",
                "event_date": ed,
                "deadline": None,
            })
            kept += 1
    print(f"fetch_opportunities: 10times — {fetched} fetched, {kept} kept")
    return items


# ---------------------------------------------------------------------------
# 3. Lu.ma
# ---------------------------------------------------------------------------
LUMA_CITIES = ("new-delhi", "mumbai", "bengaluru")   # no Jaipur page exists
_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def fetch_luma():
    items = []
    fetched = kept = 0
    for city in LUMA_CITIES:
        url = f"https://lu.ma/{city}"
        try:
            html_text = _get(url)
        except Exception as ex:                            # noqa: BLE001
            print(f"fetch_opportunities: luma [{city}] failed: {ex!r}")
            continue
        m = _NEXT_DATA_RE.search(html_text or "")
        if not m:
            print(f"fetch_opportunities: luma [{city}] — no __NEXT_DATA__ found")
            continue
        try:
            data = json.loads(m.group(1))
            events = data["props"]["pageProps"]["initialData"]["data"]["events"]
        except Exception as ex:                            # noqa: BLE001
            print(f"fetch_opportunities: luma [{city}] — unexpected JSON shape: {ex!r}")
            continue
        fetched += len(events)
        for wrapper in events:
            ev = (wrapper or {}).get("event") or {}
            name = ev.get("name")
            slug = ev.get("url")
            start_at = ev.get("start_at")
            if not (name and slug and start_at):
                continue
            ed = _iso(start_at)
            items.append({
                "title": name,
                "link": f"https://lu.ma/{slug}",
                "source": f"Luma ({city.replace('-', ' ').title()})",
                "published": None,
                "summary": f"Local event via Luma. {'On ' + ed if ed else 'Date on event page'}.",
                "image_url": ev.get("cover_url"),
                "feed_url": f"opportunities:luma:{city}",
                "event_date": ed,
                "deadline": None,
            })
            kept += 1
    print(f"fetch_opportunities: luma — {fetched} fetched, {kept} kept")
    return items


# ---------------------------------------------------------------------------
# 4. Devpost
# ---------------------------------------------------------------------------
def fetch_devpost():
    url = "https://devpost.com/api/hackathons?status[]=upcoming&order_by=recently-added"
    try:
        # REQUIRES a full desktop Chrome UA or it 403s (backlog note, verified).
        data = _get_json(url, headers={"User-Agent": BROWSER_UA})
    except Exception as ex:                                # noqa: BLE001
        print(f"fetch_opportunities: devpost failed: {ex!r}")
        return []
    rows = (data or {}).get("hackathons") or []
    items = []
    for h in rows:
        title = (h.get("title") or "").strip()
        link = h.get("url")
        if not (title and link):
            continue
        submission_dates = h.get("submission_period_dates") or ""
        items.append({
            "title": title,
            "link": link,
            "source": "Devpost",
            "published": None,
            "summary": f"Global hackathon via Devpost. {submission_dates or 'Dates on event page'}.",
            "image_url": ("https:" + h["thumbnail_url"]) if h.get("thumbnail_url", "").startswith("//") else h.get("thumbnail_url"),
            "feed_url": "opportunities:devpost",
            "event_date": None,   # Devpost gives a free-text date range, not ISO — leave
            "deadline": None,     # unset rather than guess; build_digest's regex fallback
                                  # (extract_event_date over title+summary) still applies.
        })
    print(f"fetch_opportunities: devpost — {len(rows)} fetched, {len(items)} kept")
    return items


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    all_items = []
    counts = {}
    for name, fn in (("unstop", fetch_unstop), ("10times", fetch_10times),
                     ("luma", fetch_luma), ("devpost", fetch_devpost)):
        try:
            got = fn()
        except Exception as ex:                            # noqa: BLE001 — one source
            print(f"fetch_opportunities: {name} crashed unexpectedly: {ex!r}")
            got = []
        counts[name] = len(got)
        all_items.extend(got)

    payload = {
        "generated_at": now.isoformat(),
        "source_counts": counts,
        "items": all_items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Wrote {OUT.relative_to(ROOT)}: {len(all_items)} total items "
          f"({', '.join(f'{k}={v}' for k, v in counts.items())})")


if __name__ == "__main__":
    main()
