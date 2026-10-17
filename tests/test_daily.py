from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from civic_tracker.daily import due, run, run_federal, save, load
from civic_tracker.daily_state import refresh

ROOT=Path(__file__).resolve().parents[1]

class DailyTests(unittest.TestCase):
    def test_federal_recheck_preserves_other_sources_calendars_and_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root/'config').mkdir(); (root/'data').mkdir()
            save(root/'config/daily.json', {'timezone':'America/Chicago','review_before':'2027-01-03','max_data_bytes':20000000})
            old_health = {'checked_at':'old-full-run','status':'partial','sources':{
                'Illinois':{'status':'ok','checked_at':'old-il'},
                'Calendars':{'status':'ok','checked_at':'old-cal'},
                'Federal':{'status':'partial','errors':[{'source':'Congress.gov API','error':'RuntimeError'}]}}}
            il = {'id':'fritts','jurisdiction':'IL','events':['preserve']}
            us = {'id':'lahood','official_id':'L000585','jurisdiction':'US','meetings':['old-calendar'],
                  'media_reports':['old-news'],'communications':['old-comms'],'calendar_checked_at':'old-cal'}
            snapshot = {'as_of':'2026-10-17','recent_start':'2026-09-17','members':[il,us],
                        'daily_refresh':old_health,'inference_usage':{'actual_usd':0.001}}
            save(root/'data/dashboard.json', snapshot)
            save(root/'data/daily-report.json', old_health)
            save(root/'data/federal-index.json', {'collected_at':'old','bills':{},'votes':{}})
            save(root/'data/collection-state.json', {'last_completed_local_date':'2026-10-17'})
            state_before = (root/'data/collection-state.json').read_bytes()
            archive = {'collected_at':'fresh','bills':{},'votes':{}}
            report = {'status':'ok','checked_at':'fresh','errors':[],'api_attempts':6,'vote_requests':2}
            with patch('civic_tracker.daily.daily_federal.refresh', return_value=(archive, report)), \
                 patch('civic_tracker.daily.collect') as calendars:
                run_federal(root, datetime(2026,10,17,18,tzinfo=timezone.utc))
            calendars.assert_not_called()
            result = load(root/'data/dashboard.json')
            self.assertEqual(result['members'][0], il)
            for key in ('meetings','media_reports','communications','calendar_checked_at'):
                self.assertEqual(result['members'][1][key], us[key])
            self.assertEqual(result['inference_usage'], snapshot['inference_usage'])
            self.assertEqual(result['daily_refresh']['checked_at'], 'old-full-run')
            self.assertEqual(result['daily_refresh']['sources']['Calendars'], old_health['sources']['Calendars'])
            self.assertEqual(result['daily_refresh']['status'], 'ok')
            self.assertEqual((root/'data/collection-state.json').read_bytes(), state_before)
            self.assertEqual(load(root/'data/federal-recheck-report.json')['previous_federal_report'], old_health['sources']['Federal'])

    def test_chicago_schedule_dst_repeat_and_catch_up(self):
        plan={'enabled':True,'timezone':'America/Chicago','start_hour':1,'catch_up_before_hour':6}
        for value in ['2026-07-01T06:00:00+00:00','2026-12-01T07:00:00+00:00','2026-11-01T06:00:00+00:00','2026-11-01T07:00:00+00:00']:
            now=datetime.fromisoformat(value)
            self.assertTrue(due(plan,{},now))
            self.assertFalse(due(plan,{'last_completed_local_date':now.date().isoformat()},now))
        self.assertFalse(due(plan,{},datetime.fromisoformat('2026-12-01T06:00:00+00:00')))
        self.assertTrue(due(plan,{},datetime.fromisoformat('2026-07-01T07:45:00+00:00')))

    def test_csv_correction_replaces_totals_and_retires_previous_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config').mkdir();(root/'.local').mkdir()
            save(root/'config/project.json',{'ga':104,'subjects':[{'id':'fritts','official_member_id':'3428'}]})
            save(root/'config/daily.json',{'floor_csv_baseline_through':'2026-05-31'})
            row={'GA':'104','Chamber':'House','Vote Date':'2026-10-16','subject':'fritts','Legislation':'HB1','Vote Type':'Third Reading','Vote':'Yea','roll':['104','House','Session','HB1','Third Reading','2026-10-16'],'nay_count':3}
            old={'record_id':'old-corrected-date','verification':'official-csv','date':'2026-10-15','choices':[{'member_id':'3428','choice':'no'}],'evidence':{'sha256':'old'},'totals':{'no':2}}
            parsed={'row_count':2000,'latest_vote_date':'2026-10-16','subjects':[row]}
            response={'status':200,'body':b'synthetic','headers':{},'url':'https://ilga.gov/documents/reports/static/104MemberVotes.csv'}
            with patch('civic_tracker.daily_state.Client') as client, patch('civic_tracker.daily_state.read_csv',return_value=parsed), patch('civic_tracker.daily_state.listing',return_value={}):
                client.return_value.get.return_value=response
                result,state,report=refresh(root,{'bills':{},'votes':{'old-corrected-date':old}}, {'floor_csv':{'latest_vote_date':'2026-10-16'}},datetime(2026,10,17,tzinfo=timezone.utc))
            self.assertEqual(report['status'],'ok')
            self.assertNotIn('old-corrected-date',result['votes'])
            vote=next(iter(result['votes'].values()))
            self.assertEqual(vote['totals']['no'],3)
            self.assertEqual(vote['evidence']['sha256'],hashlib.sha256(b'synthetic').hexdigest())
            self.assertEqual(vote['choices'][0]['choice'],'yes')
            self.assertIn(old,state['csv_superseded'].values())
            # A bad empty export must not poison the persisted watermark.
            parsed.update(row_count=0,latest_vote_date='',subjects=[])
            with patch('civic_tracker.daily_state.Client') as client, patch('civic_tracker.daily_state.read_csv',return_value=parsed), patch('civic_tracker.daily_state.listing',return_value={}):
                client.return_value.get.return_value=response
                _,bad_state,bad_report=refresh(root,result,state,datetime(2026,10,18,tzinfo=timezone.utc))
            self.assertEqual(bad_report['status'],'partial')
            self.assertEqual(bad_state['floor_csv']['latest_vote_date'],'2026-10-16')

    def test_partial_calendar_keeps_prior_meeting_but_not_open_slip_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config').mkdir();(root/'data').mkdir()
            save(root/'config/daily.json',{'timezone':'America/Chicago','review_before':'2027-01-03','max_data_bytes':20000000})
            save(root/'data/collection-state.json',{})
            for name in ('illinois-index.json','federal-index.json'):save(root/'data'/name,{'bills':{},'votes':{}})
            meeting={'source_url':'https://ilga.gov/House/hearings/details/1/2','committee_url':'https://ilga.gov/House/Committees/Members/1','date_local':'2026-10-25T12:00','items':[{'bill':'HB1','submission_verified':True}]}
            member={'id':'fritts','jurisdiction':'IL','calendar_health':'checked','meetings':[meeting],'committees':[{'url':meeting['committee_url']} ]}
            baseline={'members':[member],'as_of':'2026-10-16','calendar_end':'2026-11-17'}
            save(root/'data/dashboard.json',baseline)
            def calendar(*args):
                save(root/'data/dashboard.json',{**baseline,'errors':[{'source':'committee','error':'Unavailable'}],'members':[{**member,'calendar_health':'partial_or_failed','meetings':[],'committees':[{'url':meeting['committee_url'],'health':'failed'}]}]})
            with patch('civic_tracker.daily.daily_state.refresh',return_value=({'bills':{},'votes':{}},{},{'status':'ok','errors':[]})), patch('civic_tracker.daily.daily_federal.refresh',return_value=({'bills':{},'votes':{}},{'status':'ok','errors':[]})), patch('civic_tracker.daily.collect',side_effect=calendar):
                run(root,datetime(2026,10,17,12,tzinfo=timezone.utc))
            result=json.loads((root/'data/dashboard.json').read_text())
            retained=result['members'][0]['meetings'][0]
            self.assertTrue(retained['retained_after_failure'])
            self.assertFalse(retained['items'][0]['submission_verified'])
            self.assertEqual(result['daily_refresh']['status'],'partial')

if __name__=='__main__':unittest.main()
