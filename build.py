#!/usr/bin/env python3
"""Build the Newspin static site.

Reads data/site.json and data/stories/*.json and writes a complete static site
to dist/. No dependencies beyond Python 3 (Pillow is optional, for share images).

    python3 build.py            # build into dist/
"""
import datetime as dt
import html
import json
import re
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DIST = ROOT / "dist"
STATIC = ROOT / "static"

e = lambda s: html.escape(str(s), quote=True)

PHASES = {
    "cut": ("Rate cut", "#1D4ED8", "#E8EEFD", "#1D4ED8"),
    "hold": ("Hold", "#3F444E", "#EEEEEA", "#9CA3AF"),
    "hike": ("Rate hike", "#9A3412", "#FCEBDD", "#C2410C"),
    "data": ("Data", "#0F5B4E", "#E3F2EE", "#0F6B5C"),
    "forecast": ("Forecast", "#5B3A9A", "#F3EEFB", None),
    "policy": ("Policy", "#3F444E", "#EEEEEA", None),
    "market": ("Markets", "#0F5B4E", "#E3F2EE", None),
    "world": ("World", "#5B3A9A", "#F3EEFB", None),
    "trade": ("Trade", "#9A3412", "#FCEBDD", None),
    "law": ("Law", "#3F444E", "#EEEEEA", None),
    "tech": ("Tech", "#0B5A8A", "#E6F1FA", None),
    "ai": ("AI", "#7A2E8E", "#F6EAF8", None),
    "travel": ("Travel", "#0E7490", "#E0F4F8", None),
}
CAT_INK = {"Economy": "#1D4ED8", "Markets": "#0F5B4E", "World": "#5B3A9A", "Trade": "#9A3412", "Policy": "#3F444E", "Tech": "#0B5A8A", "AI": "#7A2E8E", "Travel": "#0E7490"}

ICON_PLAY = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 5 6 9H2v6h4l5 4V5z"></path><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>'
ICON_BELL = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>'
ICON_SHARE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>'
ICON_CHEV = '<svg class="chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"></polyline></svg>'
ICON_CHECK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"></polyline></svg>'
ICON_WARN = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9A3412" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
LOGO_SVG = '<svg width="30" height="30" viewBox="0 0 64 64" aria-hidden="true"><path d="M16 50V14L48 50V14" fill="none" stroke="currentColor" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"></path><circle cx="16" cy="50" r="5" fill="currentColor"></circle><circle cx="16" cy="14" r="5" fill="currentColor"></circle><circle cx="48" cy="50" r="5" fill="currentColor"></circle><circle cx="48" cy="14" r="8" fill="var(--pin,#4B9C78)" stroke="var(--surface,#fff)" stroke-width="3"></circle></svg>'
FAVICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="15" fill="#15171C"/><path d="M18 48V18L44 48V18" fill="none" stroke="#FFFFFF" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/><circle cx="18" cy="48" r="5.5" fill="#FFFFFF"/><circle cx="18" cy="18" r="5.5" fill="#FFFFFF"/><circle cx="44" cy="48" r="5.5" fill="#FFFFFF"/><circle cx="44" cy="18" r="9" fill="#6FC39C" stroke="#15171C" stroke-width="3"/></svg>'


def src_link(src):
    cls = ' class="primary"' if src.get("primary") else ""
    tag = " · primary" if src.get("primary") else ""
    return f'<a href="{e(src["url"])}" rel="noopener" target="_blank"{cls}>{e(src["name"])}{tag}</a>'


def cat_class(cat):
    return "cat-" + cat.split(" ")[0]


def d(s):
    return dt.date.fromisoformat(s)


def nice_date(s):
    x = d(s)
    return f"{x.day} {x.strftime('%b %Y')}"


# ---------- data ----------
def load():
    site = json.loads((DATA / "site.json").read_text())
    stories = {}
    for p in sorted((DATA / "stories").glob("*.json")):
        s = json.loads(p.read_text())
        s["events"].sort(key=lambda ev: ev["date"])
        for ev in s["events"]:
            ev.setdefault("added", ev["date"])
        stories[s["slug"]] = s
    order = [x for x in site["order"] if x in stories] + [x for x in stories if x not in site["order"]]
    return site, stories, order


# ---------- timeline track ----------
class Axis:
    def __init__(self, stories, today):
        first = min(d(ev["date"]) for s in stories.values() for ev in s["events"])
        self.start = dt.date(first.year, 1, 1)
        self.end = dt.date(today.year, 12, 31)
        self.today = today
        self.years = list(range(self.start.year, self.end.year + 1))

    def pos(self, date):
        x = d(date) if isinstance(date, str) else date
        span = (self.end - self.start).days
        return max(0.5, min(99.0, (x - self.start).days / span * 100))


class LocalAxis:
    """Zoomed axis for short stories, so a two-week story isn't a single blob."""
    def __init__(self, s, today):
        first = d(s["events"][0]["date"])
        ends = [d(s["events"][-1]["date"]), today] + [d(u["date"]) for u in s.get("upcoming", []) if d(u["date"]) >= today]
        self.start = first - dt.timedelta(days=3)
        self.end = max(ends) + dt.timedelta(days=4)
        self.today = today
        self.marks = []
        m = dt.date(self.start.year, self.start.month, 1)
        while m <= self.end:
            if m >= self.start:
                self.marks.append((m, m.strftime("%b")))
            m = dt.date(m.year + (m.month // 12), m.month % 12 + 1, 1)
        self.first_label = self.start.strftime("%-d %b")

    def pos(self, date):
        x = d(date) if isinstance(date, str) else date
        span = (self.end - self.start).days
        return max(0.5, min(99.0, (x - self.start).days / span * 100))


def short_date(x, today):
    return f"{x.day} {x.strftime('%b')}" if x.year == today.year else f"{x.day} {x.strftime('%b %Y')}"


def track_html(s, axis, dark=False, link_prefix=""):
    """Horizontal timeline: zoomed to the story's own dates, nearby events grouped with a count,
    past drawn solid, future dashed, labels for the start, the latest event, now and what's next."""
    today = axis.today
    evs = s["events"]
    ink = CAT_INK.get(s["category"], "#3F444E")
    first = d(evs[0]["date"])
    ups = sorted(d(u["date"]) for u in s.get("upcoming", []) if d(u["date"]) >= today)
    end = max([today] + ups + [d(ev["date"]) for ev in evs])
    start = first - dt.timedelta(days=max(2, int((end - first).days * 0.03)))
    span = max((end - start).days, 1)
    pos = lambda x: 3 + ((x - start).days / span) * 94
    latest = latest_event(s)
    now_p = pos(today)

    parts = [f'<div class="track" role="img" aria-label="{e(track_label(s))}">']
    parts.append(f'<div class="past" style="width:{now_p:.2f}%;background:{ink}"></div>')
    if ups:
        parts.append(f'<div class="future" style="left:{now_p:.2f}%;width:{pos(ups[-1]) - now_p:.2f}%;border-color:{ink}"></div>')
    parts.append(f'<div class="now" style="left:{now_p:.2f}%"></div>')

    # group events that would overlap
    GAP = 7  # % of the track width below which two markers would touch on a phone
    groups = []
    for i, ev in enumerate(evs):
        p = pos(d(ev["date"]))
        groups.append({"items": [(i, ev)], "p_first": p, "p_last": p})
    merged = True
    while merged:  # merge neighbours until every marker has room
        merged = False
        for k in range(len(groups) - 1):
            a, c = groups[k], groups[k + 1]
            if (c["p_first"] + c["p_last"]) / 2 - (a["p_first"] + a["p_last"]) / 2 < GAP:
                a["items"] += c["items"]; a["p_last"] = c["p_last"]; del groups[k + 1]; merged = True
                break
    for g in groups:
        items = g["items"]
        p = (g["p_first"] + g["p_last"]) / 2
        idx, ev = items[-1]
        has_latest = any(x is latest for _, x in items)
        if has_latest:
            idx, ev = next((i, x) for i, x in items if x is latest)
        ph = PHASES.get(ev["phase"], PHASES["policy"])
        color = ph[3] or ink
        tip = " · ".join(f'{x["dateLabel"]}: {x["title"]}' for _, x in items)
        href = f'{link_prefix}#e{idx + 1}'
        if len(items) > 1:
            size = 22 if has_latest else 20
            ring = f"box-shadow:0 0 0 3px var(--surface),0 0 0 6px {color}33;" if has_latest else "box-shadow:0 0 0 3px var(--surface);"
            parts.append(f'<a class="dot cl" href="{e(href)}" title="{e(tip)}" style="left:{p:.2f}%;width:{size}px;height:{size}px;background:{color};{ring}">{len(items)}</a>')
        elif ev["phase"] == "forecast":
            parts.append(f'<a class="dot" href="{e(href)}" title="{e(tip)}" style="left:{p:.2f}%;width:12px;height:12px;background:var(--surface);border:2px dashed #5B3A9A"></a>')
        elif has_latest:
            parts.append(f'<a class="dot" href="{e(href)}" title="{e(tip)}" style="left:{p:.2f}%;width:16px;height:16px;background:{color};box-shadow:0 0 0 3px var(--surface),0 0 0 7px {color}33"></a>')
        else:
            parts.append(f'<a class="dot" href="{e(href)}" title="{e(tip)}" style="left:{p:.2f}%;width:11px;height:11px;background:{color};box-shadow:0 0 0 2.5px var(--surface)"></a>')
    if ups:  # only the next scheduled event gets a dot; the dashed line shows anything later
        parts.append(f'<span class="dot" style="left:{pos(ups[0]):.2f}%;width:13px;height:13px;background:var(--surface);border:2px dashed {ink}"></span>')

    # labels: latest above its dot; start, now and next below
    lp = pos(d(latest["date"]))
    anchor = "right:0;left:auto;transform:none" if lp > 78 else ("left:0;transform:none" if lp < 22 else f"left:{lp:.2f}%")
    parts.append(f'<span class="tl-top" style="{anchor}">Latest · {e(short_date(d(latest["date"]), today))}</span>')
    parts.append(f'<span class="tl-bot" style="left:0;transform:none">{e(short_date(first, today) if (today - first).days < 300 else first.strftime("%b %Y"))}</span>')
    if ups:
        up_p = pos(ups[0])
        if up_p - now_p > 14:
            parts.append(f'<span class="tl-bot now-l" style="left:{now_p:.2f}%">Now</span>')
        nxt = ups[1] if ups[0] == today and len(ups) > 1 else ups[0]
        nxt_label = next((u["label"] for u in s.get("upcoming", []) if d(u["date"]) == nxt), short_date(nxt, today))
        parts.append(f'<span class="tl-bot next-l" style="right:0;left:auto;transform:none">Next · {e(nxt_label)}</span>')
    else:
        parts.append(f'<span class="tl-bot now-l" style="right:0;left:auto;transform:none">Now</span>')
    parts.append("</div>")
    return "".join(parts)


def latest_event(s):
    done = [ev for ev in s["events"] if ev["phase"] != "forecast"]
    return (done or s["events"])[-1]


def track_label(s):
    n = len(s["events"])
    first = s["events"][0]["dateLabel"]
    last = s["events"][-1]["dateLabel"]
    return f"Timeline of {n} events from {first} to {last}"


# ---------- layout ----------
def page(site, *, title, desc, path, body, story_slug=None, og_image="/og/home.png", jsonld=None, nav="home", noindex=False, og_alt="Newspin", published=None, modified=None):
    url = site["domain"].rstrip("/") + path
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    robots = '<meta name="robots" content="noindex">' if noindex else '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">'
    dom = site["domain"].rstrip("/")
    times = (f'<meta property="article:published_time" content="{published}T09:00:00+05:30">\n<meta property="article:modified_time" content="{modified}T09:00:00+05:30">') if published else ""
    cur = lambda k: ' aria-current="page"' if nav == k else ""
    return f"""<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
{robots}
<meta property="og:type" content="{'article' if story_slug else 'website'}">
<meta property="og:site_name" content="Newspin">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:locale" content="en_IN">
<meta property="og:image" content="{e(dom + og_image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(og_alt)}">
{times}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{e(dom + og_image)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-48.png" sizes="48x48" type="image/png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#F7F7F4">
<link rel="alternate" type="application/rss+xml" title="Newspin: latest updates" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@600;700;800&family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/styles.css">
<meta name="color-scheme" content="light">
<script>(function(){{try{{var t=localStorage.getItem('np_theme')||'light';document.documentElement.setAttribute('data-theme',t);var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute('content',t==='dark'?'#0B0D12':'#F7F7F4');}}catch(e){{}}}})();</script>
{ld}
</head>
<body class="tl-b"{f' data-story="{e(story_slug)}"' if story_slug else ''}>
<a class="sr-only" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap">
  <a class="logo" href="/">{LOGO_SVG}<span>Newspin</span></a>
  <nav class="nav" aria-label="Main">
    <a href="/"{cur('home')}>Timelines</a>
    <a href="/about/"{cur('about')}>How it works</a>
  </nav>
</div></header>
<main id="main">
{body}
</main>
<footer class="site-footer"><div class="wrap">
  <span>© {dt.date.today().year} Newspin · {e(site['tagline'])}</span>
  <nav aria-label="Footer"><a href="/about/">How it works</a><a href="/about/#corrections">Corrections</a><a href="/privacy/">Privacy</a><a href="/terms/">Terms &amp; disclaimer</a></nav>
  <p class="foot-note">Newspin summarises reporting from the sources linked on each timeline. It is general information, not financial, legal or medical advice.</p>
  <button type="button" class="theme-btn" id="theme-btn" aria-label="Switch to dark mode"><svg class="i-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg><svg class="i-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"></path></svg></button>
</div></footer>
<div class="toast" id="toast" role="status" aria-live="polite" hidden></div>
<script src="/app.js" defer></script>
</body>
</html>
"""


def follow_btn(slug, cls="btn btn-follow", on="Following", off="Follow", short=""):
    aria = f' aria-label="Follow {e(short)}"' if short else ""
    return f'<button type="button" class="{cls}" data-follow="{e(slug)}" data-on="{e(on)}" data-off="{e(off)}" aria-pressed="false"{aria}>{ICON_BELL}<span class="label">{e(off)}</span></button>'


# ---------- ranking (mirrors rank() in static/app.js) ----------
QUIET_DAYS = 60


def story_facts(s, today):
    added = sorted(ev["added"] for ev in s["events"])
    nxt = sorted(u["date"] for u in s.get("upcoming", []) if d(u["date"]) >= today)
    return {"latest": added[-1], "next": nxt[0] if nxt else "", "added": added, "imp": s.get("importance", 3)}


def rank(f, today):
    days = (today - d(f["latest"])).days
    fresh = max(0.0, 10 - days * 0.5)
    up = 0.0
    if f["next"]:
        until = (d(f["next"]) - today).days
        up = 6 - until * 0.5 if until <= 7 else (2 if until <= 21 else 0)
    recent = min(4, sum(1 for a in f["added"] if 0 <= (today - d(a)).days <= 14))
    score = fresh + up + f["imp"] * 2 + recent
    quiet = days > QUIET_DAYS and not (f["next"] and (d(f["next"]) - today).days <= 30)
    return score, quiet


# ---------- story mode data (used by "Catch me up") ----------
# Bright gradients for the home-page story bubbles (white letters stay readable on both stops)
BUBBLE_BG = {"Economy": ("#2563EB", "#60A5FA"), "Markets": ("#047857", "#10B981"), "World": ("#6D28D9", "#A78BFA"),
             "Trade": ("#C2410C", "#F97316"), "Policy": ("#BE185D", "#F472B6"), "Tech": ("#0369A1", "#0EA5E9"),
             "AI": ("#A21CAF", "#E879F9"), "Travel": ("#0E7490", "#22D3EE")}


def bubble_bg(cat):
    a, b = BUBBLE_BG.get(cat, ("#334155", "#64748B"))
    return f"linear-gradient(135deg,{a},{b})"


CAT_BG = {"Economy": "#1D3FB0", "Markets": "#0B5A4C", "World": "#4A2F82", "Trade": "#8A2E0E", "Policy": "#353A45", "Tech": "#0B5A8A", "AI": "#6A2380", "Travel": "#0B5E73"}


def sm_data(s):
    evs = []
    for i, ev in enumerate(s["events"]):
        evs.append({"i": i + 1, "date": ev["date"], "added": ev["added"], "label": ev["dateLabel"], "title": ev["title"],
                    "summary": ev["summary"], "status": ev["status"], "nums": ev.get("numbers", [])[:2],
                    "sources": len(ev["sources"]), "forecast": ev["phase"] == "forecast"})
    return {"slug": s["slug"], "short": s["short"], "url": f"/stories/{s['slug']}/", "bg": CAT_BG.get(s["category"], "#353A45"),
            "letter": s["short"][0].upper(), "latestAdded": max(ev["added"] for ev in s["events"]),
            "latestTitle": latest_event(s)["title"], "latestLabel": latest_event(s)["dateLabel"], "events": evs,
            "title": s["title"], "intro": [s["glance"]["what"], s["glance"]["why"], s["glance"]["next"]]}


# Home v3: roll-up stories repeat news that already sits in each company's timeline,
# so they stay out of "Moving now" and "Latest updates" (they still appear in the AI group).
ROLLUPS = {"ai-this-week", "ai-model-tracker"}
HOME_GROUPS = ["AI", "India economy", "World and US", "Travel and everyday"]


def home_group(s):
    cat, regions = s["category"], s.get("regions", ["India"])
    if cat == "AI":
        return "AI"
    if cat in ("Economy", "Markets", "Trade"):
        return "India economy"
    if cat == "World" or (cat == "Tech" and regions != ["India"]):
        return "World and US"
    return "Travel and everyday"


def day_label(x, today):
    gap = (today - x).days
    base = short_date(x, today)
    return f"Today · {base}" if gap == 0 else f"Yesterday · {base}" if gap == 1 else f"{x.strftime('%A')} · {base}"


# ---------- home ----------
def build_home(site, stories, order, axis):
    today = axis.today
    # calendar
    ups = []
    for slug in order:
        s = stories[slug]
        for u in s.get("upcoming", []):
            if d(u["date"]) >= today:
                ups.append((u["date"], u, s))
    ups.sort(key=lambda x: x[0])
    cal_items = []
    for date, u, s in ups[:6]:
        is_today = d(date) == today
        when = "Today" if is_today else u["label"]
        cal_items.append(f'<li><span class="when{" today" if is_today else ""}">{e(when)}</span><span class="what">{e(u["text"])} <a href="/stories/{e(s["slug"])}/">· {e(s["short"])}</a></span></li>')
    cal = "".join(cal_items) or '<li><span class="what">Nothing scheduled this month.</span></li>'

    def chain_row(items):
        out = []
        for i, it in enumerate(items):
            s = stories.get(it["slug"])
            if not s:
                continue
            if out:
                out.append('<span class="arr" aria-hidden="true">→</span>')
            out.append(f'<a class="{cat_class(s["category"])}" href="/stories/{e(s["slug"])}/">{e(it["label"])}</a>')
        return "".join(out)


    facts = {slug: story_facts(stories[slug], today) for slug in order}
    ranked = sorted(order, key=lambda x: -rank(facts[x], today)[0])
    live = [x for x in ranked if not rank(facts[x], today)[1]]
    quiet = [x for x in ranked if rank(facts[x], today)[1]]
    hero_slug = live[0] if live else ranked[0]
    grid_live = [x for x in live if x != hero_slug]
    # Moving now: up to four stories with news in the last 48 hours (roll-ups and the lead excluded),
    # topped up with the next most active stories if fewer than four moved.
    pool = [x for x in grid_live if x not in ROLLUPS]
    moved = [x for x in pool if (today - d(latest_event(stories[x]).get("added", latest_event(stories[x])["date"]))).days <= 2
             or (today - d(latest_event(stories[x])["date"])).days <= 2]
    moving = (moved + [x for x in pool if x not in moved])[:4]
    all_moved = all(x in moved for x in moving)
    cards, quiet_cards = [], []
    for slug in moving:
        s = stories[slug]
        f = facts[slug]
        latest = latest_event(s)
        feat = ""
        hot = " hot" if s["tone"] == "hot" else ""
        long_ = " long" if len(s["big"]) > 6 else ""
        stands = f'<p class="stands">{e(s["glance"]["what"])}</p>'
        links = ", ".join(f'<a href="/stories/{e(l)}/">{e(stories[l]["short"])}</a>' for l in s.get("links", []) if l in stories)
        linked = f'<div class="linked">Linked to {links}</div>' if links else ""
        target = cards
        if slug in live:
            status_pill = f'<span class="status tone-{e(s["tone"])}">{e(s["status"])}</span>'
        else:
            status_pill = f'<span class="status tone-quiet">No update in {(today - d(f["latest"])).days} days</span>'
        target.append(f"""
<article class="card {cat_class(s['category'])}{feat}{hot}" data-slug="{e(slug)}" data-cat="{e(s['category'])}" data-regions="{e(' '.join(s.get('regions', ['India'])))}" data-latest="{e(f['latest'])}" data-next="{e(f['next'])}" data-imp="{f['imp']}" data-added="{e(' '.join(f['added']))}">
  <div class="card-band">
    <div class="row"><span class="cat">{e(s['category'])}</span>{status_pill}</div>
    <div class="big-row"><span class="big{long_}">{e(s['big'])}</span><span class="delta">{e(s['delta'])}</span></div>
    <span class="big-label">{e(s['bigLabel'])}</span>
  </div>
  <div class="card-body">
    <h3><a href="/stories/{e(slug)}/">{e(s['title'])}</a></h3>
    {stands}
    {track_html(s, axis, link_prefix=f"/stories/{slug}/")}
    <div class="latest"><span class="d">{e(latest['dateLabel'])}</span><span class="t">{e(latest['title'])}</span></div>
    <div class="next"><strong>Next:</strong> {e(s['next'])}</div>
    {linked}
    <div class="card-actions">
      <a class="btn btn-dark btn-sm" href="/stories/{e(slug)}/">Open timeline</a>
      {follow_btn(slug, "btn btn-follow btn-sm", short=s['short'])}
    </div>
  </div>
</article>""")

    js_data = [sm_data(stories[x]) for x in [hero_slug] + grid_live + quiet]

    # greeting + story bubbles (top 8 by rank)
    bubble_slugs = ([hero_slug] + grid_live)[:8]
    bubbles = "".join(
        f'<li><button type="button" class="bubble" data-sm-open="{e(x)}" aria-label="Catch up on {e(stories[x]["short"])}">'
        f'<span class="ring"><span class="face" style="background:{bubble_bg(stories[x]["category"])}">{e(stories[x]["short"][0].upper())}</span></span>'
        f'<span class="bl">{e(stories[x]["short"])}</span></button></li>' for x in bubble_slugs)

    # lead story
    h = stories[hero_slug]
    hl = latest_event(h)
    kn = h.get("keyNumbers", [{}])[0]
    hero_title = h.get("heroTitle") or hl["title"]
    hero_dek = h.get("heroDek") or h["dek"]
    regions = " · ".join(h.get("regions", ["India"]))
    n_ev = len(h["events"])
    hero_html = f"""
  <section class="lead {cat_class(h['category'])}" aria-labelledby="lead-h">
    <div class="lead-main">
      <div class="lead-tags"><span class="live-tag">Top story · updated {e(short_date(d(h['updated']), today))}</span><span class="lead-cat">{e(h['category'])} · {e(regions)}</span></div>
      <h2 id="lead-h"><a href="/stories/{e(hero_slug)}/">{e(hero_title)}</a></h2>
      <p>{e(hero_dek)}</p>
      <div class="lead-actions">
        <button type="button" class="btn btn-pill-light" data-sm-open="{e(hero_slug)}">Catch me up · {n_ev} events</button>
        <button type="button" class="btn btn-pill-ghost listen-btn" data-listen-story="{e(hero_slug)}" hidden>{ICON_PLAY}Listen</button>
        <a class="btn btn-pill-ghost" href="/stories/{e(hero_slug)}/">Full timeline</a>
        {follow_btn(hero_slug, "btn btn-pill-ghost", short=h['short'])}
      </div>
    </div>
    <div class="lead-side">
      <div class="lead-stat"><span class="lbl2">{e(kn.get('label', h['bigLabel']))}</span><div><span class="lead-big">{e(h['big'])}</span>{'' if h['delta'].lower() in kn.get('label', h['bigLabel']).lower() else '<span class="lead-delta">'+e(h['delta'])+'</span>'}</div></div>
      {track_html(h, axis, link_prefix=f"/stories/{hero_slug}/")}
      <span class="lead-note">Next: {e(h['next'])}</span>
    </div>
  </section>"""

    # today / next strip
    # Strip shows only firm, dated items (labels like "17 Nov" or "2–4 Dec", not "Pending" or "2027"),
    # and each event once even if several stories list it.
    seen_up, firm = set(), []
    for date, u, s in ups:
        key = (date, re.sub(r"\W+", " ", u["text"].lower()).strip())
        if not re.match(r"\d", u["label"]) or key in seen_up:
            continue
        seen_up.add(key)
        firm.append((date, u, s))
    t_chips = [f'<a class="tchip" href="/stories/{e(s["slug"])}/">{e(s["short"])}: {e(u["text"])}</a>' for date, u, s in firm if d(date) == today]
    n_chips = [f'<a class="tchip" href="/stories/{e(s["slug"])}/"><b>{e(u["label"])}</b> · {e(u["text"])}</a>' for date, u, s in firm if d(date) > today][:5]
    strip = '<div class="strip" aria-label="Today and next">'
    if t_chips:
        strip += f'<span class="strip-l hot" data-ist-day="{site["today"]}">Today</span>' + "".join(t_chips)
    if n_chips:
        strip += '<span class="strip-l">Next</span>' + "".join(n_chips)
    strip += '</div>'

    top_html = f"""
  <section class="hello" aria-labelledby="hello-h">
    <h1 class="sr-only">Newspin: the big news stories in India, the US and the world, as timelines</h1>
    <div class="hello-text"><p class="hello-hd" id="hello-h">Hello</p><p id="hello-sub">{len(order)} live timelines across India, the US and the world</p><button type="button" class="briefing-btn listen-btn" id="briefing-btn" hidden>{ICON_PLAY}<span>Play my briefing</span></button></div>
    <ul class="bubbles" aria-label="Catch up story by story">{bubbles}</ul>
  </section>
  {hero_html}
  {strip}"""

    # Latest updates: one line per event across all stories, newest first, grouped by day
    evs = []
    for slug in order:
        if slug in ROLLUPS:
            continue
        s = stories[slug]
        for i, ev in enumerate(s["events"]):
            if ev["phase"] == "forecast" or d(ev["date"]) > today:
                continue
            evs.append((ev["date"], ev["added"], i, slug, ev))
    evs.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    lu, last_day = [], None
    for date, _, i, slug, ev in evs[:8]:
        s = stories[slug]
        if date != last_day:
            lu.append(f'<li class="lu-day" data-day="{e(date)}">{e(day_label(d(date), today))}</li>')
            last_day = date
        lu.append(f'<li class="lu-item {cat_class(s["category"])}"><a href="/stories/{e(slug)}/#e{i + 1}"><span class="lu-dot" aria-hidden="true"></span>'
                  f'<span><span class="lu-s">{e(s["short"])}</span><span class="lu-t">{e(ev["title"])}</span></span></a></li>')

    # All timelines: every active story as one line, in four groups
    groups = {g: [] for g in HOME_GROUPS}
    for slug in sorted(live, key=lambda x: (facts[x]["latest"], rank(facts[x], today)[0]), reverse=True):
        groups[home_group(stories[slug])].append(slug)
    ix_html = []
    for gi, g in enumerate(HOME_GROUPS):
        if not groups[g]:
            continue
        rows = []
        for slug in groups[g]:
            s = stories[slug]
            le = latest_event(s)
            fresh = (today - d(le["date"])).days <= 1
            rows.append(f'<li><a href="/stories/{e(slug)}/" data-ix="{e(slug)}"><span class="ix-dot{" fresh" if fresh else ""}" aria-hidden="true"></span>'
                        f'<span class="ix-main"><span class="ix-name">{e(s["short"])}{"<span class=sr-only> (updated in the last day)</span>" if fresh else ""}</span>'
                        f'<span class="ix-t">{e(le["title"])}</span></span><span class="ix-d">{e(short_date(d(le["date"]), today))}</span></a></li>')
        ix_html.append(f'<details class="ix-group" open><summary><span>{e(g)}</span> <span class="n">· {len(groups[g])}</span></summary><ul class="ix">{"".join(rows)}</ul></details>')
    quiet_links = ", ".join(f'<a href="/stories/{e(x)}/">{e(stories[x]["short"])}</a>' for x in quiet)
    quiet_line = (f'<p class="quiet-line"><b>Quiet for now · {len(quiet)}</b> {quiet_links}. '
                  f'<span class="note">No news in {QUIET_DAYS} days; they come back up when something happens.</span></p>') if quiet else ""
    moving_note = "News in the last 48 hours" if all_moved else "The most active stories right now"

    body = f"""
<div class="wrap">
{top_html}
  <div class="home-grid">
    <section class="moving-sec" aria-labelledby="moving-h">
      <div class="sec-head"><h2 id="moving-h">Moving now</h2><span class="note">{moving_note}</span></div>
      <div class="cards moving">{''.join(cards)}</div>
    </section>
    <section class="updates" aria-labelledby="lu-h">
      <div class="sec-head"><h2 id="lu-h">Latest updates</h2><span class="note">All stories</span></div>
      <ul class="lu">{''.join(lu)}</ul>
    </section>
  </div>

  <section class="index" id="all" aria-labelledby="all-h">
    <div class="sec-head"><h2 id="all-h">All timelines</h2><span class="note">{len(live)} active stories · <i class="ix-dot fresh" aria-hidden="true"></i> updated in the last day</span></div>
    <div class="index-grid">{''.join(ix_html)}</div>
  </section>

  <section class="foot-line" aria-label="More">
    {quiet_line}
    <details class="more"><summary>How these stories connect</summary>
      <div class="chain-row">{chain_row(site['chain'])}<span class="arr" aria-hidden="true" style="padding:0 6px">·</span>{chain_row(site['chain2']).replace('→', '↔')}</div>
    </details>
    <details class="more"><summary>How to read the timeline dots</summary>
      <div class="legend">
        <span><i class="kd" style="background:#3F444E"></i>Event</span>
        <span><i class="kd" style="width:18px;height:18px;background:#3F444E;color:#fff;font-size:10px;font-weight:700;font-style:normal;display:inline-flex;align-items:center;justify-content:center">3</i>Several events close together</span>
        <span><i class="kd" style="width:14px;height:14px;background:#3F444E;box-shadow:0 0 0 3px #fff,0 0 0 6px #3F444E33"></i>Latest</span>
        <span><i class="kd" style="width:12px;height:12px;border:2px dashed #3F444E;box-sizing:border-box"></i>Scheduled or forecast</span>
        <span>RBI: <i class="kd" style="background:#1D4ED8"></i>cut <i class="kd" style="background:#9CA3AF"></i>hold <i class="kd" style="background:#C2410C"></i>hike</span>
        <span>Tap a dot to jump to that event</span>
      </div>
    </details>
  </section>
  <p class="note" style="margin-top:28px">Every event links to the outlets that reported it and, where available, the original document. Forecasts are labelled as forecasts, and disagreements between sources are flagged. <a href="/about/">How Newspin works</a></p>
</div>
<script>window.NP_STORIES={json.dumps(js_data, ensure_ascii=False)};</script>
"""
    dom = site["domain"].rstrip("/")
    ranked = [hero_slug] + [x for x in order if x != hero_slug]
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "@id": f"{dom}/#site", "name": "Newspin", "url": dom + "/", "description": site["description"],
         "inLanguage": "en-IN", "publisher": {"@id": f"{dom}/#org"}},
        {"@type": "Organization", "@id": f"{dom}/#org", "name": "Newspin", "url": dom + "/",
         "logo": {"@type": "ImageObject", "url": f"{dom}/logo-512.png", "width": 512, "height": 512}},
        {"@type": "ItemList", "name": "Live news timelines", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": f"{dom}/stories/{x}/", "name": stories[x]["title"]}
            for i, x in enumerate(ranked)]}]}
    return page(site, title="Newspin: news timelines for India, the US and the world", desc=site["description"], path="/", body=body, jsonld=ld,
                og_alt="Newspin: the big stories, as timelines")


# ---------- story ----------
def build_story(site, stories, s, axis):
    slug = s["slug"]
    evs = s["events"]
    items = []
    for i, ev in enumerate(evs):
        ph = PHASES.get(ev["phase"], PHASES["policy"])
        dot_color = ph[3] or CAT_INK.get(s["category"], "#3F444E")
        if ev["phase"] == "forecast":
            dot = f"background:#fff;border:2px dashed #5B3A9A;"
        else:
            dot = f"background:{dot_color};"
        nums = "".join(f'<div><span class="k">{e(n["k"])}</span><span class="v">{e(n["v"])}</span></div>' for n in ev.get("numbers", []))
        nums_html = f'<div class="nums">{nums}</div>' if nums else ""
        differs = f'<div class="differs">{ICON_WARN}<span><strong>Sources differ:</strong> {e(ev["differs"])}</span></div>' if ev.get("differs") else ""
        srcs = "".join(src_link(src) for src in ev["sources"])
        link = ""
        if ev.get("link") and ev["link"] in stories:
            link = f'<a class="ev-link" href="/stories/{e(ev["link"])}/">Part of: {e(stories[ev["link"]]["title"])} →</a>'
        n = len(ev["sources"])
        x = d(ev["date"])
        items.append(f"""
<li class="ev{' key' if ev.get('key') else ''}" data-added="{e(ev['added'])}" id="e{i+1}">
  <div class="ev-date"><i class="dd" style="{dot}"></i><b>{e(ev['dateLabel'].rsplit(' ', 1)[0] if ev['dateLabel'][-4:].isdigit() and ' ' in ev['dateLabel'] else ev['dateLabel'])}</b><span>{x.year}</span></div>
  <div class="ev-rail" aria-hidden="true"><div class="l1"></div><div class="d" style="{dot}"></div><div class="l2"></div></div>
  <div class="ev-card"><article>
    <div class="ev-tags">
      <span class="ev-when">{e(ev['dateLabel'])}</span>
      <span class="pill" style="background:{ph[2]};color:{ph[1]}">{e(ph[0])}</span>
      <span class="badge-new" hidden>New since your last visit</span>
      <span class="ev-status">{ICON_CHECK}{e(ev['status'])}</span>
    </div>
    <h3>{e(ev['title'])}</h3>
    <p>{e(ev['summary'])}</p>
    <details>
      <summary><span style="display:inline-flex;align-items:center;gap:6px">{ICON_CHEV}<span class="long-l">Sources, documents and numbers</span><span class="short-l">Sources &amp; numbers</span></span><span class="cnt">{n} source{'s' if n != 1 else ''}</span></summary>
      <div class="depth">{nums_html}{differs}<div><span class="lbl">Reported by</span><div class="srcs">{srcs}</div></div>{link}</div>
    </details>
  </article></div>
</li>""")
    ups = ""
    for u in s.get("upcoming", []):
        if d(u["date"]) >= axis.today:
            ups += f"""
<div class="upcoming">
  <div class="ev-date"><i class="dd" style="border:2px dashed #1D4ED8;background:#fff"></i><b>{e(u['label'])}</b><span>Upcoming</span></div>
  <div class="ev-rail" aria-hidden="true"><div class="l1" style="height:16px"></div><div class="d" style="border:2px dashed #1D4ED8;background:#fff"></div></div>
  <div class="box"><div><span class="lbl" style="color:#1D4ED8;margin:0">Upcoming<span class="ev-when-up"> · {e(u['label'])}</span></span><span class="t">{e(u['text'])}</span></div>{follow_btn(slug, 'btn btn-follow btn-sm', on='You’ll be caught up', off='Remind me')}</div>
</div>"""

    keyn = ""
    for k in s.get("keyNumbers", []):
        word = " word" if len(k["value"]) > 9 else ""
        keyn += f'<div><span class="l">{e(k["label"])}</span><span class="v{word}">{e(k["value"])}</span><span class="n{" hot" if k.get("hot") else ""}">{e(k.get("note", ""))}</span></div>'

    linked = ""
    for l in s.get("links", []):
        if l in stories:
            t = stories[l]
            linked += f'<a href="/stories/{e(l)}/">{e(t["title"])}<span>{e(t["status"])} · {e(t["big"])} {e(t["delta"])}</span></a>'
    linked_html = f'<section class="panel side side-links" aria-labelledby="rel-h"><h2 id="rel-h">Linked timelines</h2>{linked}</section>' if linked else ""

    if site.get("signupAction"):
        signup = f"""<section class="signup side" aria-labelledby="su-h"><h2 id="su-h">Get updates by email</h2><p>One short email when this story moves. No spam.</p>
<form method="post" action="{e(site['signupAction'])}"><label class="sr-only" for="su-email">Email address</label><input id="su-email" name="email" type="email" required placeholder="you@example.com"><input type="hidden" name="story" value="{e(slug)}"><button class="btn" type="submit">Notify me</button></form></section>"""
    else:
        signup = f"""<section class="signup side" aria-labelledby="su-h"><h2 id="su-h">Follow this story</h2><p>Follow it and the Newspin home page will show you what changed since your last visit. Email alerts are coming soon.</p><div style="margin-top:14px">{follow_btn(slug, 'btn btn-light')}</div></section>"""

    n_src = sum(len(ev["sources"]) for ev in evs)
    body = f"""
<div class="wrap">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Timelines</a> / {e(s['category'])}</nav>
  <section class="story-hero" aria-labelledby="t">
    <div class="meta"><span class="pill pill-cat {cat_class(s['category'])}">{e(s['category'])}</span><span>{len(evs)} events since {e(evs[0]['dateLabel'])}</span><span aria-hidden="true">·</span><span>Last updated {e(nice_date(s['updated']))}</span></div>
    <h1 id="t">{e(s['title'])}</h1>
    <p class="dek">{e(s['dek'])}</p>
    <div class="hero-actions">{follow_btn(slug, 'btn btn-follow', on='Following this story', off='Follow story')}<button type="button" class="btn btn-light" data-sm-open="{e(slug)}">Catch me up</button><button type="button" class="btn btn-light listen-btn" data-listen-story="{e(slug)}" hidden>{ICON_PLAY}Listen</button><button type="button" class="btn btn-light" data-share>{ICON_SHARE}Share</button></div>
  </section>
  <div class="story-cols">
    <div class="story-main">
      <section class="panel glance" aria-labelledby="g-h">
        <div class="glance-head"><h2 class="eyebrow" id="g-h">In 30 seconds</h2><span>For everyone</span></div>
        <div class="glance-cols">
          <div><h3>What happened</h3><p>{e(s['glance']['what'])}</p></div>
          <div><h3>Why it matters</h3><p>{e(s['glance']['why'])}</p></div>
          <div><h3>What’s next</h3><p>{e(s['glance']['next'])}</p></div>
        </div>
        <div class="keynums">{keyn}</div>
      </section>
      <div class="story-track {cat_class(s['category'])}">{track_html(s, axis)}</div>
      <section class="newbar" id="newbar" aria-live="polite" hidden>
        <div><span class="k"></span><span class="h"></span></div>
        <button type="button" class="btn btn-light" aria-pressed="false">Show only what’s new</button>
      </section>
      <section aria-labelledby="tl-h" style="display:flex;flex-direction:column;gap:18px">
        <div class="tl-head">
          <div><h2 id="tl-h">Timeline</h2><span class="sub">Simple: key events · Detailed: sources, documents and numbers</span></div>
          <div class="seg" role="group" aria-label="Detail level"><button type="button" data-mode="simple" aria-pressed="true">Simple</button><button type="button" data-mode="detailed" aria-pressed="false">Detailed</button></div>
        </div>
        <div class="tl-wrap">{'<p class="tl-order">Newest first</p>' if s.get("order") == "desc" else ""}<ol class="events">{''.join(reversed(items) if s.get("order") == "desc" else items)}</ol>
        {ups}</div>
      </section>
      <p class="note">This timeline draws on {n_src} source links. Labels show whether each event is confirmed, official data, reported by a single outlet or a forecast. Spotted an error? <a href="/about/#corrections">Tell us</a>.</p>
    </div>
    <aside class="story-side">
      <section class="panel side" aria-labelledby="fy-h"><h2 id="fy-h">What this means for you</h2><p>{e(s['forYou'])}</p></section>
      {linked_html}
      {signup}
    </aside>
  </div>
</div>
"""
    body += f'<script>window.NP_STORIES={json.dumps([sm_data(s)], ensure_ascii=False)};</script>'
    dom = site["domain"].rstrip("/")
    published = min(ev["added"] for ev in s["events"])
    url = f"{dom}/stories/{slug}/"
    org = {"@type": "Organization", "@id": f"{dom}/#org", "name": "Newspin", "url": dom + "/",
           "logo": {"@type": "ImageObject", "url": f"{dom}/logo-512.png", "width": 512, "height": 512}}
    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "NewsArticle", "headline": s["title"][:110], "description": s["dek"], "url": url,
         "mainEntityOfPage": url, "inLanguage": "en-IN",
         "datePublished": f"{published}T09:00:00+05:30", "dateModified": f"{s['updated']}T09:00:00+05:30",
         "image": [f"{dom}/og/{slug}.png"], "articleSection": s["category"],
         "author": {"@id": f"{dom}/#org"}, "publisher": {"@id": f"{dom}/#org"}},
        org,
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Timelines", "item": dom + "/"},
            {"@type": "ListItem", "position": 2, "name": s["category"], "item": dom + "/"},
            {"@type": "ListItem", "position": 3, "name": s["short"], "item": url}]}]}
    return page(site, title=f"{s['seoTitle']} | Newspin", desc=s["dek"], path=f"/stories/{slug}/", body=body,
                story_slug=slug, og_image=f"/og/{slug}.png", jsonld=ld, nav="story",
                og_alt=f"{s['short']} timeline: {s['big']}", published=published, modified=s["updated"])


# ---------- simple pages ----------
def build_about(site):
    body = f"""<div class="wrap-narrow prose">
<h1>How Newspin works</h1>
<p>News is written for people who already know the background. Newspin is for everyone else: each big story becomes one timeline you can read in 30 seconds or study in depth.</p>
<h2>Three layers on every story</h2>
<p><strong>In 30 seconds:</strong> what happened, why it matters and what’s next. <strong>Timeline:</strong> the key events in order. <strong>Detailed:</strong> open any event for the numbers, the original documents and every outlet that reported it.</p>
<h2>How we source</h2>
<ul>
<li>Every event links to the reports it is based on. Where an official document exists (a regulator’s statement, a gazette notification, official statistics), we link it and mark it <em>primary</em>.</li>
<li>We prefer official sources, then established news outlets. Analyst and economist views are labelled <span class="pill" style="background:#F3EEFB;color:#5B3A9A">Forecast</span> and never presented as fact.</li>
<li>When an event rests on a single outlet, we say so.</li>
<li>When reliable sources disagree, we show a <strong>Sources differ</strong> note instead of quietly picking one.</li>
<li>We summarise in our own words and link to the original. We don’t republish articles.</li>
</ul>
<h2>How timelines are built</h2>
<p>AI tools help us gather reports and draft events. A person checks every event, its date and its sources before it is published.</p>
<h2 id="corrections">Corrections</h2>
<p>If something is wrong or missing, email <a href="mailto:{e(site.get('contactEmail', 'hello@newspinapp.com'))}">{e(site.get('contactEmail', 'hello@newspinapp.com'))}</a> with the story and the event. We fix errors quickly and note significant corrections on the timeline.</p>
<h2>Independence</h2>
<p>Newspin is independent and not affiliated with any political party or news outlet. Story selection is based on how big and long-running a story is, not on who it helps.</p>
</div>"""
    return page(site, title="How Newspin works | Newspin", desc="How Newspin builds sourced news timelines: three layers, sourcing rules, forecasts, and corrections.", path="/about/", body=body, nav="about")


def build_privacy(site):
    mail = e(site.get('contactEmail', 'hello@newspinapp.com'))
    body = f"""<div class="wrap-narrow prose">
<h1>Privacy</h1>
<p><em>Last updated 13 November 2026.</em></p>
<p>Newspin is built to work without knowing who you are. This page explains the little that is stored or shared when you use it.</p>
<h2>No accounts, no tracking</h2>
<p>You can read Newspin without signing up. We do not use advertising or tracking cookies, and we do not run analytics or share data with advertisers. If that ever changes, we will update this page first and say so on the site.</p>
<h2>What your browser stores on your device</h2>
<p>To remember your choices, Newspin saves a few small items in your browser’s local storage:</p>
<ul>
<li>stories you follow, and the date you last opened each story (so we can show what changed since your last visit);</li>
<li>your detail level, sort order and light or dark theme;</li>
<li>your preferred listening speed.</li>
</ul>
<p>These stay on your device and are not sent to us. Clearing your browser data removes them.</p>
<h2>Listen</h2>
<p>The Listen feature uses your device’s built-in text-to-speech. Newspin does not send the text anywhere. Some browsers offer online voices run by the browser maker; if you have chosen one of those, your browser may process the text on its maker’s servers under its own privacy policy.</p>
<h2>Services we rely on</h2>
<ul>
<li><strong>Hosting:</strong> the site is hosted on GitHub Pages. Like any web host, GitHub may log technical data such as your IP address for security and operations.</li>
<li><strong>Fonts:</strong> pages load fonts from Google Fonts, so your browser connects to Google’s servers to fetch them.</li>
<li><strong>Sharing:</strong> if you use Share, your device’s own share menu or clipboard handles it.</li>
<li><strong>Links:</strong> source links take you to other websites, which have their own privacy policies.</li>
</ul>
<h2>Email alerts</h2>
<p>Email alerts are not live yet. When they are, we will use your email address only to send updates on the stories you chose, and every email will have an unsubscribe link.</p>
<h2>Children</h2>
<p>Newspin is a general news site and does not knowingly collect information from children.</p>
<h2>Changes and contact</h2>
<p>If this policy changes, we will update the date at the top. Questions or requests: <a href="mailto:{mail}">{mail}</a>.</p>
</div>"""
    return page(site, title="Privacy | Newspin", desc="What Newspin stores, what it shares and why.", path="/privacy/", body=body, nav="privacy")


def build_terms(site):
    mail = e(site.get('contactEmail', 'hello@newspinapp.com'))
    body = f"""<div class="wrap-narrow prose">
<h1>Terms of use and disclaimer</h1>
<p><em>Last updated 13 November 2026.</em></p>
<h2>What Newspin is</h2>
<p>Newspin organises reporting on major ongoing news stories into timelines. Each event summarises, in our own words, what published sources have reported, and links to those sources so you can read them yourself.</p>
<h2>Not advice</h2>
<p>Everything on Newspin is general information. It is not financial, investment, legal, tax or medical advice, and it is not a recommendation to buy, sell or hold anything. Make important decisions using the original sources and, where appropriate, a qualified professional.</p>
<h2>Accuracy</h2>
<p>We work to keep timelines accurate and current: every event is sourced, reports are labelled by how firm they are (confirmed, reported, allegation, forecast), and disagreements between outlets are flagged. News changes quickly, though, and sources can be wrong or updated after we read them. Newspin is provided as it is, without guarantees of completeness or accuracy. Allegations described on Newspin are claims made by the people or outlets named, not findings of fact.</p>
<h2>How Newspin is made</h2>
<p>Newspin uses AI tools to help find news, draft summaries and update timelines, working to written editorial rules. Updates may be published automatically. Every event links to its sources so you can check it.</p>
<h2>Corrections and complaints</h2>
<p>If you spot an error, or believe something on Newspin is unfair or unlawful, email <a href="mailto:{mail}">{mail}</a> with the page link and what is wrong. We review every report and correct mistakes openly on the timeline.</p>
<h2>Using Newspin</h2>
<p>You are welcome to read, link to and share Newspin pages. Please do not copy timelines wholesale, republish them or scrape the site for commercial use without permission.</p>
<h2>Other people’s content and names</h2>
<p>Linked articles and documents belong to their publishers. Company and product names belong to their owners and are used only to identify them; Newspin is not affiliated with or endorsed by them.</p>
<h2>Changes</h2>
<p>We may update these terms; the date at the top shows the latest version. Continuing to use Newspin means you accept the current terms.</p>
</div>"""
    return page(site, title="Terms and disclaimer | Newspin", desc="How to use Newspin, and what it is and is not.", path="/terms/", body=body, nav="terms")


def build_404(site):
    body = """<div class="wrap-narrow prose"><h1>That page isn’t here</h1><p>The story may have moved. <a href="/">See all live timelines</a>.</p></div>"""
    return page(site, title="Not found | Newspin", desc="Page not found.", path="/404.html", body=body, noindex=True)


# ---------- share images ----------
def build_og(site, stories, order, axis):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed: skipping share images")
        return
    def font(names, size):
        for n in names:
            for base in ["/usr/share/fonts/opentype/inter", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "C:/Windows/Fonts"]:
                p = os.path.join(base, n)
                if os.path.exists(p):
                    return ImageFont.truetype(p, size)
        return ImageFont.load_default()
    bold = lambda sz: font(["Inter-Bold.otf", "DejaVuSans-Bold.ttf", "Arial Bold.ttf"], sz)
    semi = lambda sz: font(["Inter-SemiBold.otf", "DejaVuSans-Bold.ttf"], sz)
    serif = lambda sz: font(["DejaVuSerif-Bold.ttf", "Georgia Bold.ttf"], sz)
    reg = lambda sz: font(["Inter-Regular.otf", "DejaVuSans.ttf"], sz)
    out = DIST / "og"
    out.mkdir(parents=True, exist_ok=True)

    def wrap(draw, text, f, width):
        words, lines, cur = text.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=f) <= width:
                cur = t
            else:
                lines.append(cur); cur = w
        lines.append(cur)
        return lines

    def card(path, kicker, big, title, s=None):
        im = Image.new("RGB", (1200, 630), "#15171C")
        dr = ImageDraw.Draw(im)
        # N-timeline mark, 44px tall, top-left
        sx, sy, k = 56, 50, 44 / 64
        pt = lambda x, y: (sx + x * k, sy + y * k)
        dr.line([pt(16, 50), pt(16, 14), pt(48, 50), pt(48, 14)], fill="#FFFFFF", width=5, joint="curve")
        for (cx, cy, r, col) in [(16, 50, 5, "#FFFFFF"), (16, 14, 5, "#FFFFFF"), (48, 50, 5, "#FFFFFF"), (48, 14, 9, "#6FC39C")]:
            x, y = pt(cx, cy); rr = r * k
            dr.ellipse((x - rr, y - rr, x + rr, y + rr), fill=col)
        dr.text((116, 50), "Newspin", font=serif(36), fill="#FFFFFF")
        dr.text((60, 130), kicker.upper(), font=semi(24), fill="#B9BEC8")
        y = 170
        if big:
            dr.text((56, y), big, font=bold(132), fill="#FFFFFF")
            y += 160
        for line in wrap(dr, title, serif(46 if big else 60), 1080)[:3]:
            dr.text((60, y), line, font=serif(46 if big else 60), fill="#FFFFFF")
            y += 58 if big else 74
        if s:
            x0, x1, ty = 60, 1140, 560
            dr.line((x0, ty, x1, ty), fill="#3A3F4A", width=3)
            for ev in s["events"]:
                px = x0 + (x1 - x0) * axis.pos(ev["date"]) / 100
                dr.ellipse((px - 8, ty - 8, px + 8, ty + 8), fill="#FFFFFF" if ev is not s["events"][-1] else "#6FC39C")
            dr.text((x0, ty + 16), str(axis.years[0]), font=reg(20), fill="#9CA3AF")
            dr.text((x1 - 50, ty + 16), "Now", font=semi(20), fill="#FFFFFF")
        im.save(path, optimize=True)

    card(out / "home.png", f"{len(order)} live timelines", None, "The biggest stories in India and the world, as timelines you can read in 30 seconds.")
    for slug in order:
        s = stories[slug]
        card(out / f"{slug}.png", s["category"] + " · " + s["status"], s["big"], s["title"], s)


# ---------- main ----------
def main():
    site, stories, order = load()
    ist_today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()  # the site's home time zone
    today = dt.date.fromisoformat(os.environ.get("NEWSPIN_TODAY") or ist_today.isoformat())
    axis = Axis(stories, today)
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for f in STATIC.iterdir():
        shutil.copy(f, DIST / f.name)
    (DIST / "favicon.svg").write_text(FAVICON)
    (DIST / "index.html").write_text(build_home(site, stories, order, axis))
    for slug in order:
        p = DIST / "stories" / slug
        p.mkdir(parents=True)
        (p / "index.html").write_text(build_story(site, stories, stories[slug], axis))
    for name, fn in [("about", build_about), ("privacy", build_privacy), ("terms", build_terms)]:
        (DIST / name).mkdir()
        (DIST / name / "index.html").write_text(fn(site))
    (DIST / "404.html").write_text(build_404(site))
    dom = site["domain"].rstrip("/")
    newest = max(stories[x]["updated"] for x in order)
    urls = [("/", newest)] + [(f"/stories/{s}/", stories[s]["updated"]) for s in order] + [("/about/", site["today"]), ("/privacy/", site["today"]), ("/terms/", site["today"])]
    sm = "".join(f"<url><loc>{dom}{u}</loc><lastmod>{m}</lastmod></url>" for u, m in urls)
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {dom}/sitemap.xml\n")
    (DIST / "CNAME").write_text("newspinapp.com\n")
    (DIST / "feed.xml").write_text(build_feed(site, stories, order))
    build_og(site, stories, order, axis)
    print(f"Built {len(order)} stories into {DIST}")


def build_feed(site, stories, order, limit=40):
    """RSS 2.0 feed of the newest timeline entries, for feed readers and news aggregators."""
    from email.utils import format_datetime
    dom = site["domain"].rstrip("/")
    items = []
    for slug in order:
        s = stories[slug]
        for i, ev in enumerate(s["events"]):
            if ev["phase"] == "forecast":
                continue
            items.append((ev["added"], i, s, ev))
    items.sort(key=lambda t: (t[0], t[3]["date"]), reverse=True)
    def rfc(d):
        return format_datetime(dt.datetime.fromisoformat(d + "T09:00:00+05:30"))
    out = []
    for added, i, s, ev in items[:limit]:
        link = f"{dom}/stories/{s['slug']}/#e{i + 1}"
        out.append(f"<item><title>{e(s['short'])}: {e(ev['title'])}</title><link>{link}</link>"
                   f"<guid isPermaLink=\"true\">{link}</guid><pubDate>{rfc(added)}</pubDate>"
                   f"<category>{e(s['category'])}</category><description>{e(ev['dateLabel'] + ' · ' + ev['summary'])}</description></item>")
    newest = items[0][0] if items else site["today"]
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
            f"<title>Newspin: latest timeline updates</title><link>{dom}/</link><description>{e(site['description'])}</description>"
            f"<language>en-in</language><lastBuildDate>{rfc(newest)}</lastBuildDate>"
            f'<atom:link href="{dom}/feed.xml" rel="self" type="application/rss+xml"/>' + "".join(out) + "</channel></rss>\n")


if __name__ == "__main__":
    main()
