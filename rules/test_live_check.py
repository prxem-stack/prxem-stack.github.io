import unittest
from datetime import datetime, timezone
from live_check import build, normalize, state


class Checks(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 6, tzinfo=timezone.utc)
        self.record = {'id': 'test', 'sources': ['https://official.example/'], 'approvedHashes': {'https://official.example/': 'same'}}
        self.pages = {'https://official.example/': {'status': 'fetched', 'sha256': 'same'}}

    def test_verified(self):
        self.assertEqual(state(self.record, self.pages, self.now), 'verified')

    def test_changed(self):
        self.pages['https://official.example/']['sha256'] = 'changed'
        self.assertEqual(state(self.record, self.pages, self.now), 'review_pending')

    def test_unavailable(self):
        self.pages['https://official.example/']['status'] = 'unavailable'
        self.assertEqual(state(self.record, self.pages, self.now), 'unavailable')

    def test_expired(self):
        self.record['endsAt'] = '2026-10-05T00:00:00Z'
        self.assertEqual(state(self.record, self.pages, self.now), 'expired')

    def test_first_check_not_approval(self):
        self.record['approvedHashes'] = {}
        feed, review = build({'offers': [self.record], 'rules': []}, self.pages, self.now)
        self.assertEqual(feed['offers'], [])
        self.assertEqual(review[0]['status'], 'review_pending')

    def test_strip_scripts(self):
        self.assertEqual(normalize('<p>Hello</p><script>wrong()</script><p>world &amp; you</p>'), 'Hello world & you')

    def test_independent_change_review_is_not_numeric_approval(self):
        change = {**self.record, 'id': 'ftmo.one', 'changes': [{'kind': 'new', 'title': 'Test', 'details': 'Details', 'appliesTo': '1-Step only'}]}
        model = {**self.record, 'id': 'ftmo.one', 'approvedHashes': {}}
        manifest = {'offers': [], 'rules': [model], 'changeReviews': [change]}
        feed, _ = build(manifest, self.pages, self.now)
        self.assertEqual(feed['ruleChecks']['ftmo.one']['status'], 'review_pending')
        self.assertEqual(len(feed['ruleChanges']), 1)
        self.assertEqual(feed['rulePatches'], [])
        self.pages['https://official.example/']['sha256'] = 'changed'
        feed, review = build(manifest, self.pages, self.now)
        self.assertEqual(feed['ruleChanges'], [])
        self.assertTrue(any(r['kind'] == 'changeReviews' for r in review))

    def test_unknown_change_model_fails(self):
        with self.assertRaises(ValueError):
            build({'offers': [], 'rules': [], 'changeReviews': [self.record]}, self.pages, self.now)

    def test_scoped_changes_require_review(self):
        self.record['id'] = 'ftmo.two'
        self.record['changes'] = [{'kind': 'removed', 'title': 'Example', 'details': 'Test only', 'appliesTo': 'Example cohort'}]
        feed, _ = build({'offers': [], 'rules': [self.record]}, self.pages, self.now)
        self.assertEqual(feed['ruleChanges'][0]['modelId'], 'ftmo.two')
        self.pages['https://official.example/']['sha256'] = 'changed'
        feed, _ = build({'offers': [], 'rules': [self.record]}, self.pages, self.now)
        self.assertEqual(feed['ruleChanges'], [])


if __name__ == '__main__':
    unittest.main()
