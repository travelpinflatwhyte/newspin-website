#!/usr/bin/env python3
"""Build the Newspin static site.

Reads data/site.json and data/stories/*.json and writes a complete static site
to dist/. No dependencies beyond Python 3 (Pillow is optional, for share images).

    python3 build.py            # build into dist/
"""
import datetime as dt
import html
import json
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
}
CAT_INK = {"Economy": "#1D4ED8", "Markets": "#0F5B4E", "World": "#5B3A9A", "Trade": "#9A3412", "Policy": "#3F444E", "Tech": "#0B5A8A"}

ICON_BELL = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>'
ICON_SHARE = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line></svg>'
ICON_CHEV = '<svg class="chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"></polyline></svg>'
ICON_CHECK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="20 6 9 17 4 12"></polyline></svg>'
ICON_WARN = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9A3412" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>'
LOGO_SVG = '<svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true"><circle cx="14" cy="14" r="12" fill="none" stroke="#15171C" stroke-width="2.5"></circle><circle cx="14" cy="14" r="4" fill="#1D4ED8"></circle><line x1="14" y1="2" x2="14" y2="7" stroke="#15171C" stroke-width="2.5"></line></svg>'
FAVICON = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 28 28"><rect width="28" height="28" rx="7" fill="#F7F7F4"/><circle cx="14" cy="14" r="10" fill="none" stroke="#15171C" stroke-width="2.5"/><circle cx="14" cy="14" r="3.6" fill="#1D4ED8"/><line x1="14" y1="4" x2="14" y2="8" stroke="#15171C" stroke-width="2.5"/></svg>'


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


def track_html(s, axis, dark=False):
    if (axis.today - d(s["events"][0]["date"])).days < 120:
        axis = LocalAxis(s, axis.today)
    parts = [f'<div class="track{" track-dark" if dark else ""}" role="img" aria-label="{e(track_label(s))}">', '<div class="axis"></div>']
    if isinstance(axis, LocalAxis):
        parts.append(f'<span class="yr" style="left:0">{axis.first_label}</span>')
        for m, label in axis.marks:
            p = axis.pos(m)
            if 8 < p < 85:
                parts.append(f'<div class="tick" style="left:{p:.2f}%"></div><span class="yr" style="left:calc({p:.2f}% + 4px)">{label}</span>')
    else:
        for i, y in enumerate(axis.years):
            p = axis.pos(dt.date(y, 1, 1))
            if i > 0:
                parts.append(f'<div class="tick" style="left:{p:.2f}%"></div>')
            left = "0" if i == 0 else f"calc({p:.2f}% + 4px)"
            parts.append(f'<span class="yr" style="left:{left}">{y}</span>')
    np_ = axis.pos(axis.today)
    now_l = '<span class="now-l">Now</span>' if np_ > 90 else f'<span class="now-l" style="right:auto;left:{np_:.2f}%;transform:translateX(-50%)">Now</span>'
    parts.append(f'<div class="now" style="left:{np_:.2f}%"></div>{now_l}')
    ink = CAT_INK.get(s["category"], "#3F444E")
    ring = "#15171C" if dark else "#FFFFFF"
    real = [ev for ev in s["events"]]
    latest = latest_event(s)["date"]
    for ev in real:
        p = axis.pos(ev["date"])
        ph = PHASES.get(ev["phase"], PHASES["policy"])
        color = ph[3] or ink
        if ev["phase"] == "forecast":
            st = f"width:12px;height:12px;top:8px;left:calc({p:.2f}% - 6px);border:2px dashed #5B3A9A;background:{ring};"
        elif ev["date"] == latest:
            st = f"width:16px;height:16px;top:6px;left:calc({p:.2f}% - 8px);background:{color};box-shadow:0 0 0 3px {ring},0 0 0 5px {color};"
        else:
            st = f"width:11px;height:11px;top:8.5px;left:calc({p:.2f}% - 5.5px);background:{color};border:2px solid {ring};"
        parts.append(f'<span class="dot" style="{st}"></span>')
    for up in s.get("upcoming", []):
        if d(up["date"]) >= axis.today:
            p = axis.pos(up["date"])
            parts.append(f'<span class="dot" style="width:14px;height:14px;top:7px;left:calc({p:.2f}% - 7px);border:2px dashed {ink};background:{ring};"></span>')
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
def page(site, *, title, desc, path, body, story_slug=None, og_image="/og/home.png", jsonld=None, nav="home", noindex=False):
    url = site["domain"].rstrip("/") + path
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    robots = '<meta name="robots" content="noindex">' if noindex else ""
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
<meta property="og:image" content="{e(site['domain'].rstrip('/') + og_image)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{e(site['domain'].rstrip('/') + og_image)}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500;6..72,600;6..72,700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/styles.css">
{ld}
</head>
<body{f' data-story="{e(story_slug)}"' if story_slug else ''}>
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
  <nav aria-label="Footer"><a href="/about/">How it works</a><a href="/about/#corrections">Corrections</a><a href="/privacy/">Privacy</a></nav>
</div></footer>
<div class="toast" id="toast" role="status" aria-live="polite" hidden></div>
<script src="/app.js" defer></script>
</body>
</html>
"""


def follow_btn(slug, cls="btn btn-follow", on="Following", off="Follow", short=""):
    aria = f' aria-label="Follow {e(short)}"' if short else ""
    return f'<button type="button" class="{cls}" data-follow="{e(slug)}" data-on="{e(on)}" data-off="{e(off)}" aria-pressed="false"{aria}>{ICON_BELL}<span class="label">{e(off)}</span></button>'


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

    chips = "".join(f'<button type="button" class="chip" data-filter="{e(c)}" aria-pressed="{"true" if c == "All" else "false"}">{e(c)}</button>' for c in site["categories"])
    region_btns = "".join(f'<button type="button" data-region="{e(r)}" aria-pressed="{"true" if r == "All" else "false"}">{e(r if r != "All" else "Everywhere")}</button>' for r in site.get("regions", ["All"]))

    cards = []
    for slug in order:
        s = stories[slug]
        latest = latest_event(s)
        feat = " featured" if s.get("featured") else ""
        hot = " hot" if s["tone"] == "hot" else ""
        long_ = " long" if len(s["big"]) > 6 else ""
        stands = f'<p class="stands">{e(s["glance"]["what"])}</p>' if s.get("featured") else ""
        links = ", ".join(f'<a href="/stories/{e(l)}/">{e(stories[l]["short"])}</a>' for l in s.get("links", []) if l in stories)
        linked = f'<div class="linked">Linked to {links}</div>' if links else ""
        cards.append(f"""
<article class="card {cat_class(s['category'])}{feat}{hot}" data-cat="{e(s['category'])}" data-regions="{e(' '.join(s.get('regions', ['India'])))}">
  <div class="card-band">
    <div class="row"><span class="cat">{e(s['category'])}</span><span class="status tone-{e(s['tone'])}">{e(s['status'])}</span></div>
    <div class="big-row"><span class="big{long_}">{e(s['big'])}</span><span class="delta">{e(s['delta'])}</span></div>
    <span class="big-label">{e(s['bigLabel'])}</span>
  </div>
  <div class="card-body">
    <h3><a href="/stories/{e(slug)}/">{e(s['title'])}</a></h3>
    {stands}
    {track_html(s, axis)}
    <div class="latest"><span class="d">{e(latest['dateLabel'])}</span><span class="t">{e(latest['title'])}</span></div>
    <div class="next"><strong>Next:</strong> {e(s['next'])}</div>
    {linked}
    <div class="card-actions">
      <a class="btn btn-dark btn-sm" href="/stories/{e(slug)}/">Open timeline</a>
      {follow_btn(slug, "btn btn-follow btn-sm", short=s['short'])}
    </div>
  </div>
</article>""")

    js_data = [{"slug": s["slug"], "short": s["short"], "url": f"/stories/{s['slug']}/",
                "latestAdded": max(ev["added"] for ev in s["events"]),
                "latestTitle": latest_event(s)["title"], "latestLabel": latest_event(s)["dateLabel"]} for s in (stories[x] for x in order)]

    body = f"""
<div class="wrap">
  <div class="home-top">
    <section class="catchup" id="catchup-intro" aria-labelledby="intro-h">
      <span class="kicker">{len(order)} live timelines · India, World and US · updated {e(nice_date(site['today']))}</span>
      <h1 id="intro-h">Every big story, from the beginning.</h1>
      <p>Newspin turns the biggest ongoing stories in India and around the world into clear timelines: what happened, when, and what comes next. Every event links to its sources.</p>
      <p>Follow a few stories and this space becomes your catch-up: what changed since you last looked.</p>
      <div class="hero-actions"><a class="btn btn-light" href="#live">Browse timelines</a><a class="btn btn-ghost" href="/about/">How it works</a></div>
    </section>
    <section class="catchup" id="catchup" aria-live="polite" hidden>
      <span class="kicker">Your stories</span>
      <h1>Your stories</h1>
      <ul></ul>
      <div class="hero-actions"><a class="btn btn-light" data-all href="#live">Catch me up</a><a class="btn btn-ghost" href="#live">All timelines</a></div>
    </section>
    <section class="cal" aria-labelledby="cal-h">
      <h2 class="eyebrow" id="cal-h">Coming up</h2>
      <ol>{cal}</ol>
    </section>
  </div>

  <section class="chain" aria-labelledby="chain-h">
    <div class="chain-head"><h2 id="chain-h">How these stories connect</h2><span class="note">Cause and effect across timelines</span></div>
    <div class="chain-row">{chain_row(site['chain'])}<span class="arr" aria-hidden="true" style="padding:0 6px">·</span>{chain_row(site['chain2']).replace('→', '↔')}</div>
  </section>

  <section id="live" aria-labelledby="live-h">
    <div class="grid-head"><h2 id="live-h">Live timelines</h2><div class="seg" role="group" aria-label="Filter by region">{region_btns}</div></div>
    <div class="chips" role="group" aria-label="Filter by topic" style="margin:-4px 0 18px">{chips}</div>
    <p class="note" id="nomatch" hidden>No timelines match these filters yet.</p>
    <div class="cards">{''.join(cards)}</div>
    <div class="legend"><b>Timeline key</b>
      <span><i class="kd" style="background:#3F444E"></i>Event</span>
      <span><i class="kd" style="width:14px;height:14px;background:#3F444E;box-shadow:0 0 0 3px #fff,0 0 0 5px #3F444E"></i>Latest</span>
      <span><i class="kd" style="width:12px;height:12px;border:2px dashed #3F444E;box-sizing:border-box"></i>Scheduled or forecast</span>
      <span>RBI: <i class="kd" style="background:#1D4ED8"></i>cut <i class="kd" style="background:#9CA3AF"></i>hold <i class="kd" style="background:#C2410C"></i>hike</span>
    </div>
  </section>
  <p class="note" style="margin-top:28px">Every event links to the outlets that reported it and, where available, the original document. Forecasts are labelled as forecasts, and disagreements between sources are flagged. <a href="/about/">How Newspin works</a></p>
</div>
<script>window.NP_STORIES={json.dumps(js_data, ensure_ascii=False)};</script>
"""
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": "Newspin", "url": site["domain"], "description": site["description"]}
    return page(site, title="Newspin · The big stories, as timelines", desc=site["description"], path="/", body=body, jsonld=ld)


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
  <div class="ev-date"><b>{e(ev['dateLabel'].rsplit(' ', 1)[0] if ev['dateLabel'][-4:].isdigit() and ' ' in ev['dateLabel'] else ev['dateLabel'])}</b><span>{x.year}</span></div>
  <div class="ev-rail" aria-hidden="true"><div class="l1"></div><div class="d" style="{dot}"></div><div class="l2"></div></div>
  <div class="ev-card"><article>
    <div class="ev-tags">
      <span class="pill" style="background:{ph[2]};color:{ph[1]}">{e(ph[0])}</span>
      <span class="badge-new" hidden>New since your last visit</span>
      <span class="ev-status">{ICON_CHECK}{e(ev['status'])}</span>
    </div>
    <h3>{e(ev['title'])}</h3>
    <p>{e(ev['summary'])}</p>
    <details>
      <summary><span style="display:inline-flex;align-items:center;gap:6px">{ICON_CHEV}Sources, documents and numbers</span><span class="cnt">{n} source{'s' if n != 1 else ''}</span></summary>
      <div class="depth">{nums_html}{differs}<div><span class="lbl">Reported by</span><div class="srcs">{srcs}</div></div>{link}</div>
    </details>
  </article></div>
</li>""")
    ups = ""
    for u in s.get("upcoming", []):
        if d(u["date"]) >= axis.today:
            ups += f"""
<div class="upcoming">
  <div class="ev-date"><b>{e(u['label'])}</b><span>Upcoming</span></div>
  <div class="ev-rail" aria-hidden="true"><div class="l1" style="height:16px"></div><div class="d" style="border:2px dashed #1D4ED8;background:#fff"></div></div>
  <div class="box"><div><span class="lbl" style="color:#1D4ED8;margin:0">Upcoming</span><span class="t">{e(u['text'])}</span></div>{follow_btn(slug, 'btn btn-follow btn-sm', on='You’ll be caught up', off='Remind me')}</div>
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
    <div class="hero-actions">{follow_btn(slug, 'btn btn-follow', on='Following this story', off='Follow story')}<button type="button" class="btn btn-light" data-share>{ICON_SHARE}Share</button></div>
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
        <ol class="events">{''.join(items)}</ol>
        {ups}
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
    ld = {"@context": "https://schema.org", "@type": "Article", "headline": s["title"], "description": s["dek"],
          "dateModified": s["updated"], "datePublished": s["updated"], "url": f"{site['domain']}/stories/{slug}/",
          "image": f"{site['domain']}/og/{slug}.png", "publisher": {"@type": "Organization", "name": "Newspin", "url": site["domain"]},
          "articleSection": s["category"]}
    return page(site, title=f"{s['seoTitle']} | Newspin", desc=s["dek"], path=f"/stories/{slug}/", body=body,
                story_slug=slug, og_image=f"/og/{slug}.png", jsonld=ld, nav="story")


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
    body = f"""<div class="wrap-narrow prose">
<h1>Privacy</h1>
<p><em>Last updated {e(nice_date(site['today']))}.</em></p>
<h2>No accounts, no tracking cookies</h2>
<p>You can read Newspin without signing up. Newspin does not set advertising or tracking cookies.</p>
<h2>What your browser stores</h2>
<p>When you follow a story, switch the detail level or open a timeline, Newspin saves that choice and the date in your browser’s local storage, so it can show you what changed since your last visit. This stays on your device and is never sent to us. Clearing your browser data removes it.</p>
<h2>Fonts</h2>
<p>Pages load fonts from Google Fonts, which means your browser connects to Google’s servers to fetch them.</p>
<h2>Email alerts</h2>
<p>If email alerts are offered and you sign up, we use your email address only to send updates on the stories you chose, and you can unsubscribe at any time.</p>
<h2>Contact</h2>
<p>Questions: <a href="mailto:{e(site.get('contactEmail', 'hello@newspinapp.com'))}">{e(site.get('contactEmail', 'hello@newspinapp.com'))}</a></p>
</div>"""
    return page(site, title="Privacy | Newspin", desc="What Newspin stores and why.", path="/privacy/", body=body, nav="privacy")


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
        dr.ellipse((60, 52, 100, 92), outline="#FFFFFF", width=4)
        dr.ellipse((73, 65, 87, 79), fill="#3B6CF0")
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
                dr.ellipse((px - 8, ty - 8, px + 8, ty + 8), fill="#FFFFFF" if ev is not s["events"][-1] else "#F97316")
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
    today = dt.date.fromisoformat(os.environ.get("NEWSPIN_TODAY") or dt.date.today().isoformat())
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
    for name, fn in [("about", build_about), ("privacy", build_privacy)]:
        (DIST / name).mkdir()
        (DIST / name / "index.html").write_text(fn(site))
    (DIST / "404.html").write_text(build_404(site))
    dom = site["domain"].rstrip("/")
    urls = [("/", site["today"])] + [(f"/stories/{s}/", stories[s]["updated"]) for s in order] + [("/about/", site["today"]), ("/privacy/", site["today"])]
    sm = "".join(f"<url><loc>{dom}{u}</loc><lastmod>{m}</lastmod></url>" for u, m in urls)
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {dom}/sitemap.xml\n")
    build_og(site, stories, order, axis)
    print(f"Built {len(order)} stories into {DIST}")


if __name__ == "__main__":
    main()
