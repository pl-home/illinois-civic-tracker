"""Stage B acceptance: official HTML fixtures, state transitions and safe views."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from unittest.mock import patch
from bs4 import BeautifulSoup
from civic_tracker.hearings import parse_hearing_details, hearing_date
from civic_tracker.hearing_changes import identity, agenda, delta, explicit_status, slip_current, retain_failed, clear_slips
from civic_tracker.hearing_collect import state_meetings
from civic_tracker.change_sources import calendars
from civic_tracker.changes import reconcile, empty, public_events, packed, validate_fact
from civic_tracker.hearing_view import sections, meeting_row
from civic_tracker.dashboard_sources import senate_schedule, state_schedule

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://ilga.gov/House/hearings/details/3062/23132'
NOW = '2026-10-19T15:00:00+00:00'
LATER = '2026-10-20T15:00:00+00:00'
COMMITTEE = {'id': '3062', 'chamber': 'House', 'name': 'Judiciary - Civil', 'health': 'checked',
    'checked_at': NOW, 'role': 'Republican Spokesperson',
    'url': 'https://ilga.gov/House/Committees/Members/3062',
    'schedule_url': 'https://ilga.gov/House/Committees/Hearings/3062'}
PROOF = {'url': URL, 'sha256': 'a'*64, 'checked_at': NOW}
HEADERS = '<tr>'+''.join('<th>'+s+'</th>' for s in ['Bill #','Motion','Vote Motion','Vote Total','Vote Result','Witness Slip Results'])+'</tr>'


def bill_row(bill='HB24', amendment='SFA2', result='', motion='Concur'):
    import re
    typ, number = re.fullmatch(r'([A-Z]+)(\d+)', bill).groups()
    return f'<tr><td><a href="/legislation/BillStatus?DocTypeID={typ}&amp;DocNum={number}&amp;GAID=18&amp;SessionID=114">{bill}'+(f' ({amendment})' if amendment else '')+f'</a></td><td>{motion}</td><td>Do Pass</td><td></td><td>{result}</td><td><a title="View Witness Slips" href="/results">Results</a></td></tr>'


def html(rows=None, status=None, when='10/25/2026 8:00 AM', table=True, room='Room 114'):
    field = f'<tr><td><span>Status:</span> {status}</td></tr>' if status else ''
    fields = f'<table><tr><td><span>Date:</span> {when}</td></tr><tr><td><span>Location:</span> {room}</td></tr>{field}</table>'
    return '<main><h2>House Judiciary - Civil Hearing Details - 104th General Assembly</h2>'+fields+('<table>'+HEADERS+(bill_row() if rows is None else rows)+'</table>' if table else '')+'</main>'


def meeting(**extra):
    result = {**parse_hearing_details(html(), URL), 'committee_url': COMMITTEE['url'], 'committee_name': COMMITTEE['name'],
        'hearing_key': identity({'source_url': URL}, 'IL'), 'evidence': PROOF,
        'timezone': 'America/Chicago', 'status': 'scheduled', 'status_basis': 'scheduled-listing'}
    result.update(extra)
    return result


def snapshot(meetings=None, checked=NOW, health='checked'):
    return {'as_of': '2026-10-19', 'calendar_end': '2026-11-19', 'generated_at': checked,
        'calendar_sources': [PROOF], 'members': [{'id': 'fritts','name': 'Bradley Fritts', 'jurisdiction': 'IL',
            'calendar_checked_at': checked, 'calendar_health': health,
            'committees': [{**COMMITTEE, 'checked_at': checked}], 'meetings': meetings if meetings is not None else [meeting()]}]}


class HearingChangeTests(unittest.TestCase):
    def baseline(self): return reconcile(empty(), list(calendars(snapshot())), NOW)[0]

    def next(self, row):
        row = {**row, 'evidence': {**PROOF, 'checked_at': LATER, 'sha256': 'b'*64}}
        return reconcile(self.baseline(), list(calendars(snapshot([row], LATER))), LATER)

    def test_quiet_baseline_and_unchanged_replay(self):
        initial = self.baseline()
        self.assertEqual(initial['events'], [])
        again, report = reconcile(initial, list(calendars(snapshot(checked=LATER))), LATER)
        self.assertEqual(again['events'], [])
        self.assertEqual(report['status'], 'ok')

    def test_amendment_identity_and_reordering_do_not_collapse_or_alert(self):
        rows = [parse_hearing_details(html(rows=bill_row('HB24','SFA1')+bill_row('HB24','SFA2')),URL)['items']]
        items = rows[0]
        self.assertEqual(len(agenda(items,'IL')),2)
        self.assertEqual(agenda(items,'IL'),agenda(items[::-1],'IL'))
        copy = deepcopy(items);copy[0]['amendment']='Senate Floor Amendment No. 1'
        self.assertEqual(agenda(items,'IL'),agenda(copy,'IL'))

    def test_agenda_add_remove_and_context_changes_are_explicit(self):
        revised = meeting(items=parse_hearing_details(html(rows=bill_row('HB25','SFA1')),URL)['items'])
        ledger, _ = self.next(revised)
        changes = ledger['events'][-1]['hearing_changes']
        self.assertIn({'type':'agenda-added','item':'HB25:SFA1'},changes)
        self.assertIn({'type':'agenda-removed','item':'HB24:SFA2'},changes)
        self.assertFalse(any(c['type']=='bill-postponed' for c in changes))

    def test_reorder_and_cosmetic_whitespace_are_quiet(self):
        revised = meeting()
        revised['items'][0]['motion'] = '  Concur  '
        ledger, report = self.next(revised)
        self.assertEqual(ledger['events'], [])

    def test_reschedule_keeps_identity_and_does_not_assert_postponement(self):
        ledger, _ = self.next(meeting(date_local='2026-10-26T09:00',location='Room 200'))
        event = ledger['events'][-1]
        self.assertEqual(event['fact']['hearing_key'],meeting()['hearing_key'])
        self.assertEqual({c['type'] for c in event['hearing_changes']},{'time-changed','location-changed'})
        self.assertEqual(event['fact']['status'],'scheduled')

    def test_explicit_cancellation_without_agenda_does_not_remove_all_bills(self):
        parsed = parse_hearing_details(html(status='This hearing has been canceled',table=False),URL)
        ledger, report = self.next(meeting(**parsed))
        self.assertEqual(report['status'],'ok')
        event=ledger['events'][-1]
        self.assertEqual(event['fact']['status'],'canceled')
        self.assertFalse(any(c['type']=='agenda-removed' for c in event['hearing_changes']))

    def test_postponed_hearing_date_can_be_unknown(self):
        parsed = parse_hearing_details(html(status='Postponed until further notice',when='TBA',table=False),URL)
        ledger, report=self.next(meeting(**parsed))
        self.assertEqual(report['status'],'ok')
        self.assertIsNone(ledger['events'][-1]['fact']['occurred_at'])
        self.assertIn('postponed',ledger['events'][-1]['inclusion_reason'])

    def test_bill_postponement_is_not_meeting_postponement(self):
        items=parse_hearing_details(html(rows=bill_row(result='Postponed')),URL)['items']
        ledger,_=self.next(meeting(items=items))
        event=ledger['events'][-1]
        self.assertEqual(event['fact']['status'],'scheduled')
        self.assertIn({'type':'bill-postponed','item':'HB24:SFA2'},event['hearing_changes'])

    def test_proposed_postponement_and_negative_status_are_not_assertions(self):
        for value in ['Not canceled','Cancellation policy','Motion to postpone','Bill postponed','No postponements']:
            self.assertIsNone(explicit_status(value))
        items=parse_hearing_details(html(rows=bill_row(motion='Motion to postpone',result='Motion failed')),URL)['items']
        ledger,_=self.next(meeting(items=items))
        self.assertNotIn('Bill explicitly postponed',ledger['events'][-1]['inclusion_reason'])

    def test_date_only_and_upon_adjournment_do_not_invent_midnight(self):
        for raw in ['10/25/2026','10/25/2026 Upon adjournment']:
            when, precision, note=hearing_date(raw)
            self.assertEqual((when,precision),('2026-10-25','day'))
            row=meeting(date_local=when,time_note=note)
            self.assertNotIn('12:00',meeting_row(row))

    def test_wrong_session_heading_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'session'):parse_hearing_details(html().replace('104th','105th'),URL)

    def test_explicit_canceled_notice_can_omit_date_and_agenda(self):
        source=html(status='Canceled',table=False).replace('<tr><td><span>Date:</span> 10/25/2026 8:00 AM</td></tr>','')
        parsed=parse_hearing_details(source,URL)
        self.assertEqual(parsed['status'],'canceled')
        self.assertIsNone(parsed['date_local'])
        self.assertEqual(parsed['agenda_coverage'],'not-published')

    def test_claimed_cancellation_without_a_matching_assertion_is_quarantined(self):
        bad=meeting(status='canceled',status_basis='explicit-notice',status_notice='Not canceled')
        ledger,report=self.next(bad)
        self.assertEqual(report['status'],'partial')
        self.assertEqual(ledger['facts'],self.baseline()['facts'])

    def test_per_committee_failure_leaves_healthy_sibling_eligible(self):
        snap=snapshot(health='partial_or_failed')
        self.assertTrue(list(calendars(snap))[0]['complete'])
        snap['members'][0]['committees'][0]['health']='partial'
        self.assertFalse(list(calendars(snap))[0]['complete'])

    def test_wrong_bill_session_keeps_last_good_agenda(self):
        revised=meeting();revised['items'][0]['official_url']=revised['items'][0]['official_url'].replace('SessionID=114','SessionID=115')
        ledger,report=self.next(revised)
        self.assertEqual(report['status'],'partial')
        self.assertEqual(ledger['facts'],self.baseline()['facts'])

    def test_same_senate_feed_has_distinct_subject_identities_and_collisions_fail(self):
        xml='<css_meetings_scheduled>'+''.join('<meeting><date_iso_8601>2026-10-25</date_iso_8601><committee>Judiciary</committee><cmte_code>SSJU</cmte_code><time>10:00</time><matter>'+s+'</matter></meeting>' for s in ['One topic','Another topic'])+'</css_meetings_scheduled>'
        events=senate_schedule(xml)
        self.assertNotEqual(identity(events[0],'US'),identity(events[1],'US'))
        duplicate=senate_schedule(xml.replace('Another topic','One topic'))
        with self.assertRaisesRegex(ValueError,'ambiguous'):identity(duplicate[0],'US')

    def test_senate_room_and_time_change_do_not_change_fallback_identity(self):
        row={'source_url':'https://www.senate.gov/general/committee_schedules/hearings.xml','committee_code':'SSJU','description':'Subject one','date_local':'2026-10-25T10:00'}
        self.assertEqual(identity(row,'US'),identity({**row,'date_local':'2026-10-26T11:00','location':'New room'},'US'))

    def test_missing_schedule_row_is_rechecked_and_unconfirmed(self):
        old=meeting();fetch=Mock(return_value=(html(),PROOF));committee=deepcopy(COMMITTEE)
        rows=state_meetings(committee,'<div id="scheduled">No Hearings Scheduled at this time.</div>',PROOF,[old],date(2026,10,19),date(2026,11,19),fetch,json.loads((ROOT/'config/hearings.json').read_text()),{},[])
        self.assertEqual(rows[0]['status'],'unconfirmed')
        self.assertFalse(rows[0]['listing_present'])
        fetch.assert_called_once()

    def test_missing_listing_can_find_explicit_cancellation_on_same_detail(self):
        old=meeting();fetch=Mock(return_value=(html(status='Canceled',table=False),PROOF))
        rows=state_meetings(deepcopy(COMMITTEE),'<div id="scheduled">No Hearings Scheduled at this time.</div>',PROOF,[old],date(2026,10,19),date(2026,11,19),fetch,json.loads((ROOT/'config/hearings.json').read_text()),{},[])
        self.assertEqual(rows[0]['status'],'canceled')
        self.assertEqual(rows[0]['hearing_key'],old['hearing_key'])

    def test_failed_detail_and_bound_retain_old_values_without_slips(self):
        old=meeting();old['items'][0]['submission_verified']=True
        options=json.loads((ROOT/'config/hearings.json').read_text())
        for opts,fetch in [(options,Mock(side_effect=RuntimeError)),({**options,'max_missing_hearing_rechecks':0},Mock())]:
            committee=deepcopy(COMMITTEE);errors=[]
            rows=state_meetings(committee,'<div id="scheduled">No Hearings Scheduled at this time.</div>',PROOF,[old],date(2026,10,19),date(2026,11,19),fetch,opts,{},errors)
            self.assertTrue(rows[0]['retained_after_failure'])
            self.assertFalse(rows[0]['items'][0]['submission_verified'])
            self.assertEqual(committee['health'],'partial')

    def test_full_failure_clears_even_earlier_valid_form_claims(self):
        snap=snapshot();snap['members'][0]['meetings'][0]['items'][0]['submission_verified']=True
        clear_slips(snap)
        self.assertFalse(snap['members'][0]['meetings'][0]['items'][0]['submission_verified'])

    def test_form_expiry_cancellation_retained_and_missing_timestamp_are_closed(self):
        item={'submission_verified':True,'submission_checked_at':NOW}
        self.assertTrue(slip_current(item,meeting(),NOW))
        for row in [meeting(status='canceled'),meeting(retained_after_failure=True),meeting(status='unconfirmed')]:
            self.assertFalse(slip_current(item,row,NOW))
        self.assertFalse(slip_current(item,meeting(),'2026-10-21T15:00:00+00:00'))
        self.assertFalse(slip_current({'submission_verified':True},meeting(),NOW))

    def test_navigation_role_agenda_evidence_and_history_render_from_accepted_facts(self):
        revised=meeting(items=parse_hearing_details(html(rows=bill_row()+bill_row('HB25','SFA1')),URL)['items'])
        ledger,report=self.next(revised)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir();(root/'config').mkdir()
            for name,value in [('change-ledger.json',ledger),('change-quality-report.json',report)]:
                (root/'data'/name).write_text(packed(value))
            (root/'config/hearings.json').write_bytes((ROOT/'config/hearings.json').read_bytes())
            nav,cards=sections(root,snapshot([revised],LATER))
        doc=BeautifulSoup(nav+cards['fritts'],'html.parser')
        self.assertIsNotNone(doc.select_one('#hearing-day'))
        self.assertIsNotNone(doc.select_one('#hearing-committee'))
        self.assertIn('Republican Spokesperson',doc.get_text())
        self.assertIn('Agenda added',doc.get_text())
        self.assertIn('HB25',doc.get_text())
        self.assertIsNotNone(doc.find('a',href=URL))

    def test_reviewed_live_historical_html_examples_match_both_members_committees(self):
        examples=json.loads((ROOT/'tests/fixtures/hearing-stage-b-reviewed.json').read_text())
        self.assertEqual({e['member_id'] for e in examples},{'fritts','arellano'})
        for example in examples:
            parsed=parse_hearing_details(example['html'],example['source_url'])
            self.assertEqual(len(parsed['items']),example['expected_agenda_rows'])
            self.assertTrue(agenda(parsed['items'],'IL'))

    def test_failed_detail_attempts_are_bounded_and_not_refetched(self):
        rows=''.join(f'<tr><td>10/25/2026 8:00 AM</td><td><a href="/House/hearings/details/3062/{i}">Details</a></td></tr>' for i in range(100,120))
        body='<div id="scheduled"><table>'+rows+'</table></div>'
        options=json.loads((ROOT/'config/hearings.json').read_text());options['max_detail_pages_per_run']=2
        fetch=Mock(side_effect=RuntimeError);work={}
        for _ in range(2):
            state_meetings(deepcopy(COMMITTEE),body,PROOF,[],date(2026,10,19),date(2026,11,19),fetch,options,work,[])
        self.assertEqual(fetch.call_count,2)
        self.assertEqual(len(work['details']),2)

    def test_known_hearing_rescheduled_beyond_month_is_still_rechecked(self):
        body='<div id="scheduled"><table><tr><td>12/1/2026 8:00 AM</td><td><a href="'+URL+'">Details</a></td></tr></table></div>'
        old=meeting();fetch=Mock(return_value=(html(when='12/1/2026 8:00 AM'),PROOF))
        rows=state_meetings(deepcopy(COMMITTEE),body,PROOF,[old],date(2026,10,19),date(2026,11,19),fetch,json.loads((ROOT/'config/hearings.json').read_text()),{},[])
        self.assertEqual(rows[0]['date_local'],'2026-12-01T08:00')
        self.assertTrue(rows[0]['outside_display_window'])
        fetch.assert_called_once()

    def test_senate_recurring_subject_across_feeds_does_not_claim_reschedule(self):
        row={'source_url':'https://www.senate.gov/general/committee_schedules/hearings.xml','committee_code':'SSJU',
            'description':'Business meeting','date_local':'2026-11-01T10:00','timezone':'America/New_York',
            'committee_name':'Judiciary','committee_url':'https://www.judiciary.senate.gov',
            'evidence':{**PROOF,'url':'https://www.senate.gov/general/committee_schedules/hearings.xml'},'items':[]}
        member={'id':'durbin','name':'Dick Durbin','jurisdiction':'US','calendar_health':'published_feed_checked',
            'calendar_checked_at':NOW,'committees':[{'url':row['committee_url'],'name':'Judiciary'}],'meetings':[row]}
        before={'members':[member],'calendar_sources':[]}
        ledger,report=reconcile(empty(),list(calendars(before)),NOW)
        self.assertEqual(report['status'],'ok')
        after=deepcopy(before);after['members'][0]['meetings'][0]['date_local']='2026-11-08T10:00'
        after['members'][0]['calendar_checked_at']=LATER
        observed=list(calendars(after,ledger))
        result,report=reconcile(ledger,observed,LATER)
        self.assertEqual(report['status'],'partial')
        self.assertEqual(result['facts'],ledger['facts'])
        self.assertEqual(result['events'],[])
        self.assertIn('ambiguous-hearing-identity',report['errors'][0]['codes'])

    def test_hearing_ui_rejects_fact_tampering_even_with_plausible_evidence(self):
        ledger=self.baseline()
        for stored in ledger['facts'].values():stored['fact']['location']='Invented room'
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir();(root/'config').mkdir()
            (root/'data/change-ledger.json').write_text(packed(ledger))
            (root/'config/hearings.json').write_bytes((ROOT/'config/hearings.json').read_bytes())
            nav,cards=sections(root,snapshot())
        self.assertEqual(cards,{})
        self.assertNotIn('Invented room',nav)

    def test_public_calendar_is_bounded_and_navigation_targets_exist(self):
        meetings=[]
        for number in range(50):
            row=meeting();row['source_url']=URL.rsplit('/',1)[0]+'/'+str(24000+number)
            row['hearing_key']=identity(row,'IL')
            row['committee_name']='Committee & '+('&'*300)
            row['items'][0]['motion']='&'*900
            meetings.append(row)
        snap=snapshot(meetings)
        ledger,report=reconcile(empty(),list(calendars(snap)),NOW)
        self.assertEqual(report['status'],'ok')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'data').mkdir();(root/'config').mkdir()
            (root/'data/change-ledger.json').write_text(packed(ledger))
            (root/'config/hearings.json').write_bytes((ROOT/'config/hearings.json').read_bytes())
            nav,cards=sections(root,snap)
        combined=nav+''.join(cards.values())
        self.assertLessEqual(len(combined.encode()),45000)
        page=BeautifulSoup(combined,'html.parser')
        self.assertLess(len(page.select('.hearing-nav-row')),50)
        for link in page.select('.hearing-nav-row a'):
            self.assertIsNotNone(page.find(id=link['href'][1:]))

    def test_calendar_only_refresh_preserves_protected_state_and_clears_failed_slips(self):
        from datetime import datetime
        from civic_tracker.calendar_refresh import run
        from civic_tracker.daily import save,load
        for fails in [False,True]:
            with self.subTest(failed_source=fails),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);(root/'data').mkdir();(root/'config').mkdir()
                save(root/'config/daily.json',{'timezone':'America/Chicago','review_before':'2027-01-03','max_data_bytes':20000000})
                old=snapshot();member=old['members'][0]
                member.update(events=[{'id':'prior-activity'}],media_reports=[{'id':'prior-news'}],activity_coverage='Prior verified facts')
                member['meetings'][0]['items'][0]['submission_verified']=True
                health={'checked_at':NOW,'status':'ok','sources':{'Illinois':{'status':'ok','checked_at':NOW},'Federal':{'status':'ok','checked_at':NOW},'Calendars':{'status':'ok','checked_at':NOW}}}
                old['daily_refresh']=health;old['inference_usage']={'charged_usd':'0.001'}
                save(root/'data/dashboard.json',old);save(root/'data/daily-report.json',health)
                protected={}
                for name in ['media-inference-ledger.json','pdf-extraction-ledger.json','collection-state.json','illinois-index.json','federal-index.json']:
                    save(root/'data'/name,{'protected':True});protected[name]=(root/'data'/name).read_bytes()
                def collect(*args):
                    if fails:raise RuntimeError('Synthetic source failure')
                    fresh=deepcopy(old);fresh.update(errors=[],generated_at=LATER)
                    fresh['members'][0]['events']=[{'id':'must-not-replace-activity'}]
                    save(root/'data/dashboard.json',fresh)
                with patch('civic_tracker.calendar_refresh.collect',side_effect=collect):run(root,datetime.fromisoformat(LATER))
                actual=load(root/'data/dashboard.json')
                self.assertEqual(actual['members'][0]['events'],member['events'])
                self.assertEqual(actual['members'][0]['media_reports'],member['media_reports'])
                self.assertEqual(actual['inference_usage'],old['inference_usage'])
                for key in ('Illinois','Federal'):self.assertEqual(actual['daily_refresh']['sources'][key],health['sources'][key])
                self.assertEqual(protected,{name:(root/'data'/name).read_bytes() for name in protected})
                if fails:self.assertFalse(actual['members'][0]['meetings'][0]['items'][0]['submission_verified'])


if __name__=='__main__':unittest.main()
