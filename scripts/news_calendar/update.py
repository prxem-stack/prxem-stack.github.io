"""Synchronize public official calendars; never infer a release time from a headline."""
import calendar
import hashlib
import json
import re
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'news-alert'
UA = 'PropFirmNewsAlert/1.0 (+https://prxem-stack.github.io/prop-firm-news-alert/)'

def stamp(dt):
    return dt.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')

def fetch(url):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(request, timeout=25) as response:
                data = response.read(4_000_001)
            if len(data) > 4_000_000:
                raise ValueError('Source exceeded size limit')
            return data.decode('utf-8-sig')
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def impact(title):
    if re.search(r'consumer price|producer price|employment situation|gross domestic|\bGDP\b|HICP|FOMC|interest rate decision|personal income and outlays', title, re.I):
        return 'high'
    return 'medium'

def event(provider, title, date, country, url, now):
    title = ' '.join(title.split())
    key = hashlib.sha256(f'{provider}|{title}|{stamp(date)}'.encode()).hexdigest()[:20]
    return dict(id=f'{provider}-{key}', title=title, date=stamp(date), country=country,
                impact=impact(title), source=url, status='published', reviewedAt=stamp(now),
                provider=provider, verification='automatically parsed from official schedule')

def bea(now, get=fetch):
    result = []
    # Both year pages are needed across the December/January boundary.
    for suffix in ('', '/next-year'):
        url = 'https://www.bea.gov/news/schedule' + suffix
        soup = BeautifulSoup(get(url), 'html.parser')
        table = soup.select_one('#release-schedule-table')
        if not table:
            raise ValueError('BEA schedule table missing')
        year = re.search(r'Year\s+(\d{4})', table.get_text(' ', strip=True))
        if not year:
            raise ValueError('BEA schedule year missing')
        for row in table.select('tbody tr'):
            day, clock, title = row.select_one('.release-date'), row.select_one('.scheduled-date small'), row.select_one('.release-title')
            if not all((day, clock, title)):
                continue
            dt = datetime.strptime(f'{year[1]} {day.get_text(strip=True)} {clock.get_text(strip=True)}', '%Y %B %d %I:%M %p').replace(tzinfo=ZoneInfo('America/New_York'))
            result.append(event('bea', title.get_text(' ', strip=True), dt, 'USD', url, now))
    return result

def fed(now, get=fetch):
    result = []
    start = now.year * 12 + now.month - 1
    for index in range(start, start + 3):
        year, month0 = divmod(index, 12)
        month = month0 + 1
        url = f'https://www.federalreserve.gov/newsevents/{year}-{calendar.month_name[month].lower()}.htm'
        try:
            page = get(url)
        except urllib.error.HTTPError as error:
            if error.code == 404 and index > start:
                continue  # Future monthly pages may not have been published yet.
            raise
        soup = BeautifulSoup(page, 'html.parser')
        panels = soup.select('.panel-body > .row')
        if not panels:
            raise ValueError('Fed schedule structure missing')
        for row in panels:
            clock, title, days = row.select_one('.col-xs-2'), row.select_one('.col-xs-7'), row.select_one('.col-xs-3')
            if not all((clock, title, days)):
                continue
            match = re.fullmatch(r'(\d{1,2}):(\d{2})\s*([ap])\.m\.', clock.get_text(' ', strip=True))
            if not match:
                continue  # No inferred time for approximate dates, speeches or holidays.
            title_node = title.find('p')
            if not title_node:
                continue
            name = title_node.get_text(' ', strip=True)
            # Routine daily rates/balance sheets swamp meaningful macro releases.
            if re.match(r'(H\.\d|CP\b|G\.5\b)', name):
                continue
            day_text = days.get_text(' ', strip=True)
            if not re.fullmatch(r'[\d,\s]+', day_text):
                continue
            hour = int(match[1]) % 12 + (12 if match[3] == 'p' else 0)
            for day in re.findall(r'\d+', day_text):
                dt = datetime(year, month, int(day), hour, int(match[2]), tzinfo=ZoneInfo('America/New_York'))
                result.append(event('fed', name, dt, 'USD', url, now))
    return result

def ecb(now, get=fetch):
    url = 'https://www.ecb.europa.eu/press/calendars/statscal/html/index.en.html'
    soup = BeautifulSoup(get(url), 'html.parser')
    result = []
    for node in soup.select('.definition-list dt'):
        text = node.get_text(' ', strip=True)
        if 'tentative' in text.lower():
            continue
        if not re.fullmatch(r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}', text):
            continue
        description = node.find_next_sibling('dd')
        if description is None:
            continue
        name = description.get_text(' ', strip=True).split('Reference period:')[0].strip()
        dt = datetime.strptime(text, '%d/%m/%Y %H:%M').replace(tzinfo=ZoneInfo('Europe/Berlin'))
        result.append(event('ecb', name, dt, 'EUR', url, now))
    return result

def bls(now, get=fetch):
    url = 'https://www.bls.gov/schedule/news_release/bls.ics'
    text = re.sub(r'\r?\n[ \t]', '', get(url))
    if 'BEGIN:VCALENDAR' not in text:
        raise ValueError('BLS calendar missing')
    result = []
    for block in text.split('BEGIN:VEVENT')[1:]:
        fields = {}
        for line in block.splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                fields[key] = value
        entry = next(((k, v) for k, v in fields.items() if k.startswith('DTSTART')), None)
        if not entry or 'SUMMARY' not in fields:
            continue
        key, value = entry
        if value.endswith('Z'):
            dt = datetime.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=UTC)
        elif 'TZID=America/New_York' in key or 'TZID=US/Eastern' in key:
            dt = datetime.strptime(value, '%Y%m%dT%H%M%S').replace(tzinfo=ZoneInfo('America/New_York'))
        else:
            continue  # Do not guess timezone or all-day times.
        result.append(event('bls', fields['SUMMARY'].replace('\\,', ','), dt, 'USD', url, now))
    return result

def headlines(now, get=fetch):
    url = 'https://www.federalreserve.gov/feeds/press_all.xml'
    root = ET.fromstring(get(url))
    result = []
    for item in root.findall('./channel/item'):
        title, link, date = (item.findtext(k) for k in ('title', 'link', 'pubDate'))
        if not all((title, link, date)) or not link.startswith('https://www.federalreserve.gov/'):
            continue
        dt = parsedate_to_datetime(date)
        if dt.tzinfo is None or dt > now + timedelta(minutes=5):
            continue
        result.append(dict(id='fed-news-' + hashlib.sha256(link.encode()).hexdigest()[:20],
                           title=title, source=link, publishedAt=stamp(dt), status='published', provider='fed-news'))
    return result[:50]

SOURCES = {'bea': bea, 'fed': fed, 'ecb': ecb, 'bls': bls, 'fed-news': headlines}

def synchronize(previous, now, sources=SOURCES):
    events, news, health = [], [], {}
    oldhealth = previous.get('sourceHealth', {})
    for name, load in sources.items():
        target, key = (news, 'headlines') if name == 'fed-news' else (events, 'events')
        try:
            rows = load(now)
            if not rows:
                raise ValueError('Empty source response; retaining last successful data')
            if key == 'events' and not any(datetime.fromisoformat(x['date'].replace('Z', '+00:00')) >= now for x in rows):
                raise ValueError('No future releases returned; retaining last successful data')
            target.extend(rows)
            health[name] = dict(status='ok', checkedAt=stamp(now), lastSuccessAt=stamp(now), records=len(rows))
        except Exception as error:
            saved = [x for x in previous.get(key, []) if x.get('provider') == name or x.get('id', '').startswith(name + '-')]
            target.extend(saved)
            health[name] = dict(status='error', checkedAt=stamp(now), lastSuccessAt=oldhealth.get(name, {}).get('lastSuccessAt'),
                                records=len(saved), error=str(error)[:240])
    lower, upper = now - timedelta(days=7), now + timedelta(days=100)
    events = [x for x in events if lower <= datetime.fromisoformat(x['date'].replace('Z', '+00:00')) <= upper]
    events = sorted({x['id']: x for x in events}.values(), key=lambda x: (x['date'], x['id']))
    news = sorted({x['id']: x for x in news}.values(), key=lambda x: x['publishedAt'], reverse=True)[:50]
    # Never make an all-source outage look like a newly published healthy feed.
    successful = any(x['status'] == 'ok' for x in health.values())
    return dict(schemaVersion=1, publishedAt=stamp(now) if successful else previous.get('publishedAt', stamp(now)),
                checkedAt=stamp(now), coverage='Partial official-source coverage: US BEA, Federal Reserve, BLS when available, and ECB statistics. Other calendars are not yet covered. Impact is an app classification.',
                sourceHealth=health, events=events, headlines=news)

def atomic_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'reviewed.json'
    previous = json.loads(path.read_text()) if path.exists() else {}
    result = synchronize(previous, datetime.now(UTC))
    # Keep the existing publication intact if all sources failed.
    if any(x['status'] == 'ok' for x in result['sourceHealth'].values()):
        atomic_json(path, result)
    atomic_json(OUT / 'health.json', dict(checkedAt=result['checkedAt'], sources=result['sourceHealth'],
                                        futureEvents=sum(x['date'] >= result['checkedAt'] for x in result['events'])))
    for name, state in result['sourceHealth'].items():
        print(name, state['status'], state['records'], state.get('error', ''))
    if any(x['status'] != 'ok' for x in result['sourceHealth'].values()):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
