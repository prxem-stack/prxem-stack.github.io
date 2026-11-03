# Official calendar updater

The installed Android/iOS clients consume `news-alert/reviewed.json` (schema 1).
The GitHub Actions workflow refreshes it at minutes 17 and 47 of each hour,
independently of the developer's computer. GitHub schedules may be delayed.
Workflow dispatch can trigger an immediate refresh. Public-source coverage is
partial, not a comprehensive live market-news subscription.

Sources: BEA release schedules (current and next year), Federal Reserve monthly
calendars, ECB statistical calendar, selected confirmed ONS macro releases, BLS
published iCalendar with a St. Louis Fed FRED calendar fallback, and Federal Reserve press-release RSS. Headlines remain
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

BLS delivery is automatic: try the official ICS first; on access failure, malformed
content, or exhausted dates, fetch the public FRED calendar for these eight BLS
releases: CPI, Employment Situation, JOLTS, PPI, Productivity and Costs, Import/Export
Prices, State Employment, and Metropolitan Employment. FRED explicitly supplies
release dates and times in US Central Time. Convert with America/Chicago (DST),
never a fixed offset or an assumed 08:30 ET. Missing times, unexpected names,
missing timezone declarations and incomplete pagination cause failure instead of
guessed events. Source links point to the actual dated FRED calendar query.

Health reports `BLS direct ICS` or `FRED fallback` and names the fallback's covered
releases. FRED success is not a claim that BLS direct access recovered. BLS records
are replaced by the live successful source, so November's manually seeded entries
are no longer needed. This fallback covers the eight named releases, not every BLS
publication (for example, Real Earnings is not separately supplied). If both sources
fail, preserve the last working snapshot and fail the workflow visibly. New-year
windows advance automatically; only published schedules are included, with no
invented future dates. Other currencies/sources remain partial coverage.

Run locally:

    pip install -r scripts/news_calendar/requirements.txt
    python -m unittest discover -s scripts/news_calendar -v
    python scripts/news_calendar/update.py

Exit 1 means at least one source failed; inspect health.json even if useful data
was published. An expired cached calendar cannot be made current by repeatedly
refreshing a client. Repair the upstream source/scheduler instead.
