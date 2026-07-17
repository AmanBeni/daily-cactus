#!/usr/bin/env python3
"""Fix 1 — resolve Google News RSS article redirects to the real publisher URL.

WHY THIS EXISTS
---------------
About half of every section's candidates come in via Google News RSS queries
(see sources.yaml). The `<link>` those feeds carry is NOT the publisher URL —
it's a `news.google.com/rss/articles/CBMi...` redirect page. That breaks two
things downstream:
  1. `enrich_shortlist.py` fetches this URL to extract article text — but
     trafilatura/readability extract Google's own interstitial page, not the
     article, so extraction silently fails for ~half the digest.
  2. The renderer's "Read the original" link sends the reader to a Google
     interstitial instead of the actual article.

HOW RESOLUTION WORKS
---------------------
Two strategies, cheapest first:
  1. Offline: some tokens are old-style base64 blobs that embed the real URL
     directly in the decoded bytes. Try that first — free, no network.
  2. Network: fetch the `news.google.com/rss/articles/...` page with a real
     browser User-Agent. Either:
       a) the response redirects straight to the publisher (rare but cheap —
          just check the final URL), or
       b) it serves Google News' Angular shell, which embeds a per-article
          `data-n-a-id` / `data-n-a-ts` / `data-n-a-sg` triple. POST those to
          Google's internal `batchexecute` endpoint (the same call the Google
          News web app itself makes) and parse the real URL out of the
          response body.

Cached within a run (module-level dict) since the same story can appear in
several sections' candidate pools before shortlisting. Never raises — any
failure at any stage returns the ORIGINAL url unchanged, so a resolution
failure can never break the pipeline; the story just keeps its Google News
link, exactly like before this fix.

Only call this on Google News links. Direct publisher links should never be
routed through here (nothing to resolve, and it would waste two HTTP round
trips for nothing).
"""
import base64
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request

PER_REQUEST_TIMEOUT = 10  # seconds, per HTTP call (two calls in the worst case)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = None

_BATCHEXECUTE_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"

_ATTR_RE = re.compile(
    r'data-n-a-id="([^"]+)"[^>]*data-n-a-ts="(\d+)"[^>]*data-n-a-sg="([^"]+)"')

_cache: dict[str, str] = {}


def _is_gnews_article(url: str) -> bool:
    return bool(url) and "news.google.com/rss/articles/" in url


def _http_get(url: str, headers=None, data=None) -> tuple[str, str]:
    """Returns (final_url, body_text). Raises on network/HTTP errors."""
    req = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=PER_REQUEST_TIMEOUT, context=_SSL_CTX) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        return resp.geturl(), body


def _decode_offline(article_path: str) -> str | None:
    """Best-effort fully-offline decode: some (older-style) Google News article
    ids are base64 blobs with the real article URL embedded as plain bytes
    inside a protobuf wrapper. Try to base64-decode and regex out an http(s)
    URL; return None (never raise) if that doesn't pan out — the network path
    handles the current/common token format."""
    try:
        # Article ids are urlsafe-base64-ish but sometimes need padding fixed.
        padded = article_path + "=" * (-len(article_path) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception:
        return None
    m = re.search(rb"https?://[^\x00-\x1f\"\\]+", raw)
    if not m:
        return None
    url = m.group(0).decode("utf-8", errors="ignore")
    # Strip trailing garbage bytes that sometimes tag along after the real URL.
    url = re.split(r"[\x00-\x1f]", url)[0]
    if "news.google.com" in url or "." not in url:
        return None
    return url


def _decode_via_batchexecute(article_id: str, page_body: str) -> str | None:
    m = _ATTR_RE.search(page_body)
    if not m or m.group(1) != article_id:
        # Fall back to searching without requiring an exact id match — some
        # pages carry only one candidate block anyway.
        m = _ATTR_RE.search(page_body)
    if not m:
        return None
    _id, ts, sig = m.group(1), m.group(2), m.group(3)
    inner = json.dumps([
        "garturlreq",
        [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1,
          None, None, None, None, None, 0, 1],
         "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
        _id, int(ts), sig,
    ])
    freq = json.dumps([[["Fbv4je", inner, None, "generic"]]])
    payload = ("f.req=" + urllib.parse.quote(freq)).encode()
    _, resp_body = _http_get(
        _BATCHEXECUTE_URL, data=payload,
        headers={"User-Agent": UA,
                  "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    # The response is Google's ")]}'"-prefixed anti-hijacking JSON: a JSON
    # array of arrays, where the "wrb.fr"/"Fbv4je" row's 3rd element is ITSELF
    # a JSON-encoded string (["garturlres", "<real url>", ...]). Parse both
    # layers properly rather than regexing the escaped quotes.
    text = resp_body.lstrip()
    if text.startswith(")]}'"):
        text = text[4:]
    text = text.lstrip("\n")
    try:
        outer = json.loads(text)
    except json.JSONDecodeError:
        return None
    for row in outer:
        if isinstance(row, list) and len(row) >= 3 and row[0] == "wrb.fr" and row[1] == "Fbv4je":
            try:
                inner_data = json.loads(row[2])
            except (json.JSONDecodeError, TypeError):
                return None
            if isinstance(inner_data, list) and len(inner_data) >= 2 and inner_data[0] == "garturlres":
                return inner_data[1] or None
    return None


def resolve(url: str) -> str:
    """Turn a `news.google.com/rss/articles/...` URL into the real publisher
    URL. Returns the ORIGINAL url unchanged if it isn't a Google News article
    link, or if resolution fails for any reason — this function never raises."""
    if not url:
        return url
    if not _is_gnews_article(url):
        return url
    if url in _cache:
        return _cache[url]

    resolved = url
    try:
        parsed = urllib.parse.urlparse(url)
        # path looks like /rss/articles/<article_id>
        article_id = parsed.path.rsplit("/", 1)[-1]

        # 1. Cheap offline attempt (older-style tokens embed the URL directly).
        offline = _decode_offline(article_id)
        if offline:
            resolved = offline
        else:
            # 2. Network: fetch the interstitial; a same-domain redirect never
            #    happens in practice for this URL shape, but check anyway.
            final_url, body = _http_get(url)
            if "news.google.com" not in urllib.parse.urlparse(final_url).netloc:
                resolved = final_url
            else:
                decoded = _decode_via_batchexecute(article_id, body)
                if decoded:
                    resolved = decoded
    except Exception:
        resolved = url  # never crash the pipeline on a resolution failure

    _cache[url] = resolved
    return resolved


if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else None
    if not test_url:
        print("usage: resolve_gnews.py <news.google.com/rss/articles/... url>")
        raise SystemExit(1)
    print(resolve(test_url))
