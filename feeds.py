#!/usr/bin/env python3
"""Pull cryptography feeds and print items from the last N hours (default 24).

Stdlib only. Usage: python3 feeds.py [hours]
Output: one block per source, items as "- [date] title | link | summary".
A source that fails prints an ERROR line instead of stopping the run.
"""
import email.utils
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 24
SINCE = datetime.now(timezone.utc) - timedelta(hours=HOURS)
UA = {"User-Agent": "Mozilla/5.0 (cryptography-digest skill)"}

FEEDS = [  # (label, url, kind)
    ("IACR ePrint (new papers)", "https://eprint.iacr.org/rss/rss.xml", "rss"),
    ("Cryptography Dispatches (Filippo Valsorda)", "https://words.filippo.io/rss/", "rss"),
    ("Matthew Green", "https://blog.cryptographyengineering.com/feed/", "rss"),
    ("Bitcoin Optech", "https://bitcoinops.org/feed.xml", "rss"),
    ("zkMesh", "https://zkmesh.substack.com/feed", "rss"),
    ("Trail of Bits", "https://blog.trailofbits.com/feed/", "rss"),
    ("Schneier on Security", "https://www.schneier.com/feed/atom/", "rss"),
    ("Cloudflare (cryptography)", "https://blog.cloudflare.com/tag/cryptography/rss/", "rss"),
    ("Delving Bitcoin", "https://delvingbitcoin.org/latest.json", "discourse"),
    ("ethresear.ch", "https://ethresear.ch/latest.json", "discourse"),
]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return r.read()


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def clean(s, n=220):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] + ("…" if len(s) > n else "")


def rss(label, url):
    root = ET.fromstring(get(url))
    out = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        f = {c.tag.split("}")[-1]: c for c in it}
        title = (f.get("title").text if f.get("title") is not None else "") or ""
        link = f.get("link")
        link = (link.get("href") or link.text or "") if link is not None else ""
        date = None
        for k in ("pubDate", "published", "updated", "date"):
            if f.get(k) is not None and f[k].text:
                date = parse_date(f[k].text)
                if date:
                    break
        summ = ""
        for k in ("description", "summary", "content"):
            if f.get(k) is not None and f[k].text:
                summ = f[k].text
                break
        if date and date >= SINCE:
            link = re.sub(r"/feed/atom/?$", "", link.strip())  # Schneier's atom links
            out.append((date, clean(title, 200), link, clean(summ)))
    return out


def discourse(label, url):
    data = json.loads(get(url))
    base = url.rsplit("/", 1)[0]
    out = []
    for t in data.get("topic_list", {}).get("topics", []):
        d = parse_date(t.get("last_posted_at") or t.get("created_at"))
        if d and d >= SINCE:
            new = parse_date(t.get("created_at")) >= SINCE
            tag = "NEW" if new else f"active, {t.get('posts_count', '?')} posts"
            out.append((d, f"{t['title']} ({tag})", f"{base}/t/{t['slug']}/{t['id']}", ""))
    return out


def run(feed):
    label, url, kind = feed
    try:
        items = (rss if kind == "rss" else discourse)(label, url)
        return label, sorted(items, reverse=True), None
    except Exception as e:  # noqa: BLE001 - report and continue
        return label, [], f"{type(e).__name__}: {e}"


with ThreadPoolExecutor(8) as ex:
    results = list(ex.map(run, FEEDS))

print(f"# Cryptography feeds since {SINCE:%Y-%m-%d %H:%M} UTC ({HOURS:g}h)\n")
for label, items, err in results:
    print(f"## {label} — {'ERROR ' + err if err else str(len(items)) + ' item(s)'}")
    for d, title, link, summ in items:
        print(f"- [{d:%m-%d %H:%M}] {title} | {link}" + (f" | {summ}" if summ else ""))
    print()
