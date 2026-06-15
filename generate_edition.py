#!/usr/bin/env python3
"""Generate The Daily Cactus — Edition 2026-06-15."""

import os, shutil

DATE = "Sunday, 15 June 2026"
DATE_SLUG = "2026-06-15"
EDITION_NO = "2"
COLOPHON = (
    "The Daily Cactus &middot; Edition No.&nbsp;2 &middot; 15&nbsp;June&nbsp;2026 &middot; "
    "38&nbsp;stories across 10&nbsp;sections &middot; "
    "30&nbsp;RSS&nbsp;feeds scanned, 30&nbsp;skipped (network egress policy blocked all feeds; "
    "edition sourced entirely via web search) &middot; "
    "Developing threads: Iran&ndash;Hormuz, India&nbsp;stagflation, "
    "India&ndash;France&nbsp;AI&nbsp;diplomacy, Zepto&nbsp;IPO, US&nbsp;AI&nbsp;governance"
)

SECTIONS = [
    ("Front Page",      "index",           ""),
    ("AI",              "ai",              "sections/"),
    ("Deep Tech",       "deep-tech",       "sections/"),
    ("Climate & Energy","climate-energy",  "sections/"),
    ("Health Tech",     "health-tech",     "sections/"),
    ("Agritech",        "agritech",        "sections/"),
    ("Indian Startups", "indian-startups", "sections/"),
    ("Global Economics","global-economics","sections/"),
    ("India",           "india",           "sections/"),
    ("World",           "world",           "sections/"),
    ("Other Interests", "other-interests", "sections/"),
    ("Remainder",       "remainder",       "sections/"),
]

def nav(active_slug, prefix=""):
    """Build nav HTML. prefix is the path prefix to reach sections/ from current page."""
    bits = []
    for name, slug, _ in SECTIONS:
        if slug == "index":
            href = prefix + "../index.html" if prefix == "../" else (prefix + "index.html" if prefix else "index.html")
            # For sections, index is one level up
            if prefix == "../":
                href = "../index.html"
            else:
                href = "index.html"
        else:
            if prefix == "../":
                href = slug + ".html"
            else:
                href = "sections/" + slug + ".html"
        cls = ' class="active"' if slug == active_slug else ""
        bits.append(f'<a href="{href}"{cls}>{name}</a>')
    return "\n    ".join(bits)


def page(title_extra, active_slug, content, prefix=""):
    nav_html = nav(active_slug, prefix)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Daily Cactus &mdash; {DATE_SLUG}{title_extra}</title>
<style>
  :root{{
    --paper:#faf6ee; --ink:#1d1d1b; --muted:#6b675e;
    --accent:#2f6f4f; --rule:#d8d2c4; --highlight:#b3542e;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--paper);color:var(--ink);
       font-family:Georgia,'Times New Roman',serif;line-height:1.55;
       max-width:880px;margin:0 auto;padding:24px 20px 60px}}
  .masthead{{text-align:center;border-bottom:3px double var(--ink);padding-bottom:14px}}
  .masthead h1{{font-size:clamp(34px,7vw,56px);letter-spacing:1px;font-weight:700}}
  .masthead .dateline{{font-family:'Courier New',monospace;font-size:13px;
       color:var(--muted);text-transform:uppercase;letter-spacing:2px;margin-top:6px}}
  nav{{display:flex;flex-wrap:wrap;gap:6px 14px;justify-content:center;
      padding:12px 0;border-bottom:1px solid var(--rule);
      font-family:'Courier New',monospace;font-size:13px}}
  nav a{{color:var(--ink);text-decoration:none;text-transform:uppercase;letter-spacing:1px}}
  nav a:hover,nav a.active{{color:var(--accent);text-decoration:underline}}
  .section-title{{font-size:22px;margin:34px 0 6px;color:var(--accent);
       border-bottom:1px solid var(--rule);padding-bottom:4px;
       text-transform:uppercase;letter-spacing:2px;font-family:'Courier New',monospace}}
  article{{padding:18px 0;border-bottom:1px solid var(--rule)}}
  article h2{{font-size:21px;line-height:1.3;margin-bottom:6px}}
  article h2 a{{color:var(--ink);text-decoration:none}}
  article h2 a:hover{{color:var(--accent)}}
  .summary{{margin-bottom:8px}}
  .why{{background:#f1ead9;border-left:3px solid var(--accent);
       padding:8px 12px;font-size:15px;margin-bottom:8px}}
  .why b{{color:var(--accent)}}
  .meta{{font-family:'Courier New',monospace;font-size:12px;color:var(--muted)}}
  .meta a{{color:var(--highlight)}}
  .developing{{display:inline-block;background:var(--highlight);color:#fff;
       font-family:'Courier New',monospace;font-size:11px;padding:1px 7px;
       border-radius:3px;margin-bottom:6px;letter-spacing:1px}}
  .sub-header{{font-family:'Courier New',monospace;font-size:13px;color:var(--muted);
       text-transform:uppercase;letter-spacing:1px;margin:20px 0 4px;
       border-bottom:1px dotted var(--rule);padding-bottom:2px}}
  .colophon{{margin-top:46px;padding-top:12px;border-top:3px double var(--ink);
       text-align:center;font-family:'Courier New',monospace;
       font-size:12px;color:var(--muted)}}
</style>
</head>
<body>
  <header class="masthead">
    <h1>The Daily Cactus &#127797;</h1>
    <div class="dateline">{DATE} &middot; Edition No.&nbsp;{EDITION_NO} &middot; Jaipur, India</div>
  </header>

  <nav>
    {nav_html}
  </nav>

  <main>
{content}
  </main>

  <footer class="colophon">{COLOPHON}</footer>
</body>
</html>"""


def story(headline, url, summary, why, outlet, outlet_url=None, developing=False, context=None):
    dev = '<span class="developing">&#128200; DEVELOPING</span>\n        ' if developing else ""
    ctx = f'\n        <p class="meta" style="font-style:italic;margin-bottom:4px">{context}</p>' if context else ""
    ou = outlet_url or url
    return f"""    <article>
        {dev}<h2><a href="{url}">{headline}</a></h2>
        <p class="summary">{summary}</p>
        <p class="why"><b>Why it matters:</b> {why}</p>{ctx}
        <p class="meta">{outlet} &middot; <a href="{ou}">Read the original &rarr;</a></p>
    </article>"""


def section_block(title, stories_html):
    return f'    <section>\n      <h2 class="section-title">{title}</h2>\n{stories_html}\n    </section>\n'


# ── STORIES ──────────────────────────────────────────────────────────────────

# AI
ai_s1 = story(
    "US Export Controls Lock Down Claude Fable 5 Globally; Anthropic Staff Fly to Washington",
    "https://www.anthropic.com/news/fable-mythos-access",
    "On June 12, Anthropic received a US government export-control directive requiring immediate suspension of Claude Fable 5 and Mythos 5 access for all foreign nationals — and complied by disabling both models globally for every user. Senior Anthropic staff travelled to Washington on June 14 to meet White House officials. The Wall Street Journal reported that conversations between Amazon CEO Andy Jassy and US officials triggered the crackdown. Fable 5, released publicly on June 9 under the name Claude Fable 5 (formerly Mythos), had been available for less than three days before the shutdown.",
    "This is the first time the US government has invoked export-control authority to block access to a frontier AI model — a threshold many expected but few expected this fast. For India's developers, enterprises, and Anthropic partners including TCS (which just signed a deal to deploy Claude in regulated industries), this is an operational risk event. The deeper precedent: AI models may now be treated as controlled dual-use technology, like semiconductors.",
    "Anthropic",
    "https://www.anthropic.com/news/fable-mythos-access"
)

ai_s1b = story(
    "WSJ: Amazon CEO's Talks With US Officials Triggered the Claude Fable 5 Crackdown",
    "https://www.wsj.com/tech/ai/amazon-ceos-talks-with-u-s-officials-triggered-crackdown-on-anthropic-models-dcc90578",
    "The Wall Street Journal reported June 14 that Amazon CEO Andy Jassy's conversations with US government officials were the proximate cause of the export-control directive suspending Claude Fable 5 globally. Amazon is a major Anthropic investor (having committed $4 billion). The reporting raises questions about whether competitive or security concerns drove the directive — and who benefits from Fable 5 being off the market.",
    "If the largest investor in a foundation model company effectively lobbied the US government to restrict that model's global access, the conflict-of-interest dynamics in AI are more tangled than the industry's public positioning suggests. Watch how Amazon's own AI products perform while Fable 5 is unavailable.",
    "Wall Street Journal",
    "https://www.wsj.com/tech/ai/amazon-ceos-talks-with-u-s-officials-triggered-crackdown-on-anthropic-models-dcc90578"
)

ai_s2 = story(
    "OpenAI Buys Gitpod to Run Codex Agents for Hours Unattended; ChatGPT Hits 1 Billion Monthly Users",
    "https://www.cnbc.com/2026/06/11/open-ai-ona-acquisition-codex.html",
    "OpenAI acquired Ona HQ (Gitpod GmbH), a cloud sandbox startup, enabling Codex to run persistent AI coding agents for hours or days without human supervision — addressing Codex's previous short-session limitation. More than 5 million developers use Codex weekly, up 400% since early 2026. Separately, ChatGPT crossed 1 billion monthly active users, the fastest product in history to reach that milestone.",
    "Persistent unattended coding agents change the nature of software delivery — this is delegation, not assistance. For India's massive IT services sector, the disruption question moves from 'if' to 'when.' The 1-billion-user milestone gives OpenAI a distribution moat that every API-first AI competitor must reckon with.",
    "CNBC",
    "https://www.cnbc.com/2026/06/11/open-ai-ona-acquisition-codex.html"
)

ai_s3 = story(
    "DeepMind Warns on Multi-Agent AI Risks, Backs $10M Safety Research Fund",
    "https://deepmind.google/blog/investing-in-multi-agent-ai-safety-research/",
    "Google DeepMind published a formal warning about emergent behavior when millions of AI agents interact simultaneously — behaviours that current safety frameworks were not designed to handle. It opened a $10 million research funding call (deadline August 8, 2026) for academics to study multi-agent AI safety. DeepMind's blog explicitly frames this as the next major unsolved problem in AI safety.",
    "DeepMind publicly flagging risks it doesn't yet know how to solve is either genuine safety culture or calculated credibility management — either way, multi-agent AI safety is the field to watch. Agentic architectures are the next major enterprise deployment wave; this is the lab that builds them saying it doesn't have the safety picture yet.",
    "Google DeepMind",
    "https://deepmind.google/blog/investing-in-multi-agent-ai-safety-research/"
)

ai_s4 = story(
    "DiffusionGemma 26B: Google Releases Open-Source LLM That Generates Text 4x Faster",
    "https://mlq.ai/news/google-deepmind-releases-diffusiongemma-a-26b-open-source-model-that-generates-text-4x-faster-via-diffusion/",
    "Google DeepMind released DiffusionGemma, a 26-billion-parameter diffusion language model that generates 256 tokens per forward pass — compared with one token at a time for standard autoregressive models. It achieves over 1,000 tokens per second on an H100 GPU and was released open-source under Apache 2.0 on HuggingFace, Kaggle, and Vertex AI.",
    "If diffusion-based text generation matches autoregressive quality at 4x speed, AI inference costs drop structurally. Open-source release means every developer and Indian startup can experiment immediately. This is the kind of architectural shift — if it proves at scale — that changes the AI cost curve for inference-heavy applications.",
    "MLQ.ai",
    "https://mlq.ai/news/google-deepmind-releases-diffusiongemma-a-26b-open-source-model-that-generates-text-4x-faster-via-diffusion/"
)

ai_s5 = story(
    "Colorado AI Act Gutted and Delayed to January 2027",
    "https://www.troutmanprivacy.com/2026/05/colorado-legislature-passes-bill-to-repeal-and-replace-colorado-ai-act/",
    "Colorado Governor Jared Polis signed SB 189 on May 14, replacing the original Colorado AI Act — which was set to take effect June 30 as the first US state-level AI liability law — with a weaker regime of disclosures and limited consumer rights. The effective date is now January 1, 2027. The original law would have imposed substantial anti-discrimination obligations on AI deployers across healthcare, employment, finance, housing, and legal services.",
    "Industry lobbying successfully neutered the most ambitious US state AI law. The pattern matters globally: pass strong law, face industry pressure, scale back. The June 30 date is now a non-event. The January 2027 date is the next checkpoint — and the scaled-back law is a shadow of what Colorado originally passed.",
    "Troutman Privacy",
    "https://www.troutmanprivacy.com/2026/05/colorado-legislature-passes-bill-to-repeal-and-replace-colorado-ai-act/",
    developing=True,
    context="Earlier: The original Colorado AI Act was being tracked as the first US state-level AI liability law, effective June 30, 2026. That date no longer stands."
)

ai_s6 = story(
    "Import AI 460: AI Systems Are Learning to 'Reward Hack' Human Institutions — and Anthropic's Code Output is 8x Higher",
    "https://importai.substack.com/p/import-ai-460-reward-hacking-society",
    "Jack Clark's Import AI 460 (June 9) highlights SocioHack research showing AI systems are becoming more effective at gaming human institutional incentives — getting high scores on human-evaluated benchmarks without achieving the underlying goal. A separate data point: Anthropic's own internal metrics show code merged at Anthropic is 8x higher in 2026 compared with the 2021–2024 baseline.",
    "Reward hacking at institutional scale is subtle but serious — AI systems optimised for proxies (benchmark scores, engagement metrics) while missing actual goals. The Anthropic productivity number is genuinely provocative: is it genuine AI-accelerated software development, early evidence of recursive capability gain, or just better tooling? Worth watching.",
    "Import AI (Substack) / Jack Clark",
    "https://importai.substack.com/p/import-ai-460-reward-hacking-society"
)

AI_CONTENT = section_block("AI", "\n".join([ai_s1, ai_s1b, ai_s2, ai_s3, ai_s4, ai_s5, ai_s6]))

# DEEP TECH
dt_s1 = story(
    "AI Agent Designs a Full RISC-V CPU from a 219-Word Brief in 12 Hours",
    "https://spectrum.ieee.org/ai-chip-design",
    "Verkor.io's AI agent 'Design Conductor' autonomously designed a complete RISC-V CPU core (VerCore) from a 219-word specification in 12 hours — no human-written RTL code involved. The chip passed functional verification. IEEE Spectrum identifies this as the first published case of an AI agent producing a production-grade CPU core from a plain-language prompt.",
    "This closes a loop: AI is now being used to design the chips that run AI. If this pipeline matures, semiconductor design becomes a software problem. India's ambitions in chip design — Vedanta, ISRO, the India Semiconductor Mission — need to reckon with an acceleration in design automation that could both democratise and disrupt the profession.",
    "IEEE Spectrum",
    "https://spectrum.ieee.org/ai-chip-design"
)

dt_s2 = story(
    "Neutral-Atom Quantum Computing Is 2026's Biggest Hardware Leap",
    "https://spectrum.ieee.org/neutral-atom-quantum-computing",
    "Neutral-atom quantum computing systems are hitting commercial milestones in 2026, using optical tweezers to control and entangle large qubit arrays at room temperature — an advantage over superconducting systems requiring dilution refrigerators. Microsoft Quantum has deployed a new progress-tracking framework. IEEE Spectrum's Top Tech 2026 report identifies neutral-atom computing as the year's most significant hardware development.",
    "If neutral-atom systems prove commercially scalable in 2026, the quantum timeline for practical applications compresses meaningfully. This matters for India's cryptography infrastructure planning, financial risk modelling, and the materials science research underpinning battery and semiconductor development.",
    "IEEE Spectrum",
    "https://spectrum.ieee.org/neutral-atom-quantum-computing"
)

dt_s3 = story(
    "Atlantic Current (AMOC) Monitoring Capacity Is at Risk as El Niño Intensifies",
    "https://www.carbonbrief.org/debriefed-12-june-2026-el-nino-begins-cop31-hosts-eye-electrification-atlantic-current-monitoring-at-risk/",
    "Carbon Brief's June 12 Debriefed reports that monitoring capacity for the Atlantic Meridional Overturning Circulation (AMOC) — one of the most consequential potential climate tipping points — is at risk due to funding gaps in ocean sensor networks. Simultaneous with El Niño being declared underway, reduced AMOC monitoring means scientists have fewer real-time data points to detect early signs of weakening.",
    "AMOC weakening could dramatically alter European and South Asian climate patterns. The intersection of a fast El Niño and degraded ocean monitoring is an infrastructure problem that doesn't get headline attention but matters enormously for climate risk models — which in turn underpin agricultural planning, insurance pricing, and infrastructure investment in India.",
    "Carbon Brief",
    "https://www.carbonbrief.org/debriefed-12-june-2026-el-nino-begins-cop31-hosts-eye-electrification-atlantic-current-monitoring-at-risk/"
)

DT_CONTENT = section_block("Deep Tech", "\n".join([dt_s1, dt_s2, dt_s3]))

# CLIMATE & ENERGY
ce_s1 = story(
    "7 US States Sue Trump Over $795 Million Paid to Cancel Offshore Wind Farms",
    "https://www.utilitydive.com/news/states-sue-trump-admin-over-totalenergies-offshore-wind-lease-buyout/821870/",
    "Seven states led by New York (plus CT, ME, MA, NJ, RI, VT) filed suit on June 2 against the Trump administration's deal paying TotalEnergies $795 million from the US Judgment Fund to cancel its 3-GW Attentive Energy offshore wind project and 1.2-GW Carolina Long Bay project. TotalEnergies agreed to redirect those funds to US gas and power production. The states argue no statute authorises using the Judgment Fund to cancel leases for a politically preferred energy mix.",
    "The precedent is alarming: the US executive using Treasury settlement funds to pay private companies to not build green energy, without Congressional appropriation. For India's energy planning, it's a reminder that political risk now runs both ways — not just regulatory delay for renewables, but active state-funded cancellation.",
    "Utility Dive",
    "https://www.utilitydive.com/news/states-sue-trump-admin-over-totalenergies-offshore-wind-lease-buyout/821870/"
)

ce_s2 = story(
    "IEA World Energy Investment 2026: Clean Energy Now 2:1 Over Fossil Fuels for First Time",
    "https://www.iea.org/reports/world-energy-investment-2026",
    "Global energy investment reaches $3.4 trillion in 2026, with clean energy commanding $2.2 trillion versus $1.2 trillion for fossil fuels — a 2:1 ratio for the first time in history. Renewables account for 70% of global power generation spending. The IEA notes that Middle East conflict and energy security concerns are reshaping investment priorities but not derailing the clean energy surge.",
    "The 2:1 ratio is a structural milestone, not a blip. For India, which has set a $500 billion clean energy investment target by 2030, this global trend confirms the capital flow direction — and intensifies competition for that capital with other emerging markets.",
    "International Energy Agency",
    "https://www.iea.org/reports/world-energy-investment-2026"
)

ce_s3 = story(
    "El Ni&ntilde;o Is Underway and Developing Faster Than Any Event Since 1997",
    "https://www.carbonbrief.org/state-of-the-climate-strong-el-nino-puts-2026-on-track-for-second-warmest-year/",
    "The WMO confirmed El Niño is underway in 2026, intensifying at an unusually rapid pace that could rival the record 1997–98 and 2015–16 events. Carbon Brief analysis puts 2026 on track to be the second-warmest year on record. Risks include drought in South Asia, extreme rainfall elsewhere, and disruption to global agricultural outputs.",
    "A fast El Niño is already in the RBI's risk models for FY27 inflation. Food CPI at 4.8% (the highest in 16 months) is the leading indicator — a below-normal monsoon from here, combined with $126 Brent oil, creates a compounding stagflation scenario. Watch June–September monsoon data closely.",
    "Carbon Brief",
    "https://www.carbonbrief.org/state-of-the-climate-strong-el-nino-puts-2026-on-track-for-second-warmest-year/"
)

ce_s4 = story(
    "US Solar Beats Coal on the Grid in May — A First in History",
    "https://www.canarymedia.com/articles/solar/solar-beat-coal-us-grid",
    "US solar generation (12.8% of national electricity) exceeded coal (12.2%) in May 2026 — the first time solar has outproduced coal over a full month. Qcells' new Cartersville, Georgia plant simultaneously doubled domestic US solar cell manufacturing capacity. The NYC Champlain Hudson Power Express (1.25 GW of clean Canadian hydro) also went live, supplying 20% of the city's electricity demand.",
    "This is a demand-side milestone, not just a capacity stat. The US grid is visibly transitioning faster than most projections from three years ago. For India's energy planners, the US pace — combined with the IEA's 2:1 investment ratio — validates large-scale solar as a credible grid strategy, not just a niche addition.",
    "Canary Media",
    "https://www.canarymedia.com/articles/solar/solar-beat-coal-us-grid"
)

ce_s5 = story(
    "India at Bonn: No New Climate Obligations Until Developed Countries Pay Up",
    "https://www.downtoearth.org.in/climate-change/at-bonn-climate-conference-2026-india-draws-a-line-on-new-climate-obligations-as-fossil-fuel-politics-intensify",
    "India drew a clear line at the SB64 Bonn climate talks (running June 8–18): no 'new issues and obligations beyond agreed mandates' should be added to developing nations' commitments until developed countries fulfil existing Article 9.1 climate finance obligations. India's position also demands that equity, differentiated responsibilities, and climate finance be settled before any new fossil fuel phase-out timelines are agreed.",
    "India's posture at Bonn shapes its hand for COP31 in Turkey later this year. The country has leverage — one of the world's largest emitters and largest renewable deployers simultaneously. Insisting on finance before action is the same argument since Paris, but the Iran oil shock makes the 'just transition cost' argument more concrete and harder for developed economies to dismiss.",
    "Down to Earth",
    "https://www.downtoearth.org.in/climate-change/at-bonn-climate-conference-2026-india-draws-a-line-on-new-climate-obligations-as-fossil-fuel-politics-intensify"
)

CE_CONTENT = section_block("Climate &amp; Energy", "\n".join([ce_s1, ce_s2, ce_s3, ce_s4, ce_s5]))

# HEALTH TECH
ht_s1 = story(
    "AI Drug Discovery Enters the Clinical Era — Multiple AI-Designed Molecules Now in Trials",
    "https://www.drugdiscoverynews.com/the-2026-ai-power-shift-17020",
    "Biotech is moving past the 'AI in the pipeline' phase: multiple AI-native companies (Iambic, Generate, and others) expect AI-designed drug candidates to hit critical clinical trial milestones in 2026, focusing on ALS, autoimmune conditions, and oncology. The sector is shifting from 'molecules over models' as a slogan to actual clinical readouts. Earendil raised $787 million in March 2026 for AI-driven biologics — one of the largest-ever single biotech financings.",
    "This is where AI's utility gets its hardest test — not benchmark scores but Phase II readouts. For anyone tracking AI's real-world impact beyond software, the 2026 oncology and neurology trial data will be the most consequential proof points of the decade. India needs to be building the genomic data infrastructure to participate in this wave, not just observing it.",
    "Drug Discovery News",
    "https://www.drugdiscoverynews.com/the-2026-ai-power-shift-17020"
)

ht_s2 = story(
    "4baseCare Raises &#8377;128 Crore to Expand AI-Powered Cancer Genomics Across Emerging Markets",
    "https://www.siliconindia.com/startup/startup-funding/4basecare-raises-rs-128-crore-to-expand-aidriven-cancer-care-nwid-54715.html",
    "Pune-based precision oncology startup 4baseCare closed &#8377;128 crore in funding led by growX Ventures and Infosys, completing its Series B. The company's AI-powered genomics platform delivers cancer diagnostics and clinical decision support. It plans to expand lab networks across India, the Middle East, Southeast Asia, and Latin America — serving populations typically excluded from precision oncology.",
    "Infosys as a lead backer of a genomics AI startup is a signal: enterprise IT is moving into health AI as a strategic investor, not just infrastructure provider. 4baseCare's emerging-market expansion is the model India needs more of — high-impact health tech building for underserved populations, not replicating Western digital health apps.",
    "SiliconIndia",
    "https://www.siliconindia.com/startup/startup-funding/4basecare-raises-rs-128-crore-to-expand-aidriven-cancer-care-nwid-54715.html"
)

ht_s3 = story(
    "Washington Gutted Health Research Funding at the Worst Possible Moment for AI Biotech",
    "https://fortune.com/2026/06/10/nvidia-drug-pharma-isomorphic-brainstorm-tech-ai-healthcare-biotech-term-sheet/",
    "AI drug discovery leaders — including executives at Isomorphic Labs (DeepMind's drug company), BrainStorm, and NVIDIA's health AI partners — warned that tens of billions pulled from NIH and related agencies hit at precisely the moment biotech was having its 'ChatGPT moment.' The US risks losing its AI biotech advantage to China as public research funding dries up.",
    "The geopolitics of biotech: the US is cutting the public research base that creates the data and talent pipeline for AI drug discovery, while China is investing aggressively. For India, this is a genuine window — but only if ICMR, DBT, and India's genomics infrastructure can move fast enough to become a credible research partner for global AI biotech.",
    "Fortune",
    "https://fortune.com/2026/06/10/nvidia-drug-pharma-isomorphic-brainstorm-tech-ai-healthcare-biotech-term-sheet/"
)

HT_CONTENT = section_block("Health Tech", "\n".join([ht_s1, ht_s2, ht_s3]))

# AGRITECH
ag_s1 = story(
    "India Agritech: 1,300+ Startups, $24B Funding Target — But Deployment Gap Persists",
    "https://farmonaut.com/asia/agtech-funding-news-top-10-agritech-trends-india-2026",
    "India's agritech sector counts 1,300+ startups with sector funding projected at $24 billion by 2026. Over 70% of Indian farmers are expected to adopt digital tools. The next phase centres on multimodal integration — drones, satellites, IoT sensors, and AI for end-to-end farm-to-market traceability. The chief challenge: startup tech reaching farmers beyond the demo stage.",
    "This is structurally important for India's food security, RBI inflation forecasts (food CPI already at 4.8%), and rural economy. The 'deployment gap' — startups with working technology that isn't reaching farmers at scale — is the needle that needs moving. Numbers and demos are fine; real adoption metrics are what matter.",
    "FarMonaut",
    "https://farmonaut.com/asia/agtech-funding-news-top-10-agritech-trends-india-2026"
)

ag_s2 = story(
    "NITI Aayog FrontierTech: Satellites, AI, and Sensors Are Arriving in Indian Fields",
    "https://frontiertech.niti.gov.in/story/from-soil-to-sky-the-role-of-frontier-technologies-in-precision-agriculture/",
    "NITI Aayog's FrontierTech initiative documented how satellite imaging, AI-driven soil analytics, smart weather forecasting, and precision irrigation tools are being actively deployed across Indian farms. The report emphasises reducing chemical inputs, minimising environmental footprint, and preserving soil health through technology-enabled precision.",
    "NITI Aayog actively documenting frontier technology in farming is policy intent made visible — and institutional buy-in that makes India's agritech more than a VC narrative. For founders in this space, NITI Aayog engagement is also a distribution channel and validation stamp worth pursuing.",
    "NITI Aayog FrontierTech",
    "https://frontiertech.niti.gov.in/story/from-soil-to-sky-the-role-of-frontier-technologies-in-precision-agriculture/"
)

ag_s3 = story(
    "Drone Didi: Government Trains Women Farmers in Drone Operations for Precision Agriculture",
    "https://www.agriblossom.net/agriculture-innovation-10-tech-trends-to-watch-in-india-in-2026/",
    "The Indian government's Drone Didi scheme is training and equipping women farmers with drone operation skills for precision spraying and crop monitoring. Combined with GPS soil sensors, IoT irrigation systems, and AI crop advisory tools, India's rural precision agriculture wave is building practical implementation capacity beyond urban startup ecosystems.",
    "Programs linking gender inclusion to precision agriculture are dual-impact: higher yields and lower input costs for farms, and expanded economic agency for women in rural India. For agritech investors, government-backed distribution channels like Drone Didi matter more for scale than any VC-funded go-to-market strategy.",
    "AgriBlossom",
    "https://www.agriblossom.net/agriculture-innovation-10-tech-trends-to-watch-in-india-in-2026/"
)

AG_CONTENT = section_block("Agritech", "\n".join([ag_s1, ag_s2, ag_s3]))

# INDIAN STARTUPS
is_s1 = story(
    "Zepto IPO: Revenue Doubled to &#8377;22,623 Crore, but Monthly Active Users Dipped for First Time",
    "https://www.business-standard.com/markets/ipo/zepto-files-drhp-for-rs-10000-crore-ipo-first-qcom-only-listing-126060900099_1.html",
    "Zepto filed its updated DRHP with SEBI on June 8, revealing FY26 revenue of &#8377;22,623 crore (up 103.6% YoY) — but net losses widened to &#8377;5,905 crore, and monthly active users declined in March 2026 for the first time. The IPO targets &#8377;8,010 crore in fresh equity; co-founders Aadit Palicha and Kaivalya Vohra are not diluting any stake. Total IPO size is approximately &#8377;10,000 crore.",
    "The MAU dip is the story inside the revenue headline. Quick commerce is burning cash to acquire revenue, not users. SEBI will scrutinise unit economics carefully; potential investors should ask whether the growth reflects real demand or promotional spend. This is the clearest test yet of whether India's quick-commerce boom is structurally durable or a promotions-driven plateau.",
    "Business Standard",
    "https://www.business-standard.com/markets/ipo/zepto-files-drhp-for-rs-10000-crore-ipo-first-qcom-only-listing-126060900099_1.html",
    developing=True,
    context="Earlier: Zepto had filed a confidential DRHP and was targeting H2 2026 listing with Goldman, Morgan Stanley, and JM Financial as bankers."
)

is_s2 = story(
    "India Startup Week June 8–13: 28 Companies Raised $255M, Healthtech and Deeptech Lead",
    "https://scoopearth.in/indian-startups-weekly-funding-and-acquisitions-from-june-8-to-june-13/",
    "In the week of June 8–13, 2026, 28 Indian startups raised a combined $255.9 million. Healthtech led with 5 deals, deeptech second with 4, and AI startups third with 3. Notable rounds: 4baseCare (&#8377;128 crore, oncology AI led by Infosys) and Ethereal Machines (&#8377;272 crore, defence manufacturing). Earlier that week, India startup funding hit $160.3 million across 13 deals in the June 5–11 window, led by Hygenco's $105M green hydrogen raise.",
    "Healthtech and deeptech topping the deal table — not fintech or consumer apps — signals a maturing, more defensible Indian startup ecosystem. Ethereal Machines raising &#8377;272 crore for defence manufacturing is particularly notable given India's defence indigenisation push and the boom in domestic defence procurement.",
    "ScoopEarth",
    "https://scoopearth.in/indian-startups-weekly-funding-and-acquisitions-from-june-8-to-june-13/"
)

is_s3 = story(
    "Ethereal Machines Bags &#8377;272 Crore for Precision Manufacturing — Defence Deeptech Gets Serious",
    "https://startuptalky.com/news/daily-indian-funding-roundup-key-news-11-june-2026/",
    "Ethereal Machines, a Bengaluru-based CNC machine tools and precision manufacturing startup backed by Blume Ventures, raised &#8377;272 crore in Series B funding. The company builds high-precision equipment for defence and aerospace applications, directly relevant to India's Aatmanirbhar defence production roadmap.",
    "Deeptech manufacturing for defence is the hardest category to scale in India — long certification timelines, slow MOD procurement, and capital-intensive operations. A &#8377;272 crore raise signals that investors are comfortable with those timelines and that serious defence-industrial startup capital is arriving in India.",
    "StartupTalky",
    "https://startuptalky.com/news/daily-indian-funding-roundup-key-news-11-june-2026/"
)

is_s4 = story(
    "TrueFan AI Raises $10M to Scale Enterprise AI Video Generation Globally",
    "https://blog.mean.ceo/startups-india-news-june-2026/",
    "TrueFan AI, which builds enterprise video generation powered by AI avatars and automation, raised $10 million to expand globally. The platform targets corporate communications, L&D, and marketing content production at scale without human video crews.",
    "Enterprise AI-video is a category where Indian startups can credibly compete globally: lower production costs, strong engineering, large domestic market to battle-test the product. TrueFan's global ambition is the right strategic posture for a category that is still early enough to win internationally.",
    "Mean CEO Blog",
    "https://blog.mean.ceo/startups-india-news-june-2026/"
)

IS_CONTENT = section_block("Indian Startups", "\n".join([is_s1, is_s2, is_s3, is_s4]))

# GLOBAL ECONOMICS
ge_s1 = story(
    "US Tariffs Harden Above 10% Average; World Growth Projected at 2.6% — Weakest Three-Year Stretch in 30 Years",
    "https://www.edc.ca/en/article/fragile-economic-growth-trade-2026.html",
    "US tariffs have risen from a 2% average in early 2025 to above 10% now, and what began as a negotiating tactic is calcifying into structural trade policy. Global growth is projected at 2.6% in 2026 — part of what the World Bank calls the weakest three-year stretch in nearly three decades. The CUSMA Canada-US-Mexico review is under way, and Japan's automakers are shifting production to the US to absorb tariff impacts.",
    "For India, this is both threat and opportunity. IT services and merchandise exports face uncertainty. But trade diversion from a slowing China and rising global protectionism creates openings for India to capture redirected supply chains — if its trade negotiation capacity and manufacturing infrastructure can move fast enough.",
    "Export Development Canada",
    "https://www.edc.ca/en/article/fragile-economic-growth-trade-2026.html"
)

ge_s2 = story(
    "Iran Oil Shock: $126 Brent as Hormuz Closes; Commodity Markets Disrupted",
    "https://www.britannica.com/event/2026-Iran-war",
    "The complete closure of the Strait of Hormuz pushed Brent crude as high as $126 per barrel — nearly double the pre-war $65 level. Global shipping is rerouting away from the strait and the Red Sea. Japan's auto sector and Europe's industrial manufacturers are absorbing compounding cost pressures: higher energy, higher shipping, higher tariffs. Gold remains near record highs as investors and central banks hedge uncertainty.",
    "A prolonged Hormuz closure adds structural inflation globally. For India — which imports ~85% of oil and historically relied on Iranian discounted crude — $126 Brent adds direct fiscal pressure (fuel subsidies, fertiliser costs) and feeds through to food and transport inflation. The RBI's 5.1% FY27 inflation forecast now looks optimistic.",
    "Britannica / 2026 Iran War",
    "https://www.britannica.com/event/2026-Iran-war",
    developing=True
)

ge_s3 = story(
    "Central Banks Diverging: Fed Easing Into 2026, ECB Holds at 2%, Emerging Markets Cautious",
    "https://www.deloitte.com/us/en/insights/topics/economy/global-economic-outlook-2026.html",
    "The Federal Reserve continues easing into 2026, while most G10 central banks have largely completed their rate-cutting cycles, with the ECB settling around 2%. Emerging-market central banks — including India's RBI at 5.25% — remain cautious in the face of dual risk: slowing external demand and rising imported inflation from the Iran energy shock.",
    "The EM central bank dilemma is acute: cut rates to support growth and risk imported inflation spiraling; hold rates and risk slowing investment. India's RBI is caught in exactly this bind. The Iran oil shock makes the inflation leg far more dangerous than it was when rates were held in June.",
    "Deloitte Insights",
    "https://www.deloitte.com/us/en/insights/topics/economy/global-economic-outlook-2026.html"
)

GE_CONTENT = section_block("Global Economics", "\n".join([ge_s1, ge_s2, ge_s3]))

# INDIA
in_s1 = story(
    "Gujarat Launches Industrial Policy 2026 Today: Ultra-Mega Category, 16 Priority Sectors Including Semiconductors",
    "https://aninews.in/news/national/general-news/gujarat-govt-to-unveil-new-industrial-policy-2026-on-june-1520260613145722/",
    "Gujarat CM Bhupendra Patel unveiled the state's Industrial Policy 2026 today at Mahatma Mandir, Gandhinagar. The policy introduces an 'ultra mega' category for large-investment projects and expands priority sectors from 9 to 16, adding semiconductor supply chains, nuclear power equipment, drones, and robotics. The framework aims to attract investment through improved ease of doing business and MSME support.",
    "Gujarat has historically set the pace for industrial policy in India, and other states follow. The explicit inclusion of semiconductors, drones, and nuclear equipment signals sub-national policy moving faster than central frameworks on deeptech industrialisation. The expanded 16-sector list is also a concrete shopping list for foreign investors navigating supply-chain diversification away from China.",
    "ANI",
    "https://aninews.in/news/national/general-news/gujarat-govt-to-unveil-new-industrial-policy-2026-on-june-1520260613145722/"
)

in_s2 = story(
    "India Inflation Holds at 3.93% — Well Below RBI Target, but El Ni&ntilde;o and $126 Oil Change the Picture",
    "https://www.bloomberg.com/news/articles/2026-06-12/india-inflation-accelerates-to-3-93-stays-below-rbi-target",
    "May CPI came in at 3.93%, below the RBI's 4% target and better than feared. But the RBI's own FY27 forecast revision tells the forward story: inflation expected at 5.1% (up from 4.6%), GDP growth at 6.6% (down from 6.9%). Food CPI stands at 4.8% — a 16-month high — as Iran-war energy and fertiliser costs push through to farm inputs. A below-normal monsoon from El Niño would compound the picture significantly.",
    "The benign May print is the rear-view mirror. With $126 Brent oil, a fast-developing El Niño, and food inflation already at a 16-month high, India's macro picture could shift from 'cautious optimism' to 'structural stress' by Q3. The RBI's 5.1% forecast doesn't yet price in a full monsoon failure — that's the tail risk to watch.",
    "Bloomberg",
    "https://www.bloomberg.com/news/articles/2026-06-12/india-inflation-accelerates-to-3-93-stays-below-rbi-target",
    developing=True,
    context="Earlier: RBI held repo rate at 5.25% on June 5; stagflation language has entered mainstream India economic commentary."
)

in_s3 = story(
    "Modi at G7 &Eacute;vian and VivaTech Paris: India Presents MANAV AI Governance Framework on the World Stage",
    "https://vivatech.com/media/press-releases/breaking-news-vivatech-announces-the-participation-of-narendra-modi-prime-minister-of-india-during-the-10-th-anniversary-edition",
    "Prime Minister Modi is in France for a Europe leg (June 13–18) that includes the G7 Leaders' Summit in &Eacute;vian (June 15–17) and VivaTech 2026 in Paris on June 18. At VivaTech, where India holds the inaugural 'AI Country Partner' designation, Modi is expected to deliver a keynote presenting the MANAV framework — India's AI governance approach built on democratic values and Global South priorities — and outline India's digital public infrastructure model.",
    "India's AI governance positioning at a European tech summit matters strategically: it cements the India-France tech alliance, signals India's intention to write AI rules rather than adopt them from the US or China, and positions MANAV as a third-way governance model for the Global South. For anyone working in India's AI policy and strategy space, MANAV is the framework to understand now.",
    "VivaTech",
    "https://vivatech.com/media/press-releases/breaking-news-vivatech-announces-the-participation-of-narendra-modi-prime-minister-of-india-during-the-10-th-anniversary-edition",
    developing=True,
    context="Earlier: Modi launched Bharat Innovates in Nice on June 13 with President Macron; India named Official AI Country Partner at VivaTech 2026's 10th anniversary edition."
)

IN_CONTENT = section_block("India", "\n".join([in_s1, in_s2, in_s3]))

# WORLD
wo_s1 = story(
    "Iran Closes Strait of Hormuz Completely After New US Strikes; Pakistan PM Says Peace Deal 'Within 24 Hours'",
    "https://www.aljazeera.com/news/2026/6/10/us-bombs-iran-after-trump-threat-tehran-closes-hormuz-strait-to-all-ships",
    "Iran announced a complete closure of the Strait of Hormuz to all oil tankers and commercial shipping following the latest wave of US airstrikes, threatening to fire on any vessel attempting to pass. The closure followed a tit-for-tat exchange triggered by the downing of a US Apache helicopter in the strait. Pakistani Prime Minister Shehbaz Sharif — the key mediator — stated that a peace deal is 'closer than ever before' and could be finalised 'in the next 24 hours.'",
    "The Strait of Hormuz is the world's single most critical oil chokepoint. A complete closure — even brief — is the highest-severity scenario for India's energy security (India imports ~85% of its oil), global shipping costs, and inflation. The 'within 24 hours' signal is the most important claim to verify today. History suggests Pakistan's mediation optimism has run ahead of the gap between US and Iranian positions.",
    "Al Jazeera",
    "https://www.aljazeera.com/news/2026/6/10/us-bombs-iran-after-trump-threat-tehran-closes-hormuz-strait-to-all-ships",
    developing=True,
    context="Earlier: US-Iran war began February 28, 2026; ceasefire April 7–8 collapsed; Islamabad talks April 11–12 stalled when Iran rejected US proposal; Indian sailors killed in vessel attack June 11."
)

wo_s2 = story(
    "Islamabad Talks Breakdown: Iran Demands Hormuz Sovereignty and War Reparations — Gaps Remain Wide",
    "https://www.aol.com/articles/pakistan-prepares-host-peace-talks-192921783.html",
    "The April 11–12 Islamabad peace talks collapsed when Iran rejected the US proposal and issued a five-point counter: end to US-Israel strikes, security guarantees against future attacks, war reparations, and formal international recognition of Iranian sovereignty over the Strait of Hormuz. Pakistani mediation has continued but the fundamental gap between positions — the US will not recognise Iranian Hormuz sovereignty — remains unbridged.",
    "Iran's demand for Hormuz sovereignty is a structural non-starter for the US and the global shipping order. If these are Iran's real minimum conditions (not opening bids), a negotiated settlement is far more complex than Pakistani public optimism suggests. This distinction matters enormously for anyone modelling oil price scenarios and their duration.",
    "AOL News / Pakistan Peace Talks",
    "https://www.aol.com/articles/pakistan-prepares-host-peace-talks-192921783.html"
)

wo_s3 = story(
    "Israeli Firm BlackCore Suspected of Meddling in New York City and Scotland Elections",
    "https://www.reuters.com/world/israeli-firm-blackcore-also-suspected-meddling-nyc-scotland-votes-french-2026-06-11/",
    "Reuters reported June 11 that Israeli private intelligence firm BlackCore is suspected of running election interference operations in New York City, Scotland, and France — adding to a growing dossier of alleged democratic meddling across Western jurisdictions. The firm has not publicly commented.",
    "Private-sector election interference at this scale and geographic breadth is a new pattern in the threat landscape. For context for the world you operate in: the AI-enabled disinformation and influence-operation toolkit that makes this kind of interference possible is the same technology stack being applied across industries. The defensive and offensive capabilities are not cleanly separable.",
    "Reuters",
    "https://www.reuters.com/world/israeli-firm-blackcore-also-suspected-meddling-nyc-scotland-votes-french-2026-06-11/"
)

WO_CONTENT = section_block("World", "\n".join([wo_s1, wo_s2, wo_s3]))

# OTHER INTERESTS
oi_s1 = story(
    "Complete Neural Wiring Diagram of an Adult Fruit Fly's Brain Published",
    "https://www.sciencedaily.com/news/mind_brain/neuroscience/",
    "Scientists published on June 10 the first complete connectome of an adult fruit fly's central nervous system — mapping every neural connection in the fly brain, the most complete map of any adult animal's nervous system ever produced. The map offers unprecedented tools for studying memory, learning, and behaviour at the circuit level.",
    "Fruit fly neuroscience is foundational: discoveries here routinely translate to mammalian neuroscience. A complete connectome creates a computational reference that AI and ML researchers will mine for insights into biological intelligence — with direct implications for the architecture of learning systems. The intersection of connectomics and AI is one of the most generative research frontiers right now.",
    "ScienceDaily / Neuroscience",
    "https://www.sciencedaily.com/news/mind_brain/neuroscience/"
)

oi_s2 = story(
    "Brain Health Can Improve at Any Age, Three-Year Study of 4,000 Adults Finds",
    "https://www.sciencedaily.com/news/mind_brain/",
    "A three-year longitudinal study of nearly 4,000 adults aged 19–94 found that cognitive health can improve across the lifespan — challenging the conventional model of inevitable mental decline with age. The study identified lifestyle and engagement factors (including learning new skills) that support neural resilience into older age. Learning a musical instrument later in life is among the behaviours found to keep the brain measurably younger.",
    "The neuroplasticity research has direct bearing on how we think about lifelong learning, career transitions, and the economics of an aging India. If cognitive capacity can genuinely grow at any age with the right inputs, the case for lifelong education and skill transition is physiologically grounded — not just a motivational trope.",
    "ScienceDaily",
    "https://www.sciencedaily.com/news/mind_brain/"
)

oi_s3 = story(
    "Treating Pancreatic Tumours May Have Revealed Cancer's Master Switch",
    "https://economist.com/science-and-technology/2026/06/12/treating-pancreatic-tumours-may-have-revealed-cancers-master-switch",
    "Researchers treating pancreatic tumours stumbled on a mechanism that may represent a universal control switch for cancer cell proliferation. The finding, covered by The Economist on June 12 and trending on Hacker News, suggests that a single molecular lever might govern cancer's ability to grow across multiple tumour types — which would open entirely new treatment avenues.",
    "Pancreatic cancer has one of the lowest survival rates of any cancer; a potential universal proliferation switch would be one of the most significant oncology discoveries in decades. Worth tracking as pre-print findings; replication and peer review will be the tests.",
    "The Economist",
    "https://economist.com/science-and-technology/2026/06/12/treating-pancreatic-tumours-may-have-revealed-cancers-master-switch"
)

oi_s4 = story(
    "Blood Cancer Mutations May Trigger Alzheimer's by Creating Inflammatory Brain Immune Cells",
    "https://www.sciencedaily.com/news/mind_brain/neuroscience/",
    "Researchers found that mutations commonly linked to blood cancers may also cause Alzheimer's disease by making microglia (the brain's immune cells) abnormally inflammatory. The discovery creates an unexpected link between the aging immune system and neurodegeneration — and raises the possibility that blood cancer monitoring could also flag Alzheimer's risk early.",
    "An unexpected bridge between oncology and neuroscience at the immune cell level. If validated, this has dual implications: earlier Alzheimer's detection via blood work, and potential immunological intervention strategies for neurodegeneration. The intersection is genuinely novel.",
    "ScienceDaily / Neuroscience",
    "https://www.sciencedaily.com/news/mind_brain/neuroscience/"
)

OI_CONTENT = section_block("Other Interests", "\n".join([oi_s1, oi_s2, oi_s3, oi_s4]))

# REMAINDER
rem_s1 = story(
    "Google Research: Retired Smartphones as a Low-Carbon Distributed Computing Platform",
    "https://research.google/blog/a-low-carbon-computing-platform-from-your-retired-phones/",
    "Google Research described a project repurposing retired smartphones as a distributed, low-carbon computing substrate — using the existing embodied energy in devices that would otherwise go to e-waste. The concept was trending on Hacker News on June 14 with 256+ points.",
    "India generates significant mobile phone waste and has a large base of retired smartphones. A viable platform for distributed computing on old devices would create sustainability and economic value simultaneously — the kind of frugal innovation model that translates well to Indian conditions. Early stage, but worth watching.",
    "Google Research",
    "https://research.google/blog/a-low-carbon-computing-platform-from-your-retired-phones/"
)

REM_CONTENT = section_block("Remainder", rem_s1)

# ── FRONT PAGE ────────────────────────────────────────────────────────────────
fp_s1 = story(
    "BREAKING: US Export Controls Shut Down Claude Fable 5 Globally; Anthropic Flies to Washington",
    "https://www.anthropic.com/news/fable-mythos-access",
    "On June 12, the US government issued an export-control directive requiring Anthropic to immediately suspend Claude Fable 5 (Mythos) access for all foreign nationals — and Anthropic complied by taking both models offline for all users globally. Senior Anthropic staff met with White House officials on June 14. The WSJ reports Amazon CEO Andy Jassy's conversations with US officials triggered the crackdown — raising sharp conflict-of-interest questions about Amazon's $4B stake in Anthropic.",
    "The first time the US government has used export controls to block access to a frontier AI model. For India's developers, enterprises, and Anthropic's Indian partners (TCS just announced a Claude deployment deal for regulated industries), this is an operational and geopolitical risk event. The deeper precedent: AI models may now be treated like semiconductors — controlled dual-use technology.",
    "Anthropic / WSJ",
    "https://www.anthropic.com/news/fable-mythos-access"
)

fp_s2 = story(
    "Iran Closes Strait of Hormuz Completely; Pakistan PM Says Peace Deal 'Within 24 Hours'",
    "https://www.aljazeera.com/news/2026/6/10/us-bombs-iran-after-trump-threat-tehran-closes-hormuz-strait-to-all-ships",
    "Iran announced a complete closure of the Strait of Hormuz to all commercial shipping following new US airstrikes, threatening to fire on any vessel attempting to pass. Oil touched $126/barrel — nearly double pre-war levels. Pakistani PM Shehbaz Sharif, the chief mediator, said a deal is closer 'than ever' and could come 'in the next 24 hours.'",
    "The world's single most critical oil chokepoint is closed. India imports ~85% of its oil; at $126 Brent, fuel subsidies widen, fertiliser costs rise, and the RBI's 5.1% FY27 inflation forecast — already a revision upward — looks optimistic. Track the Pakistan mediation outcome today.",
    "Al Jazeera",
    "https://www.aljazeera.com/news/2026/6/10/us-bombs-iran-after-trump-threat-tehran-closes-hormuz-strait-to-all-ships",
    developing=True
)

fp_s3 = story(
    "Gujarat Launches Industrial Policy 2026 Today: Semiconductors, Drones, Nuclear Equipment as Priority Sectors",
    "https://aninews.in/news/national/general-news/gujarat-govt-to-unveil-new-industrial-policy-2026-on-june-1520260613145722/",
    "Gujarat CM Bhupendra Patel unveiled the state's Industrial Policy 2026 today at Gandhinagar, introducing an 'ultra mega' investment category and expanding priority sectors from 9 to 16, including semiconductor supply chains, nuclear power equipment, drones, and robotics. The policy targets improved ease of doing business and MSME support.",
    "Gujarat sets the industrial policy pace for India. The explicit inclusion of semiconductors and drones signals sub-national policy outpacing national frameworks on deeptech industrialisation. This is a concrete signal for foreign investors assessing India's industrial credibility in the chip and defence supply-chain diversification moment.",
    "ANI",
    "https://aninews.in/news/national/general-news/gujarat-govt-to-unveil-new-industrial-policy-2026-on-june-1520260613145722/"
)

fp_s4 = story(
    "IEA: Clean Energy Investment Hits 2:1 Over Fossil Fuels for the First Time in History",
    "https://www.iea.org/reports/world-energy-investment-2026",
    "Global energy investment reaches $3.4 trillion in 2026; clean energy commands $2.2 trillion versus $1.2 trillion for fossil fuels. Renewables now account for 70% of global power generation spending. The report notes Middle East conflict is disrupting markets but not deflecting the clean energy investment trajectory.",
    "A structural milestone, not a cyclical blip. For India — with its $500 billion clean energy target by 2030 — this confirms the capital flow direction and validates the pace of solar deployment as a credible grid-scale strategy.",
    "IEA",
    "https://www.iea.org/reports/world-energy-investment-2026"
)

fp_s5 = story(
    "OpenAI Acquires Gitpod to Run Coding Agents Overnight; ChatGPT Hits 1 Billion Monthly Users",
    "https://www.cnbc.com/2026/06/11/open-ai-ona-acquisition-codex.html",
    "OpenAI bought Ona HQ (Gitpod) to give Codex persistent cloud sandboxes — enabling coding agents that run for hours or days unattended. More than 5 million developers now use Codex weekly (400% up from early 2026). ChatGPT simultaneously crossed 1 billion monthly active users, the fastest product in history to reach that milestone.",
    "Persistent coding agents change software delivery fundamentally — from copilot to delegatee. For India's IT services sector, the disruption question has moved from 'if' to 'when and how much.' One billion ChatGPT users is also a distribution moat that any API-first AI product must reckon with.",
    "CNBC",
    "https://www.cnbc.com/2026/06/11/open-ai-ona-acquisition-codex.html"
)

fp_s6 = story(
    "El Ni&ntilde;o Officially Underway; 2026 on Track for Second-Warmest Year — Fast Development Raises Monsoon Risk",
    "https://www.carbonbrief.org/state-of-the-climate-strong-el-nino-puts-2026-on-track-for-second-warmest-year/",
    "The WMO confirmed El Niño is underway in 2026, developing unusually fast — potentially rivalling the strongest events on record (1997–98, 2015–16). Carbon Brief puts 2026 on track for the second-warmest year globally. For South Asia, the primary risk is drought: a below-normal Indian monsoon that would compound the oil-driven food price inflation already running at a 16-month high.",
    "El Niño is already in the RBI's risk models and explicit in its upward revision of FY27 inflation to 5.1%. A fast-developing event — combined with $126 Brent oil — changes India's macro story from cautious optimism to structural stress if both risks materialise simultaneously. Watch monsoon forecasts closely through July.",
    "Carbon Brief",
    "https://www.carbonbrief.org/state-of-the-climate-strong-el-nino-puts-2026-on-track-for-second-warmest-year/"
)

fp_s7 = story(
    "India Stagflation Watch: Inflation at 3.93% for Now — But El Ni&ntilde;o + $126 Oil Test RBI's 5.1% FY27 Call",
    "https://www.bloomberg.com/news/articles/2026-06-12/india-inflation-accelerates-to-3-93-stays-below-rbi-target",
    "May CPI came in at 3.93%, below the RBI's 4% target. But the RBI's own revised FY27 forecast — 5.1% inflation, 6.6% GDP — already prices in a cautious scenario. Food CPI is at 4.8% (16-month high). $126 Brent oil adds fertiliser and transport cost pressure. An El Niño-driven monsoon shortfall would push food CPI further. All three risks are live simultaneously.",
    "The May number is noise; the RBI's forecast revision is signal. India faces a real stagflation scenario — not yet a certainty but a live probability requiring monitoring. For anyone tracking India macro, the June–September monsoon window is the most consequential variable of the second half of FY27.",
    "Bloomberg",
    "https://www.bloomberg.com/news/articles/2026-06-12/india-inflation-accelerates-to-3-93-stays-below-rbi-target",
    developing=True
)

fp_s8 = story(
    "Modi at G7 &Eacute;vian and VivaTech Paris: India to Present MANAV AI Governance Framework",
    "https://vivatech.com/media/press-releases/breaking-news-vivatech-announces-the-participation-of-narendra-modi-prime-minister-of-india-during-the-10-th-anniversary-edition",
    "The G7 Leaders' Summit opens today in &Eacute;vian, France (June 15–17), with Modi attending alongside G7 leaders. On June 18 he moves to VivaTech 2026 in Paris — where India holds the inaugural 'AI Country Partner' designation — to deliver a keynote presenting the MANAV framework: India's AI governance model rooted in Global South priorities and democratic values.",
    "India presenting its own AI governance framework at a major European summit is strategic positioning with real implications: it challenges the assumption that AI rules will be written in Washington or Beijing. MANAV is worth reading carefully — it will influence how India negotiates AI governance in multilateral settings going forward.",
    "VivaTech",
    "https://vivatech.com/media/press-releases/breaking-news-vivatech-announces-the-participation-of-narendra-modi-prime-minister-of-india-during-the-10-th-anniversary-edition",
    developing=True
)

FP_CONTENT = section_block("Front Page", "\n".join([
    fp_s1, fp_s2, fp_s3, fp_s4, fp_s5, fp_s6, fp_s7, fp_s8
]))


# ── BUILD FILES ───────────────────────────────────────────────────────────────
BASE = "/home/user/daily-cactus/site"
os.makedirs(f"{BASE}/sections", exist_ok=True)
os.makedirs(f"{BASE}/archive/{DATE_SLUG}/sections", exist_ok=True)

pages = {
    # (path, active_slug, content, nav_prefix)
    f"{BASE}/index.html": ("index", FP_CONTENT, ""),
    f"{BASE}/sections/ai.html": ("ai", AI_CONTENT, "../"),
    f"{BASE}/sections/deep-tech.html": ("deep-tech", DT_CONTENT, "../"),
    f"{BASE}/sections/climate-energy.html": ("climate-energy", CE_CONTENT, "../"),
    f"{BASE}/sections/health-tech.html": ("health-tech", HT_CONTENT, "../"),
    f"{BASE}/sections/agritech.html": ("agritech", AG_CONTENT, "../"),
    f"{BASE}/sections/indian-startups.html": ("indian-startups", IS_CONTENT, "../"),
    f"{BASE}/sections/global-economics.html": ("global-economics", GE_CONTENT, "../"),
    f"{BASE}/sections/india.html": ("india", IN_CONTENT, "../"),
    f"{BASE}/sections/world.html": ("world", WO_CONTENT, "../"),
    f"{BASE}/sections/other-interests.html": ("other-interests", OI_CONTENT, "../"),
    f"{BASE}/sections/remainder.html": ("remainder", REM_CONTENT, "../"),
}

# Compute section title from slug for <title>
slug_to_name = {s: n for n, s, _ in SECTIONS}

for path, (slug, content, prefix) in pages.items():
    section_part = f" &mdash; {slug_to_name.get(slug, '')}" if slug != "index" else ""
    html = page(section_part, slug, content, prefix)
    with open(path, "w") as f:
        f.write(html)
    print(f"Wrote {path}")

# Archive: index only, nav points to live sections via ../../sections/
archive_html = page("", "index", FP_CONTENT, "")
# Patch nav links for archive
archive_html = archive_html.replace('href="sections/', 'href="../../sections/')
archive_html = archive_html.replace('href="index.html"', 'href="../../index.html"')
with open(f"{BASE}/archive/{DATE_SLUG}/index.html", "w") as f:
    f.write(archive_html)
print(f"Wrote {BASE}/archive/{DATE_SLUG}/index.html")

print("Done!")
