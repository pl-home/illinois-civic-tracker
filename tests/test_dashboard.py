from datetime import date
import json
from pathlib import Path
import sys
import unittest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from civic_tracker.dashboard_collect import month_after, bound_events, public_url, federal_events
from civic_tracker.dashboard_sources import state_committees, state_schedule, senate_schedule, house_schedule, open_slip_form
from civic_tracker.dashboard import activity_row, meeting_row, render

ROOT = Path(__file__).resolve().parents[1]


class DashboardTests(unittest.TestCase):
    def test_month_window_clamps_month_end_and_year_rollover(self):
        self.assertEqual(month_after(date(2026, 10, 17)), date(2026, 11, 17))
        self.assertEqual(month_after(date(2026, 1, 31)), date(2026, 2, 28))
        self.assertEqual(month_after(date(2026, 12, 20)), date(2027, 1, 20))

    def test_committee_links_are_from_member_pane_only(self):
        body = '<a href="/House/Committees/Members/9">Unrelated nav</a><div id="pane-Committees"><a href="../../Committees/Members/3133">Pensions</a></div>'
        parsed = state_committees(body, 'https://ilga.gov/House/Members/Details/3428')
        self.assertEqual([r['id'] for r in parsed], ['3133'])
        self.assertTrue(parsed[0]['schedule_url'].endswith('/House/Committees/Hearings/3133'))

    def test_empty_calendar_requires_explicit_recognized_empty_state(self):
        self.assertEqual(state_schedule('<div id="scheduled">No Hearings Scheduled at this time.</div>', 'https://ilga.gov/House/Committees/Hearings/3133'), [])
        for html in ['<main>not available</main>', '<div id="scheduled">Unknown response</div>']:
            with self.assertRaises(ValueError):
                state_schedule(html, 'https://ilga.gov/House/Committees/Hearings/3133')

    def test_state_schedule_uses_scheduled_pane_not_past_hearings(self):
        html = '<div id="past"><table><tr><td>1/2/2025 12:00 PM</td><td><a href="/House/hearings/details/3133/1">Details</a></td></tr></table></div><div id="scheduled"><table><tr><td>11/2/2026 12:00 PM</td><td><a href="/House/hearings/details/3133/2">Details</a></td></tr></table></div>'
        rows = state_schedule(html, 'https://ilga.gov/House/Committees/Hearings/3133')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['date_local'], '2026-11-02T12:00')

    def test_senate_no_hearings_sentinel_is_not_a_meeting(self):
        xml = '<css_meetings_scheduled><meeting><date_iso_8601>2026-10-17</date_iso_8601><committee/><matter>No committee hearings scheduled</matter></meeting></css_meetings_scheduled>'
        self.assertEqual(senate_schedule(xml), [])
        with self.assertRaises(ValueError):
            senate_schedule('<html>error</html>')

    def test_house_calendar_requires_the_requested_week(self):
        with self.assertRaisesRegex(ValueError, 'requested week'):
            house_schedule('<p>There are no meetings today</p>', 'https://docs.house.gov/Committee/Calendar/ByWeek.aspx', date(2026, 10, 18))

    def test_cosponsorship_has_no_invented_join_date(self):
        data = {'collected_at': '2026-10-16', 'bills': {'b': {'record_id': 'US-119-HR1', 'title': 'Example',
            'introduced_date': '2026-09-20', 'source_url': 'https://www.congress.gov/bill/119/house-bill/1',
            'relations': [{'member': 'L000585', 'role': 'cosponsored'}]}}, 'votes': {}}
        events, listings = federal_events(data, {'official_id': 'L000585'}, '2026-09-18', '2026-10-17')
        self.assertEqual(events['events'], [])
        self.assertIsNone(listings[0]['role_date'])

    def test_future_events_excluded_older_votes_are_retained_with_labels(self):
        records = [{'id': 'old', 'kind': 'vote', 'date': '2026-05-31'}, {'id': 'future', 'kind': 'vote', 'date': '2026-11-01'}]
        result = bound_events(records, '2026-09-18', '2026-10-17')
        self.assertEqual([r['id'] for r in result['events']], ['old'])
        item = {**records[0], 'title': '<script>attack</script>', 'detail': 'Third Reading', 'source_url': 'https://ilga.gov/example',
                'scope': 'committee', 'choice': 'unknown:NV', 'raw_choice': 'NV'}
        html = BeautifulSoup(activity_row(item, '2026-09-18', '2026-10-17'), 'html.parser')
        self.assertIsNone(html.find('script'))
        self.assertIn('Outside recent window', html.get_text())
        self.assertIn('Unresolved choice', html.get_text())
        self.assertIn('Committee', html.get_text())

    def test_witness_results_or_unverified_form_never_become_submission(self):
        meeting = {'date_local': '2026-11-02T12:00', 'timezone': 'America/New_York', 'committee_name': 'Example',
            'committee_url': 'https://ilga.gov/example', 'source_url': 'https://ilga.gov/example', 'items': [
                {'bill': 'HB1', 'witness_results_url': 'https://ilga.gov/results'},
                {'bill': 'HB2', 'witness_slip_url': 'https://ilga.gov/create', 'submission_verified': False}]}
        html = meeting_row(meeting)
        self.assertEqual(len(BeautifulSoup(html, 'html.parser').select('.slip-links a')), 0)
        self.assertIn('11:00 AM CST', html)
        meeting['items'][1]['submission_verified'] = True
        self.assertIn('HB2 — open witness-slip form', meeting_row(meeting))

    def test_live_snapshot_has_five_members_and_explicit_source_limits(self):
        html, data = render(ROOT)
        page = BeautifulSoup(html, 'html.parser')
        self.assertEqual(len(page.select('.member-card')), 5)
        self.assertEqual({m['id'] for m in data['members']}, {'fritts', 'arellano', 'lahood', 'durbin', 'duckworth'})
        self.assertIn('Automatic refresh is not enabled', page.get_text())
        self.assertNotIn('{{', html)
        for member in data['members']:
            for item in member['events']:
                public_url(item['source_url'])
                self.assertLessEqual(item['date'], data['as_of'])

    def test_source_urls_reject_credentials_and_unexpected_hosts(self):
        for url in ['javascript:alert(1)', 'https://ilga.gov/a?api_key=not-a-real-key', 'https://unrelated.invalid/a']:
            with self.assertRaises(ValueError):
                public_url(url)

    def test_open_form_verification_requires_fields_submit_and_not_closed(self):
        form = '<form action="/WitnessSlip/Create/123">' + ''.join('<input name="'+name+'">' for name in ['FirstName','LastName','Email','Position','Representation']) + '<button type="submit">Create slip</button></form>'
        self.assertTrue(open_slip_form(form, 'https://my.ilga.gov/WitnessSlip/Create/123'))
        self.assertFalse(open_slip_form('<p>Submission closed</p>'+form, 'https://my.ilga.gov/WitnessSlip/Create/123'))
        self.assertFalse(open_slip_form(form.replace('name="Position"', 'name="Other"'), 'https://my.ilga.gov/WitnessSlip/Create/123'))
        self.assertFalse(open_slip_form(form.replace('type="submit"', 'type="submit" disabled'), 'https://my.ilga.gov/WitnessSlip/Create/123'))
        self.assertFalse(open_slip_form(form, 'https://unrelated.invalid/WitnessSlip/Create/123'))


if __name__ == '__main__':
    unittest.main()
