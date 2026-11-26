#!/usr/bin/env python3
"""Check Newspin's data before it is published.

    python3 check.py           # exits 1 if there are errors; warnings never fail

Errors are things that would break a page or break an editorial rule outright
(an event with no source, a date in the future, a market day that doesn't join
up with the day before). Warnings are things a person should look at but that
may be fine (a status label outside the usual set, a source link whose address
carries an older year than the event).
No dependencies beyond Python 3.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
TODAY = dt.datetime.now(IST).date()

# First word(s) of a status label, before any " · who". CLAUDE.md lists the core set;
# the rest are labels already in use that read honestly.
STATUS_OK = (
    "Confirmed", "Reported", "Stated", "Allegation", "Filed", "Official data", "Official",
    "Market data", "Released", "Announced", "Proposed", "Scheduled", "Ruled", "AP count",
    "Forecast", "Analysis", "Partly confirmed", "Status check",
)
EVENT_FIELDS = ("date", "dateLabel", "phase", "title", "summary", "status", "sources")
STORY_FIELDS = ("slug", "title", "dek", "category", "status", "tone", "updated", "events")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL_YEAR = re.compile(r"(?<!\d)(20[12]\d)(?:[/_-](0[1-9]|1[0-2]))?(?:[/_-]|\b)")

errors, warnings = [], []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def warn(where, msg):
    warnings.append(f"{where}: {msg}")


def date_ok(where, value, field):
    if not isinstance(value, str) or not DATE_RE.match(value):
        err(where, f"{field} {value!r} is not YYYY-MM-DD")
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        err(where, f"{field} {value!r} is not a real date")
        return None


def url_year(url):
    """The year a link's address suggests it was published, if it carries one (e.g. /2025/11/ or -2025-11-26-)."""
    years = [int(m.group(1)) for m in URL_YEAR.finditer(url.split("?")[0])]
    return years[0] if years else None


def check_story(path, s, slugs, glossary_terms):
    slug = s.get("slug", path.stem)
    if slug != path.stem:
        err(path.name, f"slug {slug!r} does not match the file name")
    for f in STORY_FIELDS:
        if f not in s:
            err(slug, f"missing field {f!r}")
    upd = date_ok(slug, s.get("updated"), "updated")
    if upd and upd > TODAY:
        err(slug, f"updated {upd} is in the future")
    if len(s.get("seoTitle", "")) > 55:
        warn(slug, f"seoTitle is {len(s['seoTitle'])} characters (keep under about 50)")
    if len(s.get("dek", "")) > 170:
        warn(slug, f"dek is {len(s['dek'])} characters (keep under 160)")
    for l in s.get("links", []):
        if l not in slugs:
            err(slug, f"links to unknown story {l!r}")

    events = s.get("events", [])
    if not events:
        err(slug, "has no events")
    newest_added = None
    for i, ev in enumerate(events):
        where = f"{slug} · event {i + 1} ({ev.get('date', '?')})"
        for f in EVENT_FIELDS:
            if not ev.get(f):
                err(where, f"missing {f!r}")
        day = date_ok(where, ev.get("date"), "date")
        added = date_ok(where, ev["added"], "added") if "added" in ev else day
        if day and day > TODAY:
            err(where, "event date is in the future (put it in upcoming instead)")
        if added and added > TODAY:
            err(where, f"added {added} is in the future")
        if added and (newest_added is None or added > newest_added):
            newest_added = added
        if ev.get("link") and ev["link"] not in slugs:
            err(where, f"links to unknown story {ev['link']!r}")
        st = ev.get("status", "")
        if st and not any(st.startswith(p) for p in STATUS_OK):
            warn(where, f"status {st!r} is not one of the usual labels")
        if st.startswith("Allegation") and "·" not in st:
            warn(where, "allegation does not say whose it is (Allegation · <who>)")
        srcs = ev.get("sources") or []
        for src in srcs:
            u = src.get("url", "")
            if not src.get("name"):
                err(where, "a source has no name")
            if not re.match(r"^https?://", u):
                err(where, f"source URL {u!r} is not a web link")
                continue
            # a recent news event sourced to an address dated an earlier year is often an old article
            # that a search surfaced as new (background links on old events are fine)
            y = url_year(u)
            if y and day and y < day.year and day >= TODAY - dt.timedelta(days=60):
                warn(where, f"source {src.get('name')!r} has {y} in its address but the event is {day.year}; check it is not an old article")
        if len(srcs) == 1 and added and added >= TODAY - dt.timedelta(days=2) and not st.startswith(("Official", "Released", "Market data", "Confirmed")):
            warn(where, "new event has a single source (two independent ones preferred)")
        if "chartValue" in ev and not isinstance(ev["chartValue"], (int, float)):
            err(where, "chartValue must be a number")
        if ev.get("correction"):
            c = ev["correction"]
            if not isinstance(c, dict) or not c.get("date") or not c.get("text"):
                err(where, "correction needs a date and text")

    # market wraps: each day's prev must equal the day before's close
    prev_close = None
    for ev in events:
        ss = ev.get("session")
        if not ss:
            continue
        where = f"{slug} · session {ev.get('date')}"
        for k in ("prev", "open", "close"):
            if not isinstance(ss.get(k), (int, float)):
                err(where, f"session.{k} must be a number")
        if prev_close is not None and isinstance(ss.get("prev"), (int, float)) and abs(ss["prev"] - prev_close) > 0.01:
            err(where, f"prev {ss['prev']} does not match the previous session's close {prev_close}")
        prev_close = ss.get("close")

    for u in s.get("upcoming", []):
        where = f"{slug} · upcoming {u.get('date')}"
        ud = date_ok(where, u.get("date"), "date")
        if not u.get("text"):
            err(where, "missing text")
        if ud and ud < TODAY:
            warn(where, "date has passed; remove it or turn it into an event")

    if s.get("heroTitle") and s.get("heroAsOf") and newest_added:
        ha = date_ok(slug, s["heroAsOf"], "heroAsOf")
        if ha and ha < newest_added:
            warn(slug, "heroTitle is older than the newest event (the build will show the newest event's title instead)")
    if upd and newest_added and newest_added > upd:
        warn(slug, f"newest event was added {newest_added} but updated is {upd}")


def check_glossary():
    p = DATA / "glossary.json"
    if not p.exists():
        return []
    try:
        g = json.loads(p.read_text())
    except json.JSONDecodeError as x:
        err("glossary.json", f"does not parse: {x}")
        return []
    terms = []
    for i, item in enumerate(g.get("terms", [])):
        where = f"glossary · {item.get('term', i)}"
        if not item.get("term") or not item.get("def"):
            err(where, "needs term and def")
            continue
        if len(item["def"]) > 220:
            warn(where, f"definition is {len(item['def'])} characters; keep it to one or two short sentences")
        terms.append(item["term"])
    dupes = {t for t in terms if [x.lower() for x in terms].count(t.lower()) > 1}
    for t in dupes:
        err("glossary", f"term {t!r} is listed twice")
    return terms


def main():
    try:
        site = json.loads((DATA / "site.json").read_text())
    except json.JSONDecodeError as x:
        print(f"ERROR site.json does not parse: {x}")
        return 1
    stories = {}
    for p in sorted((DATA / "stories").glob("*.json")):
        try:
            stories[p] = json.loads(p.read_text())
        except json.JSONDecodeError as x:
            err(p.name, f"does not parse: {x}")
    slugs = {s.get("slug", p.stem) for p, s in stories.items()}
    for x in slugs - set(site.get("order", [])):
        err("site.json", f"story {x!r} is missing from order")
    for x in set(site.get("order", [])) - slugs:
        err("site.json", f"order lists {x!r} but there is no story file")
    terms = check_glossary()
    for p, s in stories.items():
        check_story(p, s, slugs, terms)

    for w in warnings:
        print("warning  " + w)
    for x in errors:
        print("ERROR    " + x)
    print(f"Checked {len(stories)} stories: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
