import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from civic_tracker import daily_federal as federal


class _Response:
    def __init__(self, data): self.data = data
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size=-1): return self.data[:size]


class _Opener:
    def __init__(self, api_handler, vote_handler=None):
        self.api_handler = api_handler
        self.vote_handler = vote_handler
    def open(self, request, timeout=0):
        url = request.full_url
        if 'api.congress.gov' in url:
            body = self.api_handler(url)
            return _Response(json.dumps(body).encode())
        if self.vote_handler:
            return _Response(self.vote_handler(url))
        raise HTTPError(url, 503, 'unavailable', {}, None)


class DailyFederalTests(unittest.TestCase):
    def test_amendment_date_uses_valid_submitted_date_and_rejects_missing_or_invalid(self):
        self.assertEqual(federal._valid_bill_date({'submittedDate': '2026-02-28'}), '2026-02-28')
        self.assertEqual(federal._valid_bill_date({'introducedDate': '2026-03-03', 'submittedDate': '2026-02-28'}), '2026-03-03')
        self.assertIsNone(federal._valid_bill_date({'submittedDate': '2026-02-30'}))
        self.assertIsNone(federal._valid_bill_date({}))

    def test_duplicate_pagination_keeps_last_good_relationship_and_votes_still_run(self):
        member = 'L000585'
        prior_bill = {'record_id': 'US-119-HR5', 'title': 'Prior title',
                      'introduced_date': '2025-01-01',
                      'source_url': 'https://www.congress.gov/bill/119/house-bill/5',
                      'relations': [{'member': member, 'role': 'sponsored'}]}
        prior = {'collected_at': '2026-10-16T00:00:00+00:00',
                 'bills': {'US-119-HR5': prior_bill}, 'votes': {}}
        base = f'https://api.congress.gov/v3/member/{member}/sponsored-legislation?format=json&limit=250'

        def api(url):
            path = url.split('?', 1)[0]
            if path.endswith('/L000585/sponsored-legislation'):
                return {'sponsoredLegislation': [], 'pagination': {'next': base}}
            if path.endswith('/L000585/cosponsored-legislation'):
                return {'pagination': {}}
            role = 'sponsoredLegislation' if 'sponsored-legislation' in path else 'cosponsoredLegislation'
            return {role: [], 'pagination': {}}

        with patch.dict('os.environ', {'CONGRESS_API_KEY': 'never-expose-this'}), \
             patch.object(federal, 'build_opener', return_value=_Opener(api)), \
             patch.object(federal.time, 'sleep'):
            archive, report = federal.refresh(Path('.'), prior,
                datetime(2026, 10, 17, tzinfo=timezone.utc))

        self.assertEqual(archive['bills']['US-119-HR5']['relations'], prior_bill['relations'])
        self.assertEqual(archive['collected_at'], prior['collected_at'])
        self.assertEqual(report['status'], 'partial')
        self.assertTrue(any(x['error'] == 'duplicate_pagination_url' for x in report['errors']))
        self.assertTrue(any(x['error'] == 'malformed_page' for x in report['errors']))
        self.assertTrue(any('clerk.house.gov' in x['source'] for x in report['errors']))
        self.assertNotIn('never-expose-this', json.dumps(report))

    def test_complete_sponsorship_removal_keeps_quiet_bill_record(self):
        ident = 'US-119-HR5'
        prior = {'collected_at': 'old', 'votes': {}, 'bills': {ident: {
            'record_id': ident, 'title': 'Prior', 'introduced_date': '2025-01-01',
            'source_url': 'https://www.congress.gov/bill/119/house-bill/5',
            'relations': [{'member': 'L000585', 'role': 'sponsored'}]}}}

        def api(url):
            role = 'sponsoredLegislation' if 'sponsored-legislation' in url else 'cosponsoredLegislation'
            return {role: [], 'pagination': {}}

        with patch.dict('os.environ', {'CONGRESS_API_KEY': 'test-key'}), \
             patch.object(federal, 'build_opener', return_value=_Opener(api)), \
             patch.object(federal.time, 'sleep'):
            archive, _ = federal.refresh(Path('.'), prior,
                datetime(2026, 10, 17, tzinfo=timezone.utc))
        self.assertIn(ident, archive['bills'])
        self.assertEqual(archive['bills'][ident]['relations'], [])

    def test_vote_request_cap_reports_unprocessed_ids_and_senate_empty_index(self):
        def api(url):
            role = 'sponsoredLegislation' if 'sponsored-legislation' in url else 'cosponsoredLegislation'
            return {role: [], 'pagination': {}}

        house = ('<div>of 119 Results</div>' + ''.join(
            f'<div>Roll Call Number: {n}</div>' for n in range(1, 120))).encode()
        senate = b'<roll_call_vote_menu><congress>119</congress><session>2</session><votes></votes></roll_call_vote_menu>'

        def votes(url):
            if 'MemberVotes' in url:
                return house
            if 'vote_menu_' in url:
                return senate
            return b'<invalid/>'

        with patch.dict('os.environ', {'CONGRESS_API_KEY': 'test-key'}), \
             patch.object(federal, 'MAX_VOTE_REQUESTS', 6), \
             patch.object(federal, 'build_opener', return_value=_Opener(api, votes)), \
             patch.object(federal.time, 'sleep'):
            _, report = federal.refresh(Path('.'), {'collected_at': 'old', 'bills': {}, 'votes': {}},
                datetime(2026, 10, 17, tzinfo=timezone.utc))
        house_report = next(x for x in report['vote_sources'] if 'clerk.house.gov' in x['source'])
        senate_report = next(x for x in report['vote_sources'] if 'senate.gov' in x['source'])
        self.assertEqual(report['vote_requests'], 6)
        self.assertEqual(house_report['pending'], 115)
        self.assertFalse(house_report['complete'])
        self.assertFalse(senate_report['complete'])
        self.assertTrue(any(x['source'].startswith('https://www.senate.gov/') and x['error'] == 'incomplete_index'
                            for x in report['errors']))

    def test_senate_named_choices_are_exact_and_unrecognized_labels_stay_unknown(self):
        xml = b'''<roll_call_vote>
          <congress>119</congress><session>2</session><vote_number>7</vote_number>
          <vote_date>October 16, 2026, 1:02 PM</vote_date><vote_question_text>On the motion</vote_question_text>
          <count><yeas>1</yeas><nays>1</nays><present>0</present><absent>0</absent></count>
          <members>
            <member><lis_member_id>S253</lis_member_id><state>IL</state><vote_cast>Yea</vote_cast></member>
            <member><lis_member_id>S386</lis_member_id><state>IL</state><vote_cast>Nay</vote_cast></member>
          </members></roll_call_vote>'''
        parsed = federal._parse_senate(xml, 2, 7, '2026-10-17T00:00:00+00:00')
        self.assertEqual([(c['bioguide'], c['choice'], c['raw']) for c in parsed['choices']],
                         [('D000563', 'yes', 'Yea'), ('D000622', 'no', 'Nay')])
        self.assertEqual(federal.normalize_choice('NV'), 'unknown:NV')
        xml = xml.replace(b'<vote_cast>Nay</vote_cast>', b'<vote_cast>NV</vote_cast>')
        with self.assertRaisesRegex(ValueError, 'unknown_vote_label'):
            federal._parse_senate(xml, 2, 7, '2026-10-17T00:00:00+00:00')


if __name__ == '__main__':
    unittest.main()
