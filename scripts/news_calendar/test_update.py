import unittest
import json
import urllib.error
from datetime import datetime, timezone
from update import synchronize, event, bea, fed, ecb, bls, bls_ical, fred_bls, BLS_RELEASES, ons, headlines

NOW = datetime(2026, 11, 3, tzinfo=timezone.utc)

class SyncTests(unittest.TestCase):
    def row(self, provider='bea', date=None):
        return event(provider, 'GDP', date or datetime(2026, 11, 25, 13, 30, tzinfo=timezone.utc), 'USD', 'https://www.bea.gov/news/schedule', NOW)

    def test_empty_response_preserves_previous(self):
        old = dict(publishedAt='2026-11-02T00:00:00Z', events=[self.row()])
        result = synchronize(old, NOW, {'bea': lambda _: []})
        self.assertEqual(result['events'], old['events'])
        self.assertEqual(result['publishedAt'], old['publishedAt'])
        self.assertEqual(result['sourceHealth']['bea']['status'], 'error')

    def test_one_failure_does_not_block_other_sources(self):
        def fail(_): raise ValueError('Bad HTML')
        result = synchronize({'events': [self.row('fed')]}, NOW, {'fed': fail, 'bea': lambda _: [self.row()]})
        self.assertEqual(len(result['events']), 2)
        self.assertEqual(result['sourceHealth']['bea']['status'], 'ok')
        self.assertEqual(result['sourceHealth']['fed']['status'], 'error')

    def test_success_replaces_rescheduled_source(self):
        result = synchronize({'events': [self.row()]}, NOW, {'bea': lambda _: [self.row(date=datetime(2026,11,26,13,30,tzinfo=timezone.utc))]})
        self.assertEqual(len(result['events']), 1)
        self.assertTrue(result['events'][0]['date'].startswith('2026-11-26'))

    def test_bea_reads_year_and_dst(self):
        def get(_): return '''<table id="release-schedule-table"><th>Year 2026</th><tbody><tr><td class="scheduled-date"><div class="release-date">November 4</div><small>8:30 AM</small></td><td class="release-title">Trade</td></tr></tbody></table>'''
        self.assertEqual(bea(NOW,get)[0]['date'], '2026-11-04T13:30:00Z')

    def test_ecb_skips_tentative(self):
        html = '<div class="definition-list"><dl><dt>04/11/2026 15:00</dt><dd>HICP<br>Reference period: Oct</dd><dt>06/11/2026 10:00 Tentative</dt><dd>Other</dd></dl></div>'
        rows = ecb(NOW, lambda _: html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['date'], '2026-11-04T14:00:00Z')

    def test_bls_no_guessed_timezone(self):
        html = 'BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART:20261106T083000\nSUMMARY:Employment\nEND:VEVENT'
        self.assertEqual(bls_ical(NOW, lambda _: html), [])

    def test_fed_unpublished_future_month_is_not_an_outage(self):
        def get(url):
            if 'november' not in url:
                raise urllib.error.HTTPError(url,404,'Not published',{},None)
            return '<div class="panel-body"><div class="row"><div class="col-xs-2"><p>2:00 p.m.</p></div><div class="col-xs-7"><p>FOMC Minutes</p></div><div class="col-xs-3"><p>18</p></div></div></div>'
        rows = fed(NOW,get)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['date'],'2026-11-18T19:00:00Z')

    def test_ons_excludes_cancelled_provisional_and_duplicate_datasets(self):
        rows=[]
        for title, extra in [('GDP monthly estimate', {}), ('GDP quarterly', {'cancelled':True}), ('GDP provisional', {'finalised':False}), ('GDP monthly time series', {})]:
            rows.append({'uri':'/releases/gdp', 'description':{'title':title,'release_date':'2026-11-12T07:00:00Z','finalised':True,**extra}})
        result = ons(NOW,lambda _:json.dumps({'releases':rows,'breakdown':{'total':4}}))
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['country'],'GBP')

    def test_headlines_never_become_scheduled_events(self):
        xml='<rss><channel><item><title>Fed announcement</title><link>https://www.federalreserve.gov/newsevents/pressreleases/example.htm</link><pubDate>Mon, 02 Nov 2026 15:00:00 GMT</pubDate></item></channel></rss>'
        result = headlines(NOW,lambda _:xml)
        self.assertEqual(len(result),1)
        self.assertNotIn('date',result[0])
        self.assertNotIn('impact',result[0])

    def fred_page(self, release_id, title, day='Tuesday November 10, 2026', clock='7:30 am'):
        return f'<div id="release-dates-pager"><table><tbody><tr><td colspan="2">{day}</td></tr><tr><td>{clock}</td><td><a href="/release?rid={release_id}">{title}</a></td></tr></tbody></table>Releases 1 - 1 of 1</div>All times are US Central Time'

    def fred_get(self, url):
        from urllib.parse import urlparse, parse_qs
        release_id = int(parse_qs(urlparse(url).query)['rid'][0])
        return self.fred_page(release_id, BLS_RELEASES[release_id])

    def test_bls_403_uses_automatic_official_fallback(self):
        def get(url):
            if 'bls.gov' in url:
                raise urllib.error.HTTPError(url,403,'Forbidden',{},None)
            return self.fred_get(url)
        result = bls(NOW,get)
        self.assertEqual(len(result),len(BLS_RELEASES))
        self.assertTrue(all(x['calendarSource']=='FRED' for x in result))
        self.assertEqual(result[0]['date'],'2026-11-10T13:30:00Z')

    def test_bls_valid_primary_does_not_call_fallback(self):
        calls=[]
        def get(url):
            calls.append(url)
            return 'BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART;TZID=America/New_York:20261106T083000\nSUMMARY:Employment Situation\nEND:VEVENT'
        result=bls(NOW,get)
        self.assertEqual(len(calls),1)
        self.assertEqual(result[0]['date'],'2026-11-06T13:30:00Z')

    def test_fred_central_dst_is_not_a_fixed_offset(self):
        def get(url):
            from urllib.parse import urlparse,parse_qs
            rid=int(parse_qs(urlparse(url).query)['rid'][0])
            return self.fred_page(rid,BLS_RELEASES[rid],day='Tuesday June 09, 2026')
        result=fred_bls(NOW,get)
        self.assertEqual(result[0]['date'],'2026-06-09T12:30:00Z')

    def test_fred_rejects_unknown_timezone_missing_time_and_truncation(self):
        for modify in [lambda x:x.replace('US Central Time','unknown time'),lambda x:x.replace('7:30 am','N/A'),lambda x:x.replace('of 1','of 2')]:
            with self.subTest(modify=modify),self.assertRaises(ValueError):
                fred_bls(NOW,lambda url:modify(self.fred_get(url)))

    def test_both_bls_sources_fail_retains_last_working_events(self):
        def fail(_):raise ValueError('network unavailable')
        previous={'publishedAt':'2026-11-02T00:00:00Z','events':[self.row('bls')]}
        result=synchronize(previous,NOW,{'bls':lambda now:bls(now,fail)})
        self.assertEqual(result['events'],previous['events'])
        self.assertEqual(result['sourceHealth']['bls']['status'],'error')
        self.assertEqual(result['publishedAt'],previous['publishedAt'])

    def test_past_only_is_source_failure(self):
        old = self.row(date=datetime(2026,11,2,tzinfo=timezone.utc))
        result = synchronize({}, NOW, {'bea':lambda _: [old]})
        self.assertEqual(result['sourceHealth']['bea']['status'], 'error')

if __name__ == '__main__': unittest.main()
