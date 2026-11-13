# Newspin: instructions for Claude

Newspin (newspinapp.com) turns big ongoing news stories into sourced timelines. This repo holds the source. Every push to `main` triggers `.github/workflows/deploy.yml`, which runs `python3 build.py` and publishes `dist/` to the `gh-pages` branch (the live site). Never commit `dist/` or the built files at the repo root.

## Layout
- `data/site.json`: site settings, `order` (every story slug must be listed), categories.
- `data/stories/<slug>.json`: one file per story (fields documented in README.md).
- `build.py`: static site generator, no dependencies (Pillow optional for share images).
- `static/`: `app.js`, `styles.css`, icons.

## Editorial rules (non-negotiable)
1. Every event has at least one source; prefer two independent ones. Open the page before citing it; a search snippet alone is not enough for a new fact.
2. Label status honestly: "Confirmed · <who>", "Reported", "Stated", "Allegation · <who>", "Filed · not ruled on", "Official data", "Market data".
3. If outlets disagree, add a `differs` note rather than picking one.
4. Attribute allegations to whoever made them. Never state an allegation as fact.
5. Do not name private individuals (including people at the centre of scandals who are not public figures).
6. Never put a number, date or quote in a story from memory. If a figure cannot be sourced, leave it out.
7. Neutral language. No opinions, predictions or adjectives such as "shocking" or "historic" unless quoting someone.
8. US election seat counts: take them only from the AP results tool when it is available, give the time of the count, and say counts may change. Do not write that a party controls or won a chamber.
9. Write for general readers: short sentences, explain jargon, add what it means for ordinary people where relevant.

## Update routine (scheduled runs)
1. `git pull` on `main`.
2. For every story with `tone` "hot" or "live", and anything with an `upcoming` date that has passed, search for news since the story's `updated` date. Also check the AI stories (`ai-this-week`, `ai-model-tracker` and the company timelines) for new model releases and company news.
3. Add new events (with `added` set to today's date in IST), update `big`, `delta`, `bigLabel`, `glance`, `keyNumbers`, `status`, `tone`, `next` and `upcoming` where they changed, and set `updated` to today. Remove `upcoming` items whose date has passed.
4. `ai-model-tracker` uses `"order": "desc"` (newest first on the page); keep events sorted by date in the file as usual. Add each major model launch there and to the company's own timeline.
5. Only add a new story if it is clearly big news and can be sourced well; add its slug to `site.json` `order`.
6. Run `python3 build.py`. It must finish with "Built N stories". Check that every JSON file still parses.
7. Commit with a plain summary of what changed (one line per story) and push to `main`. If nothing material changed, do not commit.
8. Finish with a short report: stories updated, new stories, anything uncertain or left out and why.

## Style of code changes
Keep the design as it is unless asked. Owner's choices to preserve: light theme by default (dark only when the reader switches), the theme button's current position, the original story cards, and the brand accent in Travelpin's pin green (`--pin` #4B9C78; `--pin-ink` #2B6F51 for text; #6FC39C in dark mode), not orange.
