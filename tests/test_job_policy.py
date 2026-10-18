"""Regression checks for feed expiry and exclusion rules."""
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
sys.path.insert(0, str(ROOT / 'build'))
import optout
import seo
from classify import classify
from fetch_feeds import recruitee


class JobPolicyTests(unittest.TestCase):
    def test_expiry_boundaries_and_metadata(self):
        today = datetime.now(ZoneInfo('Europe/Berlin')).date()
        row = dict(_feed=True, stellenangebotsTitel='Machine Learning Intern', firma='Test',
                   referenznummer='lever:test:1', country='DE', ats='lever',
                   retrieved=today.isoformat(), valid_through=today.isoformat(), featured=True)
        job, _ = classify(row)
        self.assertEqual(job['retrieved'], today.isoformat())
        self.assertTrue(job['featured'])
        self.assertFalse(seo.is_expired(job))
        posting = seo.job_posting(dict(job, page='test/'), {}, {}, {}, 'https://example.org', 'Test')
        self.assertEqual(posting['validThrough'], today.isoformat())
        row['valid_through'] = (today - timedelta(days=1)).isoformat()
        self.assertIsNone(classify(row)[0])
        self.assertTrue(seo.is_expired(row))
        row.pop('valid_through')
        with patch.dict('os.environ', FEED_MAX_STALE_DAYS='7'):
            row['retrieved'] = (today - timedelta(days=7)).isoformat()
            self.assertIsNotNone(classify(row)[0])
            row['retrieved'] = (today - timedelta(days=8)).isoformat()
            self.assertIsNone(classify(row)[0])
        fallback = seo.job_posting(dict(job, valid_through='', page='test/'), {}, {}, {}, 'https://example.org', 'Test')
        self.assertEqual(fallback['validThrough'], (today + timedelta(days=30)).isoformat())

    def test_optout_matching(self):
        with patch.object(optout, 'load_optout', return_value={
                'slugs': ['test'], 'names': ['Beispiel AG'], 'domains': ['example.org']}):
            for item in ({'id': 'lever:test:1'}, {'company': 'BEISPIEL ag'},
                         {'endpoint': 'https://jobs.example.org/feed'}, {'url': 'https://example.org/job'}):
                self.assertTrue(optout.is_opted_out(item))
            self.assertFalse(optout.is_opted_out({'url': 'https://otherexample.org/job'}))

    def test_recruitee_closing_date(self):
        company = {'ats': 'recruitee', 'slug': 'test', 'name': 'Test'}
        payload = {'offers': [{'id': 1, 'title': 'Machine Learning Intern', 'city': 'Berlin',
                              'country_code': 'DE', 'close_at': '2026-12-31T12:00:00Z'}]}
        self.assertEqual(next(recruitee(company, payload))['valid_through'], '2026-12-31')
