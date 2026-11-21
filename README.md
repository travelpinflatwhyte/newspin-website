# Newspin v0 — newspinapp.com

A static website: India's biggest ongoing stories as sourced timelines. No server, no database. It runs on any static host.

## What's in here

```
data/site.json            site settings, home-page order, "how stories connect" chain
data/stories/*.json       one file per story (events, numbers, sources, glance)
static/styles.css         all styles
static/app.js             follow, catch-me-up, Simple/Detailed, listen, share (stored in the reader's browser only)
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
3. Analytics: Cloudflare Web Analytics (cookie-free) is on every page via `page()` in build.py; the dashboard is in the Cloudflare account under Observability > Analytics > Web analytics. Keep the privacy page in step with any change.
4. Add the site to Google Search Console and submit `https://newspinapp.com/sitemap.xml`.
5. Have the About, Privacy and corrections wording reviewed, including any obligations for digital news publishers in India.
6. Open item in the data: the RBI's October FY27 inflation projection is listed as 5.0% (PRS) vs 5.2% (Swarajya, Deccan Herald). It's flagged as "Sources differ" on the page; confirm against the RBI statement and update.

## How the home page is ordered

Stories are ranked automatically; there is no manual order. Each story's score is:

- **freshness:** up to 10 points, fading over 20 days since the last event was added
- **coming up:** up to 6 points if a scheduled event is within a week (2 if within three weeks). Upcoming items marked `"minor": true` (market holidays and other non-events) still show in the Next strip but earn no points.
- **importance × 2:** `"importance"` in the story file, 1 (niche) to 5 (huge)
- **activity:** 1 point per event added in the last 14 days, up to 4
- **turning point:** 3 points if an event marked `"key": true` was added today or yesterday (`KEY_BONUS` in build.py), so a story's big day lifts it to the top

The home page, top to bottom:

- **Greeting and story bubbles:** the top eight stories; tapping one opens "Catch me up".
- **Lead card:** the highest-ranked story.
- **Next strip:** firm, dated events coming up.
- **Moving now:** up to four stories in the full card style, with news in the last 48 hours (topped up with the next highest-ranked stories if fewer moved). The roll-ups `ai-this-week` and `ai-model-tracker` are left out here and in Latest updates, because they repeat news from each company's timeline (`ROLLUPS` in `build.py`). Followed stories are not forced in.
- **Latest updates:** the eight newest events across all stories, grouped by day, each linking to that event.
- **All timelines:** every active story as one line in four groups (AI, India economy, World and US, Travel and everyday; see `home_group()`). A green dot means its latest event is from today or yesterday. On phones the groups fold, with the first open.
- **Quiet for now:** a story with no new event for 60 days, and nothing scheduled within 30 days, is listed in one line at the bottom until it gets a new event.

The ranking runs in `build.py` (and the same formula exists in `static/app.js`). Keep the two in step if you change the formula.

## Updating stories

Each story is a JSON file. To add an event, add an object to `events`:

```json
{"date": "2026-12-04", "dateLabel": "4 Dec 2026", "phase": "hike", "title": "…", "summary": "…",
 "status": "Confirmed", "numbers": [{"k": "Repo rate", "v": "5.50% → 5.75%"}],
 "sources": [{"name": "RBI", "url": "https://…", "primary": true}]}
```

Optional: `"key": true` highlights it, `"differs": "…"` adds a Sources differ note, `"link": "<slug>"` links another story, `"added": "YYYY-MM-DD"` sets when it was added (used for "new since your last visit"; defaults to the event date).

Phases: cut, hold, hike, data, forecast, policy, market, world, trade, law, tech.

Each story also has `"regions"` (any of India, World, US), and a `category` (Economy, Markets, Trade, World, Policy, Tech, AI, Travel). Stories that started less than four months ago get a zoomed-in timeline track automatically.

Also update `updated`, the card fields (`big`, `delta`, `bigLabel`, `status`, `tone`, `next`), `glance` and `upcoming` as the story moves. Then run `python3 build.py` and upload `dist/` again.

Or ask Claude: "Update the RBI story with today's decision", attach this project (or link the GitHub repo), and it will research, edit the JSON, rebuild and hand back a new `dist/`.

### Market wraps (`india-markets-daily`, `us-markets-daily`)

These stories set `market` (`index`, `second`, `tz`) and give each trading-day event a `session`: `prev` (previous close), `open`, `close`, and optionally `low` and `high`. The build works out the gap (open minus previous close; under 0.1% is a flat open), the day's change, the tags and the "Latest session" panel. Each day's `prev` must equal the previous day's `close`. Take open and close figures from two reports, and note any disagreement in `differs`. Information only: no tips, targets or forecasts.

### Headline change colour (optional)

On the lead card, a `delta` starting with ▲ shows green, ▼ shows red, anything else neutral. Set `"deltaTone": "good" | "bad" | "neutral"` where the arrow would mislead (inflation rising is not good news; a rate rise is neither).

### Lead headline (optional)

`heroTitle` and `heroDek` give the story a hand-written headline when it is the top story on the home page. Set `heroAsOf` to the date you wrote them. If a newer event arrives (its `added` date is later than `heroAsOf`), the build ignores them and shows the newest event's title and first sentence instead, so the lead never shows an out-of-date headline. Scheduled updates rewrite all three whenever the story moves.

### Flags on story bubbles (optional)

A story about one foreign country can set `"flag": "us"` (two-letter country code). The home-page bubble then shows that flag instead of a letter. Flag images live in `data/flags/` and come from the MIT-licensed flag-icons project (1x1 set); add a new file there before using a new code. Stories about India, about several countries, or about a company keep the letter. Company logos are not used: Nvidia and Anthropic both require written permission.

### Explainer diagrams (optional)

A story can carry an `explainers` list. Each item has `file` (an HTML fragment with an inline SVG in `data/explainers/`), `title`, `caption` and `sources`. They appear between the story's track and the timeline. Draw them from sourced figures only, say in the caption what is to scale and what isn't, and style them with the site's CSS variables so they work in dark mode. Don't use photos unless their licence allows commercial use.

### Timeline tools
Story pages get a Key moments / Everything switch (stories with 3+ events marked `"key": true` and 10+ events; 20+ events and 5+ keys open on Key moments), an order button, filter chips (by `phase` and by status label), a sticky date scrubber (8+ events) and folds for hidden stretches. The latest event and anything new since the reader's last visit always stay visible.

### Chart (optional)
Add `"chart": {"title": "Repo rate, %", "unit": "%", "step": true, "note": "..."}` to a story and a `chartValue` number to each event that reports that figure (taken from the event's own sourced `numbers`). At least 3 points are needed. Market wraps chart their daily closes automatically. Don't chart figures that mix measures (intraday vs close, different times of day).

## Search and sharing
- Every page: title, description, canonical, Open Graph and Twitter tags, `max-image-preview:large`.
- Story pages: NewsArticle + BreadcrumbList structured data; datePublished = first event added, dateModified = `updated`. Keep `updated` current on every edit.
- Keep `seoTitle` under about 50 characters (" | Newspin" is added) and `dek` under 160.
- `feed.xml` (RSS, latest 40 entries), `sitemap.xml`, `robots.txt`, and `CNAME` (newspinapp.com) are generated. Upload the whole zip so CNAME is never lost.

## Listen
- Uses the device's built-in text-to-speech (Web Speech API). No audio files, no service, no cost; nothing is sent anywhere.
- Story pages: "Listen" reads the 30-second summary, then the latest 3 updates (or what's new since the reader's last visit).
- Home: "Play my briefing" reads the latest update of followed stories (or stories that moved in the last 3 days). The lead card also has Listen.
- Catch me up: the speaker button narrates each update and moves on automatically.
- Text is cleaned for speech in app.js `clean()` (₹, cr, bps, mbpd, ≈, ranges). Buttons stay hidden on browsers without speech.
