# Newspin v0 — newspinapp.com

A static website: India's biggest ongoing stories as sourced timelines. No server, no database. It runs on any static host.

## What's in here

```
data/site.json            site settings, home-page order, "how stories connect" chain
data/stories/*.json       one file per story (events, numbers, sources, glance)
static/styles.css         all styles
static/app.js             follow, catch-me-up, Simple/Detailed, filters, share (stored in the reader's browser only)
build.py                  turns data/ into the finished site in dist/
dist/                     the finished site: upload this folder
```

## Build

```
python3 build.py
```

Needs Python 3.9+. Pillow (`pip install pillow`) is optional; it makes the share images in `dist/og/`.

## Deploy

Upload the contents of `dist/` to the host that runs travelpinapp.com, as a separate site for newspinapp.com, then point the domain at it.

- **Netlify / Cloudflare Pages / Vercel:** create a new project, drag in `dist/` (or connect a GitHub repo with build command `python3 build.py` and output folder `dist`). Add `newspinapp.com` as a custom domain and follow the DNS steps they show.
- **GitHub Pages:** push `dist/` to a `gh-pages` branch and set the custom domain.
- **Any web server:** copy `dist/` to the web root. Configure `404.html` as the not-found page.

## Before launch

1. Create the mailbox `hello@newspinapp.com` (used for corrections), or change `contactEmail` in `data/site.json`.
2. Email alerts: create a form with a newsletter or forms service and put its form URL in `signupAction` in `data/site.json`. While empty, story pages show "Follow" only.
3. Add analytics if you want it (a privacy-friendly one), and update the privacy page to match.
4. Add the site to Google Search Console and submit `https://newspinapp.com/sitemap.xml`.
5. Have the About, Privacy and corrections wording reviewed, including any obligations for digital news publishers in India.
6. Open item in the data: the RBI's October FY27 inflation projection is listed as 5.0% (PRS) vs 5.2% (Swarajya, Deccan Herald). It's flagged as "Sources differ" on the page; confirm against the RBI statement and update.

## How the home page is ordered

Stories are ranked automatically; there is no manual order. Each story's score is:

- **freshness:** up to 10 points, fading over 20 days since the last event was added
- **coming up:** up to 6 points if a scheduled event is within a week (2 if within three weeks)
- **importance × 2:** `"importance"` in the story file, 1 (niche) to 5 (huge)
- **activity:** 1 point per event added in the last 14 days, up to 4

The top two stories are shown large. A story with no new event for 60 days, and nothing scheduled within 30 days, moves to "Quiet for now" until it gets a new event. Readers can switch the order to Latest update, Coming up or Biggest stories. The ranking runs in `build.py` and again in the reader's browser (`static/app.js`), so the order stays current between rebuilds. Keep the two in step if you change the formula.

## Updating stories

Each story is a JSON file. To add an event, add an object to `events`:

```json
{"date": "2026-12-04", "dateLabel": "4 Dec 2026", "phase": "hike", "title": "…", "summary": "…",
 "status": "Confirmed", "numbers": [{"k": "Repo rate", "v": "5.50% → 5.75%"}],
 "sources": [{"name": "RBI", "url": "https://…", "primary": true}]}
```

Optional: `"key": true` highlights it, `"differs": "…"` adds a Sources differ note, `"link": "<slug>"` links another story, `"added": "YYYY-MM-DD"` sets when it was added (used for "new since your last visit"; defaults to the event date).

Phases: cut, hold, hike, data, forecast, policy, market, world, trade, law, tech.

Each story also has `"regions"` (any of India, World, US), which drives the region filter on the home page, and a `category` (Economy, Markets, Trade, World, Policy, Tech). Stories that started less than four months ago get a zoomed-in timeline track automatically.

Also update `updated`, the card fields (`big`, `delta`, `bigLabel`, `status`, `tone`, `next`), `glance` and `upcoming` as the story moves. Then run `python3 build.py` and upload `dist/` again.

Or ask Claude: "Update the RBI story with today's decision", attach this project (or link the GitHub repo), and it will research, edit the JSON, rebuild and hand back a new `dist/`.
