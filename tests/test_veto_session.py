import json
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from civic_tracker.veto_session import classify_action, context, load_config

ROOT = Path(__file__).resolve().parents[1]


class VetoSessionTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(ROOT)

    def test_published_days_and_status_are_explicit(self):
        self.assertEqual(self.config['session_days'], ['2026-11-17', '2026-11-18', '2026-11-19'])
        self.assertEqual(context(self.config, date(2026, 11, 17))['status'], 'active')
        self.assertEqual(context(self.config, date(2026, 11, 20))['status'], 'published-days-passed')

    def test_no_unpublished_december_dates_are_inferred(self):
        self.assertEqual(context(self.config, '2026-11-30')['session_days'], ['2026-11-17', '2026-11-18', '2026-11-19'])
        self.assertIn('No December date is inferred', self.config['scope_note'])

    def test_action_labels_are_explainable_and_narrow(self):
        self.assertIn('gubernatorial-veto', classify_action('Governor vetoed the bill'))
        self.assertIn('governor-recommendations', classify_action('Returned to the General Assembly with recommendations'))
        self.assertIn('reduced-or-vetoed-appropriation', classify_action('Appropriation reduced by the Governor'))
        self.assertIn('veto-session-procedure', classify_action('Resolution adopted'))
        self.assertEqual(classify_action('Placed on the calendar for third reading'), [])

    def test_config_is_json_and_has_both_chambers(self):
        parsed = json.loads((ROOT / 'config/veto-session.json').read_text(encoding='utf-8'))
        self.assertEqual(set(parsed['calendar_urls']), {'house', 'senate', 'house_schedule', 'senate_schedule'})
