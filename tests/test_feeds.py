import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
import fetch_feeds as feeds
from geo import locate
from classify import classify


class FeedTests(unittest.TestCase):
    def test_geo(self):
        self.assertEqual(locate(['London', 'Erlangen, Germany (Hybrid)']), ('Erlangen', 'DE', 'Bayern'))
        self.assertEqual(locate(['Remote - Zürich']), ('Zürich', 'CH', 'Schweiz'))
        self.assertIsNone(locate(['Paris'], personio=True))
        self.assertIsNone(locate(['Remote'], country='US', remote=True))
        self.assertEqual(locate(['Unbekannt'], country='DE')[2], '')

    def test_cache_and_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'feed.json'
            with patch.object(feeds, 'request', return_value=(b'{"jobs": []}', 200, {'ETag': 'abc'})) as request:
                self.assertEqual(feeds.cached('https://example.org', path), ({'jobs': []}, False, True))
                feeds.cached('https://example.org', path)
                self.assertEqual(request.call_count, 1)
            with patch.dict('os.environ', FEED_MAX_AGE_H='0'):
                with patch.object(feeds, 'request', return_value=(None, 304, {})) as request:
                    self.assertFalse(feeds.cached('https://example.org', path)[1])
                    self.assertEqual(request.call_args.args[1]['If-None-Match'], 'abc')
                with patch.object(feeds, 'request', side_effect=OSError('offline')):
                    self.assertTrue(feeds.cached('https://example.org', path)[1])

    def test_feed_classifier_metadata(self):
        row = dict(_feed=True, stellenangebotsTitel='Machine Learning Engineer', firma='Test', referenznummer='lever:test:1', employment_type='internship', description='Machine learning with PyTorch', country='AT', ats='lever', url='https://example.org/job', region='Österreich')
        job, _ = classify(row)
        self.assertEqual(job['type'], 'Praktikum')
        self.assertEqual(job['source_label'], 'Zur Stelle bei Test')
        self.assertEqual(job['country'], 'AT')
        row['stellenangebotsTitel'] = 'Senior Machine Learning Engineer'
        self.assertIsNone(classify(row)[0])

    def test_plain(self):
        self.assertEqual(feeds.plain('&lt;p&gt;AI &amp;amp; ML&lt;/p&gt;'), 'AI & ML')


if __name__ == '__main__':
    unittest.main()
