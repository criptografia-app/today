# Cryptography Today

Daily cryptography roundup: an ASCII-Turing banner (1200x627, LinkedIn size) with
the day's highlights, plus a post whose text carries all the links.

- `feeds.py [hours]` — pull ePrint, crypto blogs, Optech, zkMesh, Delving Bitcoin,
  ethresear.ch; prints items in the window (stdlib only).
- `today.py banner editions/<date>/spec.json` — render `banner.html` + `banner.png`.
- `today.py index` — rebuild `index.html` (all editions, copy-post buttons).
- `editions/<date>/` — `spec.json`, `post.txt`, `briefing.md`, `banner.png`.
- `assets/` — `turing.png`, VT323 font (SIL Open Font License).

Generated daily by the `/criptografia` Claude Code skill. Needs Python 3 + Pillow
and Google Chrome (headless) for the PNG.
