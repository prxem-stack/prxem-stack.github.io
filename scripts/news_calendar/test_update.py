import unittest
import json
import urllib.error
from datetime import datetime, timezone
from update import synchronize, event, bea, fed, ecb, bls, ons, headlines

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
        self.assertEqual(bls(NOW, lambda _: html), [])

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

    def test_past_only_is_source_failure(self):
        old = self.row(date=datetime(2026,11,2,tzinfo=timezone.utc))
        result = synchronize({}, NOW, {'bea':lambda _: [old]})
        self.assertEqual(result['sourceHealth']['bea']['status'], 'error')

if __name__ == '__main__': unittest.main()
