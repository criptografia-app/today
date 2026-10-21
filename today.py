#!/usr/bin/env python3
"""Cryptography Today: render the daily banner and the editions page.

  python3 today.py banner editions/<date>/spec.json   -> banner.html + banner.png next to it
  python3 today.py index                              -> index.html (all editions)

spec.json:
  {"date": "2026-10-14",
   "headline": "one line under the title",
   "items": [{"tag": "PQC", "title": "short title"}, ...],    # 4-6 items, no links
   "stats": "15 new ePrint papers · 7 posts · 3 forums",      # optional
   "window": "96h"}                                            # optional, default "24h"

The banner is 1200x627 (LinkedIn link-post size), rendered at 2x by headless
Chrome. Left: Alan Turing as coloured ASCII. Right: title, date and items.
Links never go on the banner; they live in post.txt.
"""
import html
import json
import re
import os
import subprocess
import sys
from datetime import date as Date
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 1200, 627
RAMP = " .`:-=+*cox#%@"
TAG_COLORS = {"ATTACK": "#ff3b5c", "CVE": "#ff3b5c", "PQC": "#b967ff", "BTC": "#ffb000",
              "ZK": "#39ff9f", "MPC": "#00eaff", "PAPER": "#7ff6ff", "STD": "#4fd6ff",
              "AI": "#ff4fd8", "SUPPLY": "#ff6a3d", "ETH": "#8fa3ff"}


def turing_ascii(cols=132, rows=84):
    """Return rows of (char, colour) for the engraving, cropped to its alpha box."""
    im = Image.open(ROOT / "assets" / "turing.png").convert("RGBA")
    im = im.crop(im.split()[-1].getbbox())
    im = im.resize((cols, rows), Image.LANCZOS)
    # stretch contrast inside the portrait only: the engraving's hatching
    # averages to flat mid-grey at this size, which reads as a silhouette
    alpha = im.split()[-1]
    gray = ImageOps.autocontrast(im.convert("L"), cutoff=2, mask=alpha.point(lambda a: 255 if a > 128 else 0))
    gray = ImageOps.equalize(gray, mask=alpha.point(lambda a: 255 if a > 128 else 0))
    im = Image.merge("RGBA", (gray, gray, gray, alpha))
    px = im.load()
    out = []
    for y in range(rows):
        row = []
        for x in range(cols):
            r, g, b, a = px[x, y]
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255 * (a / 255)
            ch = RAMP[min(len(RAMP) - 1, int(lum * len(RAMP)))]
            # phosphor palette: dark teal -> cyan -> near-white highlights
            lvl = min(5, int(lum * 6))
            col = ["#0b2a33", "#12505e", "#1b8094", "#2fb8cc", "#8fe9f5", "#e8fbff"][lvl]
            row.append((ch, col))
        out.append(row)
    return out


def ascii_html(grid):
    lines = []
    for row in grid:
        spans, cur, buf = [], None, []
        for ch, col in row:
            if col != cur and buf:
                spans.append(f'<span style="color:{cur}">{html.escape("".join(buf))}</span>')
                buf = []
            cur = col
            buf.append(ch)
        if buf:
            spans.append(f'<span style="color:{cur}">{html.escape("".join(buf))}</span>')
        lines.append("".join(spans))
    return "\n".join(lines)


def banner(spec_path):
    spec_path = Path(spec_path).resolve()
    spec = json.loads(spec_path.read_text())
    d = Date.fromisoformat(spec["date"])
    out_dir = spec_path.parent
    font = os.path.relpath(ROOT / "assets" / "VT323-Regular.ttf", out_dir)
    items = "".join(
        f'<li><span class="tag" style="--c:{TAG_COLORS.get(i["tag"].upper(), "#9a90d8")}">{html.escape(i["tag"].upper())}</span>'
        f'<span class="t">{html.escape(i["title"])}</span></li>' for i in spec["items"][:6])
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Cryptography Today {d}</title>
<style>
@font-face {{ font-family: VT323; src: url("{font}"); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; background: #05040d; overflow: hidden; }}
.card {{ position: relative; width: {W}px; height: {H}px;
  background: radial-gradient(ellipse at 22% 55%, #0d2230 0%, #05040d 62%); color: #e6e2ff; font-family: VT323, monospace; font-variant-ligatures: none; }}
pre.ascii {{ position: absolute; left: 18px; top: 22px; font: 7px/6.9px Menlo, 'DejaVu Sans Mono', monospace;
  letter-spacing: -0.35px; text-shadow: 0 0 4px rgba(47,184,204,.35); }}
.right {{ position: absolute; left: 560px; top: 40px; right: 44px; }}
.prompt {{ font-size: 22px; color: #39ff9f; }} .prompt b {{ color: #4fd6ff; font-weight: normal; }}
h1 {{ font-size: 76px; line-height: 64px; margin-top: 10px; font-weight: normal; letter-spacing: 1px;
  background: linear-gradient(180deg, #ffffff 0%, #c3cbdc 45%, #5d6782 52%, #e9eef8 60%, #9aa3b9 100%);
  -webkit-background-clip: text; color: transparent; filter: drop-shadow(0 0 10px rgba(159,220,255,.35)); }}
h1 span {{ background: linear-gradient(180deg, #ff2e88, #00eaff); -webkit-background-clip: text; }}
.date {{ font-size: 26px; color: #ffb000; margin-top: 8px; letter-spacing: 2px; text-shadow: 0 0 8px rgba(255,176,0,.5); }}
.headline {{ font-size: 25px; color: #c9b8ff; margin: 16px 0 12px; line-height: 25px; }}
ul {{ list-style: none; border-top: 1px solid #2b2650; }}
li {{ display: flex; gap: 12px; align-items: baseline; padding: 7px 0; border-bottom: 1px solid #1a1638; font-size: 25px; line-height: 24px; }}
.tag {{ flex: none; width: 76px; text-align: center; font-size: 19px; color: var(--c); border: 1px solid var(--c);
  border-radius: 3px; padding: 0 4px; text-shadow: 0 0 6px var(--c); }}
.t {{ color: #e6e2ff; }}
.foot {{ position: absolute; left: 560px; right: 44px; bottom: 26px; display: flex; justify-content: space-between;
  font-size: 22px; color: #8f86c9; }}
.foot .links {{ color: #39ff9f; }}
.scan {{ position: absolute; inset: 0; background: repeating-linear-gradient(0deg, rgba(0,0,0,.18) 0 1px, transparent 1px 3px); pointer-events: none; }}
.frame {{ position: absolute; inset: 10px; border: 1px solid #00eaff55; border-radius: 6px; box-shadow: 0 0 18px #00eaff22 inset; }}
</style></head><body><div class="card">
<pre class="ascii">{ascii_html(turing_ascii())}</pre>
<div class="right">
  <div class="prompt">metaver5o@criptografia:~$ <b>./today --last {html.escape(spec.get("window", "24h"))}</b></div>
  <h1>CRYPTOGRAPHY<br><span>TODAY</span></h1>
  <div class="date">{d:%a %d %b %Y}{(" · " + html.escape(spec["stats"])) if spec.get("stats") else ""}</div>
  <div class="headline">{html.escape(spec.get("headline", ""))}</div>
  <ul>{items}</ul>
</div>
<div class="foot"><span>metaver5o.eth · criptografia.app</span><span class="links">links in the post ↓</span></div>
<div class="frame"></div><div class="scan"></div>
</div></body></html>"""
    (out_dir / "banner.html").write_text(page)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=2",
                    f"--window-size={W},{H}", "--virtual-time-budget=2000",
                    f"--screenshot={out_dir / 'banner.png'}", (out_dir / "banner.html").as_uri()],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(out_dir / "banner.png")


SECTION_TAGS = [("ai\\b", "AI"), ("secur", "ATTACK"), ("attack", "ATTACK"), ("cve", "CVE"), ("post-quantum", "PQC"),
                ("bitcoin", "BTC"), ("zero", "ZK"), ("zk", "ZK"), ("mpc", "MPC"), ("threshold", "MPC"),
                ("paper", "PAPER"), ("eprint", "PAPER"), ("standard", "STD"),
                ("supply", "SUPPLY"), ("ethereum", "ETH")]


def linkify(post):
    """Show ' — <url>' as a short [LINK] in its section's banner tag colour.
    The Copy button still copies the full URLs."""
    out, colour = [], "#4fd6ff"
    for line in post.splitlines():
        low = line.lower()
        if line.strip() and not line.lstrip().startswith(("•", "#")) and "http" not in low:
            for key, tag in SECTION_TAGS:
                if re.search(r"\b" + key, low):
                    colour = TAG_COLORS[tag]
                    break
        out.append(re.sub(r'\s+—\s+(https?://\S+)|(https?://\S+)',
                          lambda m: f' <a href="{m.group(1) or m.group(2)}" target="_blank" rel="noopener" style="--c:{colour}">[LINK]</a>',
                          html.escape(line, quote=False)))
    return "\n".join(out)


def index():
    eds = sorted((p for p in (ROOT / "editions").iterdir() if (p / "banner.png").exists()), reverse=True)
    cards = []
    for p in eds:
        post = (p / "post.txt").read_text() if (p / "post.txt").exists() else ""
        cards.append(f"""<article><h2>{p.name}</h2>
<a href="editions/{p.name}/banner.png"><img src="editions/{p.name}/banner.png" alt="Cryptography Today banner, {p.name}"></a>
<div class="row"><button onclick="copy(this)">Copy post</button><a href="editions/{p.name}/banner.png" download>Download banner</a></div>
<pre class="post">{linkify(post)}</pre><pre class="raw" hidden>{html.escape(post)}</pre></article>""")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cryptography Today</title><style>
@font-face {{ font-family: VT323; src: url("assets/VT323-Regular.ttf"); }}
body {{ margin: 0; background: #05040d; color: #e6e2ff; font: 15px/1.5 ui-monospace, Menlo, monospace; font-variant-ligatures: none; }}
main {{ max-width: 980px; margin: 0 auto; padding: 28px 16px 60px; }}
h1 {{ font: 54px VT323, monospace; margin: 0; color: #e9eef8; text-shadow: 0 0 12px #9fdcff66; }}
.sub {{ color: #8f86c9; margin-bottom: 28px; }}
article {{ border: 1px solid #2b2650; border-radius: 8px; padding: 16px; margin-bottom: 28px; background: #0a0716; }}
h2 {{ font: 30px VT323, monospace; color: #ffb000; margin: 0 0 10px; }}
img {{ width: 100%; border-radius: 6px; display: block; }}
.row {{ display: flex; gap: 14px; align-items: center; margin: 12px 0; }}
button {{ font: inherit; background: #39ff9f; color: #05040d; border: 0; border-radius: 4px; padding: 6px 12px; cursor: pointer; }}
a {{ color: #4fd6ff; }}
pre.post a {{ color: var(--c); text-decoration: none; text-shadow: 0 0 6px var(--c); }}
pre.post a:hover {{ text-decoration: underline; }}
pre.post {{ white-space: pre-wrap; background: #05040d; border: 1px solid #1a1638; padding: 12px; border-radius: 6px; margin: 0; }}
</style></head><body><main>
<h1>CRYPTOGRAPHY TODAY</h1><div class="sub">Daily roundup · {len(eds)} edition(s)</div>
{"".join(cards) or "<p>No editions yet.</p>"}
</main><script>
function copy(b) {{ const t = b.closest('article').querySelector('pre.raw').textContent;
  navigator.clipboard.writeText(t).then(() => {{ b.textContent = 'Copied'; setTimeout(() => b.textContent = 'Copy post', 1500); }}); }}
</script></body></html>"""
    (ROOT / "index.html").write_text(page)
    print(ROOT / "index.html")


if __name__ == "__main__":
    {"banner": lambda: banner(sys.argv[2]), "index": index}[sys.argv[1]]()
