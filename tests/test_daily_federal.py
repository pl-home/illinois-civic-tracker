import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

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
    @staticmethod
    def house_page(page, total):
        start = (page - 1) * 10 + 1
        end = min(page * 10, total)
        return (f'<div>{start} - {end} of {total} Results</div>' + ''.join(
            f'<div>Roll Call Number: <a href="/Votes/2026{n}">{n}</a></div>'
            for n in range(total - start + 1, total - end, -1))).encode()

    def test_house_pages_validate_ranges_total_and_year(self):
        first, total = federal._house_page(self.house_page(1, 13), 1)
        last, _ = federal._house_page(self.house_page(2, 13), 2, total)
        self.assertEqual(sorted(first + last), list(range(1, 14)))
        for body, page, expected in [(self.house_page(1, 13), 2, 13),
                                     (self.house_page(2, 14), 2, 13)]:
            with self.assertRaisesRegex(ValueError, 'incomplete_index'):
                federal._house_page(body, page, expected)
        with self.assertRaisesRegex(ValueError, 'identity_mismatch'):
            federal._house_page(self.house_page(1, 13).replace(b'/Votes/2026', b'/Votes/2025'), 1)

    def test_new_secret_alias_and_transient_retries_are_bounded_and_sanitized(self):
        urls = []
        def api(url):
            urls.append(url)
            if len(urls) == 1:
                raise URLError('private transport text with never-publish-new')
            if len(urls) == 2:
                raise HTTPError(url, 503, 'private', {}, None)
            role = 'sponsoredLegislation' if '/sponsored-legislation' in url else 'cosponsoredLegislation'
            return {role: [], 'pagination': {'count': 0}}
        with patch.dict('os.environ', {'CONGRESSGOV_API': 'never-publish-new', 'CONGRESS_API_KEY': 'never-publish-old'}), \
             patch.object(federal, 'build_opener', return_value=_Opener(api)), \
             patch.object(federal.time, 'sleep'):
            _, report = federal.refresh(Path('.'), {}, datetime(2026, 10, 17, tzinfo=timezone.utc))
        self.assertEqual(report['api_attempts'], 8)
        self.assertTrue(all('api_key=never-publish-new' in u for u in urls))
        self.assertEqual(report['recovered_requests'][0],
                         {'source': 'Congress.gov API', 'attempts': 3, 'error': 'HTTP_503'})
        self.assertTrue(all(s['complete'] for s in report['legislation_sources']))
        self.assertNotIn('never-publish', json.dumps(report))

    def test_pagination_count_mismatch_retains_previous_relationship(self):
        prior = {'bills': {'US-119-HR5': {'relations': [{'member': 'L000585', 'role': 'sponsored'}]}}, 'votes': {}}
        def api(url):
            role = 'sponsoredLegislation' if '/sponsored-legislation' in url else 'cosponsoredLegislation'
            return {role: [], 'pagination': {'count': 1}}
        with patch.dict('os.environ', {'CONGRESS_API_KEY': 'test'}), \
             patch.object(federal, 'build_opener', return_value=_Opener(api)), \
             patch.object(federal.time, 'sleep'):
            archive, report = federal.refresh(Path('.'), prior, datetime(2026, 10, 17, tzinfo=timezone.utc))
        self.assertEqual(archive['bills'], prior['bills'])
        self.assertTrue(all(s['error'] == 'pagination_count_mismatch' for s in report['errors'] if s['source'] == 'Congress.gov API'))

    def test_permanent_http_errors_are_not_retried_and_transport_failures_keep_code(self):
        for exception, attempts, code in [(HTTPError('https://api.congress.gov',401,'private',{},None),6,'HTTP_401'),
                                          (URLError('private transport details'),18,'URLError')]:
            def api(url):
                raise exception
            with patch.dict('os.environ', {'CONGRESS_API_KEY':'test'}), \
                 patch.object(federal, 'build_opener', return_value=_Opener(api)), \
                 patch.object(federal.time, 'sleep'):
                _, report = federal.refresh(Path('.'), {}, datetime(2026,10,17,tzinfo=timezone.utc))
            self.assertEqual(report['api_attempts'], attempts)
            errors = [e for e in report['errors'] if e['source']=='Congress.gov API']
            self.assertEqual({e['error'] for e in errors}, {code})
            self.assertTrue(all(e['completed_pages']==0 and e['member_role'] for e in errors))
            self.assertNotIn('private', json.dumps(report))

    def test_distinct_url_duplicate_page_and_missing_count_cannot_prune_roles(self):
        relation = {'member': 'L000585', 'role': 'sponsored'}
        prior = {'bills': {'US-119-HR5': {'relations': [relation]}}, 'votes': {}}
        row = {'congress':119,'type':'HR','number':'6','introducedDate':'2026-01-01','title':'New'}
        def api(url):
            path = urlsplit(url).path
            if path.endswith('/L000585/sponsored-legislation'):
                nxt = 'https://api.congress.gov' + path + '?format=json&limit=250&offset=1'
                return {'sponsoredLegislation':[row], 'pagination':{'count':2, **({'next':nxt} if 'offset=1' not in url else {})}}
            if path.endswith('/L000585/cosponsored-legislation'):
                return {'cosponsoredLegislation':[], 'pagination':{}}
            role = 'sponsoredLegislation' if '/sponsored-legislation' in url else 'cosponsoredLegislation'
            return {role:[], 'pagination':{'count':0}}
        with patch.dict('os.environ', {'CONGRESS_API_KEY':'test'}), \
             patch.object(federal, 'build_opener', return_value=_Opener(api)), \
             patch.object(federal.time, 'sleep'):
            archive, report = federal.refresh(Path('.'), prior, datetime(2026,10,17,tzinfo=timezone.utc))
        self.assertEqual(archive['bills']['US-119-HR5']['relations'], [relation])
        self.assertEqual([e['error'] for e in report['errors'] if e['source']=='Congress.gov API'],
                         ['duplicate_legislation_record','pagination_count_mismatch'])
        self.assertTrue(all(not s['complete'] for s in report['legislation_sources'][:2]))

    def test_identical_within_page_source_duplicate_is_deduplicated_but_conflict_is_not(self):
        row = {'congress':119,'type':'S','number':'38','title':'Original','introducedDate':'2025-01-09'}
        prior = {'bills':{'US-119-HR5':{'relations':[{'member':'D000622','role':'sponsored'}]}}, 'votes':{}}
        for conflict in (False, True):
            def api(url):
                return {'sponsoredLegislation':[row,{**row, **({'title':'Conflicting'} if conflict else {})}],
                        'pagination':{'count':2}}
            with patch.dict('os.environ', {'CONGRESS_API_KEY':'test'}), \
                 patch.object(federal, 'build_opener', return_value=_Opener(api)), \
                 patch.object(federal.time, 'sleep'):
                archive, report = federal.refresh(Path('.'), prior, datetime(2026,10,17,tzinfo=timezone.utc),
                    member_roles={'D000622:sponsored'}, include_votes=False)
            self.assertEqual(report['legislation_sources'][0]['complete'], not conflict)
            if conflict:
                self.assertEqual(report['errors'][0]['error'], 'duplicate_legislation_record')
                self.assertEqual(archive['bills']['US-119-HR5']['relations'], prior['bills']['US-119-HR5']['relations'])
            else:
                self.assertEqual(report['duplicate_source_rows'][0]['identity'], [119,'S',38])
                self.assertEqual(archive['bills']['US-119-HR5']['relations'], [])
                self.assertEqual(len(archive['bills']['US-119-S38']['relations']), 1)

    def test_scoped_diagnostic_missing_key_has_named_incomplete_source(self):
        with patch.dict('os.environ', {'CONGRESS_API_KEY':'','CONGRESSGOV_API':''}):
            _, report = federal.refresh(Path('.'), {}, datetime(2026,10,17,tzinfo=timezone.utc),
                member_roles={'D000622:sponsored'}, include_votes=False)
        self.assertEqual(report['legislation_sources'][0]['source'], 'D000622:sponsored')
        self.assertFalse(report['legislation_sources'][0]['complete'])
        self.assertEqual(report['api_attempts'], 0)

    def test_house_pagination_collects_all_pages_before_selecting_votes(self):
        seen_pages = []
        def api(url):
            role = 'sponsoredLegislation' if '/sponsored-legislation' in url else 'cosponsoredLegislation'
            return {role: [], 'pagination': {'count': 0}}
        def votes(url):
            if 'MemberVotes' in url:
                page = int(parse_qs(urlsplit(url).query)['Page'][0])
                seen_pages.append(page)
                return self.house_page(page, 13)
            return b'<invalid/>'
        with patch.dict('os.environ', {'CONGRESS_API_KEY': 'test'}), \
             patch.object(federal, 'build_opener', return_value=_Opener(api, votes)), \
             patch.object(federal.time, 'sleep'):
            _, report = federal.refresh(Path('.'), {}, datetime(2026, 10, 17, tzinfo=timezone.utc))
        self.assertEqual(seen_pages, [1, 2])
        source = next(s for s in report['vote_sources'] if 'clerk.house.gov' in s['source'])
        self.assertEqual(source['discovered'], 13)
        self.assertEqual(source['selected'], 13)
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
                return {'sponsoredLegislation': [], 'pagination': {'count': 0, 'next': base}}
            if path.endswith('/L000585/cosponsored-legislation'):
                return {'pagination': {'count': 0}}
            role = 'sponsoredLegislation' if '/sponsored-legislation' in path else 'cosponsoredLegislation'
            return {role: [], 'pagination': {'count': 0}}

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
            role = 'sponsoredLegislation' if '/sponsored-legislation' in url else 'cosponsoredLegislation'
            return {role: [], 'pagination': {'count': 0}}

        with patch.dict('os.environ', {'CONGRESS_API_KEY': 'test-key'}), \
             patch.object(federal, 'build_opener', return_value=_Opener(api)), \
             patch.object(federal.time, 'sleep'):
            archive, _ = federal.refresh(Path('.'), prior,
                datetime(2026, 10, 17, tzinfo=timezone.utc))
        self.assertIn(ident, archive['bills'])
        self.assertEqual(archive['bills'][ident]['relations'], [])

    def test_vote_request_cap_reports_unprocessed_ids_and_senate_empty_index(self):
        def api(url):
            role = 'sponsoredLegislation' if '/sponsored-legislation' in url else 'cosponsoredLegislation'
            return {role: [], 'pagination': {'count': 0}}

        house = self.house_page(1, 9)
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
        self.assertEqual(house_report['pending'], 5)
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
