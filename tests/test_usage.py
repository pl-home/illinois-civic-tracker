from datetime import datetime, timezone
from pathlib import Path
import json
import tempfile
import unittest
from bs4 import BeautifulSoup
from civic_tracker import usage, media, media_inference as mi
from civic_tracker.dashboard import usage_panel
from civic_tracker.inference_eval import EvaluationError


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        media.save(self.root/'config/media.json',{'inference':{'daily_cap_usd':'0.02','weekly_cap_usd':'0.20','lifetime_cap_usd':'20'}})

    def tearDown(self):self.temp.cleanup()

    def test_week_boundary_and_dst_use_chicago_date_and_entry_attempt(self):
        media.save(self.root/'data/inference-evaluation-ledger.json',{'experiments':[{'reserved_at':'2026-10-25T12:00:00+00:00','entries':[
            {'attempted_at':'2026-11-01T06:30:00+00:00','charged_usd':'0.001','reserved_usd':'0.02'},
            {'attempted_at':'2026-11-01T07:30:00+00:00','charged_usd':'0.002','reserved_usd':'0.02'}]}]})
        sunday=usage.summary(self.root,datetime.fromisoformat('2026-11-02T05:30:00+00:00'))
        self.assertEqual(sunday['local_date'],'2026-11-01')
        self.assertEqual(sunday['week_start'],'2026-10-26')
        self.assertEqual(sunday['week_end'],'2026-11-01')
        self.assertEqual(sunday['day']['charged_usd'],'0.003')
        monday=usage.summary(self.root,datetime.fromisoformat('2026-11-02T06:00:00+00:00'))
        self.assertEqual(monday['week_start'],'2026-11-02')
        self.assertEqual(monday['week']['charged_usd'],'0')
        self.assertEqual(monday['lifetime']['charged_usd'],'0.003')

    def test_reservations_are_separate_from_charges_and_not_double_counted(self):
        media.save(self.root/'data/media-inference-ledger.json',{'batches':[
            {'day':'2026-10-17','charged_usd':'0.0002','reserved_usd':'0.002'},
            {'day':'2026-10-17','charged_usd':None,'reserved_usd':'0.002'},
            {'day':'2026-10-17','charged_usd':'0','reserved_usd':'0.002'}]})
        report=usage.summary(self.root,datetime(2026,10,17,18,tzinfo=timezone.utc))
        self.assertEqual(report['week']['charged_usd'],'0.0002')
        self.assertEqual(report['week']['reserved_usd'],'0.002')
        self.assertEqual(report['week']['liability_usd'],'0.0022')
        self.assertEqual(report['week']['unsettled_requests'],1)
        self.assertEqual(report['day']['remaining_usd'],'0.0178')

    def test_undated_liability_is_conservative_and_quarantine_has_no_charge(self):
        media.save(self.root/'data/inference-evaluation-ledger.json',{'experiments':[{'entries':[
            {'charged_usd':None,'reserved_usd':'0.002'},
            {'status':'quarantined-deterministically','charged_usd':None,'reserved_usd':'0.02'}]}]})
        report=usage.summary(self.root,datetime(2026,10,17,18,tzinfo=timezone.utc))
        self.assertEqual(report['week']['liability_usd'],'0.002')
        self.assertEqual(report['day']['undated_entries'],1)
        self.assertIn('Some entry dates are unknown',usage_panel({'inference_usage':report}))

    def test_weekly_guard_uses_prior_days_and_all_new_reservations(self):
        config={'enabled':True,'model':mi.MODEL,'provider':mi.PROVIDER,'daily_cap_usd':'0.02','weekly_cap_usd':'0.20','lifetime_cap_usd':'20','per_request_reserved_usd':'0.002','max_daily_calls':4,'prompt_version':mi.PROMPT_VERSION}
        media.save(self.root/'config/media.json',{'inference':config})
        media.save(self.root/'data/inference-evaluation-ledger.json',{'experiments':[{'reserved_at':'2026-10-16T12:00:00+00:00','entries':[{'charged_usd':'0.198','reserved_usd':'0.20'}]}]})
        cases=[{'id':f'{i:08x}','member_id':'member','member_name':'Member','title':'Member discusses policy','snippet':'Public report'} for i in range(16)]
        report=mi.prepare(self.root,cases,datetime(2026,10,17,18,tzinfo=timezone.utc))
        self.assertEqual(report['costs']['reserved_usd'],'0.002')
        self.assertEqual(len(report['deferred_ids']),8)
        self.assertEqual(mi._weekly_liability(self.root,media.load(self.root/'data/media-inference-ledger.json'),'2026-10-17'),mi.WEEKLY_CAP)

    def test_usage_refresh_is_read_only_for_financial_ledgers_and_panel_shows_limits(self):
        ledger=self.root/'data/media-inference-ledger.json'
        media.save(ledger,{'batches':[]});before=ledger.read_bytes()
        media.save(self.root/'data/dashboard.json',{'members':[]})
        report=usage.apply(self.root,datetime(2026,10,17,18,tzinfo=timezone.utc))
        self.assertEqual(ledger.read_bytes(),before)
        soup=BeautifulSoup(usage_panel({'inference_usage':report}),'html.parser')
        self.assertEqual([m['max'] for m in soup.select('meter')],['0.20','0.02'])
        self.assertIn('Monday–Sunday',soup.get_text())
        self.assertIn('unrelated OpenRouter account use',soup.get_text())
        self.assertEqual(media.load(self.root/'data/inference-usage.json')['week_start'],'2026-10-12')

    def test_missing_or_invalid_unsettled_cost_is_never_silently_zero(self):
        path=self.root/'data/inference-evaluation-ledger.json'
        media.save(path,{'experiments':[{'entries':[{'charged_usd':None}]}]})
        with self.assertRaises(KeyError):usage.summary(self.root,datetime(2026,10,17,tzinfo=timezone.utc))
        for amount in ('NaN','-1',True):
            media.save(path,{'experiments':[{'entries':[{'charged_usd':None,'reserved_usd':amount}]}]})
            with self.subTest(amount=amount),self.assertRaises(EvaluationError):
                usage.summary(self.root,datetime(2026,10,17,tzinfo=timezone.utc))
        media.save(path,{'experiments':[{'entries':[{'charged_usd':'NaN','reserved_usd':'0.002'}]}]})
        with self.assertRaises(EvaluationError):usage.summary(self.root,datetime(2026,10,17,tzinfo=timezone.utc))


if __name__=='__main__':unittest.main()
