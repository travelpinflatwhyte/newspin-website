#!/usr/bin/env python3
"""Tell IndexNow search engines (Bing, Yandex, Seznam, Naver and others) which pages just changed.

Run by the deploy workflow after the site is published. Usage:
    python3 indexnow.py [changed files ...]
Changed story files (data/stories/<slug>.json) become story URLs; the home page and sitemap are always sent.
With no story files given, stories whose `updated` is today (IST) are sent instead.
Never fails the build: errors are printed and the script exits 0.
"""
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

from build import DATA, INDEXNOW_KEY, IST

site = json.loads((DATA / "site.json").read_text())
dom = site["domain"].rstrip("/")
host = dom.split("://", 1)[1]
order = set(site["order"])

slugs = {Path(a).stem for a in sys.argv[1:] if a.startswith("data/stories/") and a.endswith(".json")}
if not slugs:
    today = dt.datetime.now(IST).date().isoformat()
    for p in (DATA / "stories").glob("*.json"):
        if json.loads(p.read_text()).get("updated") == today:
            slugs.add(p.stem)
slugs &= order  # only stories that are actually published

urls = [f"{dom}/"] + [f"{dom}/stories/{s}/" for s in sorted(slugs)]
body = json.dumps({"host": host, "key": INDEXNOW_KEY, "keyLocation": f"{dom}/{INDEXNOW_KEY}.txt",
                   "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow: HTTP {r.status} for {len(urls)} URLs")
except Exception as exc:  # 202 is success; anything else is logged, not fatal
    print(f"IndexNow: {exc} ({len(urls)} URLs)")
for u in urls:
    print(" ", u)
