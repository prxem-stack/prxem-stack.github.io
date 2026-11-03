# Official calendar updater

The installed Android/iOS clients consume `news-alert/reviewed.json` (schema 1).
The GitHub Actions workflow refreshes it at minutes 17 and 47 of each hour,
independently of the developer's computer. GitHub schedules may be delayed.
Workflow dispatch can trigger an immediate refresh. Public-source coverage is
partial, not a comprehensive live market-news subscription.

Sources: BEA release schedules (current and next year), Federal Reserve monthly
calendars, ECB statistical calendar, selected confirmed ONS macro releases, BLS
published iCalendar, and Federal Reserve press-release RSS. Headlines remain
separate from timed releases. No Actual/Forecast values or firm restrictions
are inferred. Impact levels are app classifications.

Network calls have timeouts, bounded retries and response-size limits. A missing
page structure, empty response or a schedule without upcoming events counts as
source failure. Each healthy source replaces its own snapshot, allowing official
reschedules/removals; failed sources retain their previous records. An all-source
outage preserves the existing publication. UTC conversion uses official source
timezones (including DST); all-day or untimed events are skipped.

`news-alert/health.json` records checked time, last successful fetch and errors
per source. A successful fetch is not a claim that the government changed the
schedule. `publishedAt` is the time this combined snapshot was published, not
proof that every source is healthy. The workflow publishes healthy sources and
health metadata before marking a degraded run failed, so GitHub can report it.
Check repository Actions notifications for failures. Do not hide repeated errors
or relabel stale source data as newly verified.

As of 2026-11-03 BLS returns HTTP 403 both locally and on GitHub Actions. The
November BLS events were manually verified against its official monthly schedule
and retain that provenance. The updater retries the official ICS without bypassing
access controls. Other currencies/sources are not covered; blank calendar results
do not imply no economic releases exist.

Run locally:

    pip install -r scripts/news_calendar/requirements.txt
    python -m unittest discover -s scripts/news_calendar -v
    python scripts/news_calendar/update.py

Exit 1 means at least one source failed; inspect health.json even if useful data
was published. An expired cached calendar cannot be made current by repeatedly
refreshing a client. Repair the upstream source/scheduler instead.
