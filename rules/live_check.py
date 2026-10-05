"""Public, fail-closed source checks. No credentials, arbitrary scraping or inferred rules.

Reviewed snapshots are usable only while ALL approved page hashes still match.
Changed/new pages go to review.json. Never auto-approve a new baseline in CI.
"""
import hashlib
import html
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.skip = max(0, self.skip - 1)

    def handle_data(self, value):
        if not self.skip:
            self.parts.append(value)


def normalize(raw):
    parser = Text()
    parser.feed(raw)
    return re.sub(r'\s+', ' ', html.unescape(' '.join(parser.parts))).strip()


def fetch(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.username or parsed.password:
            raise ValueError('Invalid source')
        request = Request(url, headers={'User-Agent': 'PropFirmSourceCheck/1.0'})
        with urlopen(request, timeout=25) as response:
            dest = urlparse(response.url)
            if dest.scheme != 'https' or dest.hostname.removeprefix('www.') != parsed.hostname.removeprefix('www.'):
                raise ValueError('Unexpected redirect')
            if 'text/html' not in response.headers.get('Content-Type', ''):
                raise ValueError('Not HTML')
            raw = response.read(3_000_001)
            if len(raw) > 3_000_000:
                raise ValueError('Oversized page')
        text = normalize(raw.decode('utf-8', errors='replace'))
        if len(text) < 300 or any(x in text.lower() for x in ('verify you are human', 'just a moment...', 'access denied', 'enable javascript and cookies to continue')):
            raise ValueError('Source unavailable')
        return {'status': 'fetched', 'sha256': hashlib.sha256(text.encode()).hexdigest(), 'text': text}
    except Exception as exc:
        return {'status': 'unavailable', 'error': type(exc).__name__}


def state(record, pages, now):
    expires = record.get('endsAt')
    if expires and now >= datetime.fromisoformat(expires.replace('Z', '+00:00')):
        return 'expired'
    urls = record['sources']
    if not urls or any(pages[url]['status'] != 'fetched' for url in urls):
        return 'unavailable'
    approved = record.get('approvedHashes', {})
    if any(approved.get(url) != pages[url]['sha256'] for url in urls):
        return 'review_pending'
    return 'verified'


def build(manifest, pages, now):
    feed = {'schemaVersion': 1, 'checkedAt': now.isoformat(),
            'validUntil': (now + timedelta(hours=18)).isoformat(),
            'offers': [], 'ruleChecks': {}, 'rulePatches': []}
    review = []
    for kind in ('offers', 'rules'):
        for record in manifest[kind]:
            status = state(record, pages, now)
            evidence = {u: {k: v for k, v in pages[u].items() if k != 'text'} for u in record['sources']}
            if status != 'verified':
                review.append({'id': record['id'], 'kind': kind, 'status': status, 'evidence': evidence})
            if kind == 'offers':
                # Unverified terms are never published as actionable offers.
                if status == 'verified':
                    feed['offers'].append({k: v for k, v in record.items() if k not in ('approvedHashes',)})
            else:
                feed['ruleChecks'][record['id']] = {'status': status, 'sources': record['sources'], 'checkedAt': now.isoformat()}
                if status == 'verified' and record.get('patch'):
                    feed['rulePatches'].append({'id': record['id'], 'values': record['patch'], 'sources': record['sources']})
    feed['summary'] = {'publishedOffers': len(feed['offers']), 'ruleModels': len(feed['ruleChecks']),
                       'pendingReview': len(review), 'unavailableSources': sum(p['status'] == 'unavailable' for p in pages.values())}
    return feed, review


def run():
    manifest = json.loads((ROOT / 'live-manifest.json').read_text())
    urls = sorted({u for group in ('offers', 'rules') for r in manifest[group] for u in r['sources']})
    with ThreadPoolExecutor(max_workers=4) as pool:
        pages = dict(zip(urls, pool.map(fetch, urls)))
    now = datetime.now(timezone.utc)
    feed, review = build(manifest, pages, now)
    (ROOT / 'live.json').write_text(json.dumps(feed, indent=2) + '\n')
    (ROOT / 'review.json').write_text(json.dumps({'checkedAt': now.isoformat(), 'items': review}, indent=2) + '\n')
    print(json.dumps(feed['summary']))


if __name__ == '__main__':
    run()
