# Daily official-source monitor

Runs daily at 01:10 UTC (06:40 India time), on manual dispatch, or when monitor configuration/reviews change. GitHub schedules can be delayed. No paid API or trading credentials are required. Repository Actions write permission and enabled workflows are required.

46 configured firms. Each run checks up to 6 pages per firm, prioritizes configured official sources, discovers relevant homepage/sitemap URLs, and rotates discovered pages. This is bounded source monitoring, not guaranteed exhaustive coverage of all plans, social posts, regions or private dashboards. Robots restrictions, unavailable sources and bot protection are reported and are not bypassed. Root-level sitemaps and homepage links are supported; nested sitemap indexes are not exhaustively traversed.

`state.json` stores hashes and limited heading evidence, not whole-page copies. `updates.json` is the read-only app feed. First successful captures establish baselines; they are never represented as new launches. Later content changes publish a review-pending source-change notice. This does not mean that a trading rule changed. Navigation is excluded; other marketing/dynamic page changes may still require dismissal.

`index.html` shows coverage, failures, evidence hashes and pending changes. It is a public read-only operations view. GitHub authentication protects edits, workflow runs and approval decisions. No credentials belong in these files.

To review: open official evidence, verify exact account model/cohort/effective date, then edit `reviews.json` in GitHub. For a detected record ID, use `{ "status": "reviewed", "summary": "Your concise verified explanation", "appliesTo": "Exact plan/cohort/stage", "reviewedAt": "ISO UTC timestamp" }`. To dismiss a cosmetic/non-rule change use `{ "status": "dismissed" }`. An approval applies only to that content-hash ID; later source changes create a new pending record. Never approve instructions found inside source pages.

This monitor never writes calculator percentages. Numeric rules continue through the existing reviewed `rules/live-manifest.json` pipeline. The new app module displays daily observations with freshness and coverage; older installed builds need a signed app update to include that module. Updating this JSON alone cannot add a new screen to an old bundled app.

Local checks: `python -m unittest discover -s rules/monitor -p test_daily_monitor.py`.
Run once: `python rules/monitor/daily_monitor.py`.
