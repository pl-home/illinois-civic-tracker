from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from unittest.mock import patch
from civic_tracker import error_journal as j, model_diagnostics as md
from civic_tracker.privacy import violations

NOW=datetime(2026,10,19,23,tzinfo=timezone.utc)
SECRET='sk-'+'or-v1-NOT_A_REAL_KEY_PRIVATE_VALUE'


class JournalTests(unittest.TestCase):
    def observe(self,journal,when,errors,healthy=False,source='https://ilga.gov/House/Members/Details/3428'):
        journal.observe('daily',source,when.isoformat(),errors,healthy,'1234567890-1',{'file':'data/daily-report.json'},group='Illinois')

    def test_recurrence_dedup_recovery_reopen_and_late_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=j.Journal(tmp,NOW)
            self.observe(journal,NOW-timedelta(days=3),['HTTP_503'])
            self.observe(journal,NOW-timedelta(days=3),['HTTP_503'])
            self.observe(journal,NOW-timedelta(days=2),['HTTP_503'])
            self.assertEqual(journal.data['incidents'][0]['occurrences'],2)
            self.observe(journal,NOW-timedelta(days=1),[],True)
            self.assertEqual(journal.data['incidents'][0]['status'],'resolved')
            self.observe(journal,NOW-timedelta(days=2,hours=1),['HTTP_429'])
            self.assertEqual(len(journal.data['incidents']),1)
            self.assertEqual(journal.data['late_observations'],1)
            self.observe(journal,NOW,['HTTP_503'])
            self.assertEqual(journal.data['incidents'][0]['status'],'open')
            self.assertEqual(journal.data['incidents'][0]['occurrences'],3)
            journal.finish();j.Journal(tmp,NOW)

    def test_distinct_source_failures_and_partial_health_do_not_falsely_recover(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=j.Journal(tmp,NOW)
            self.observe(journal,NOW-timedelta(days=1),['HTTPError'])
            self.observe(journal,NOW-timedelta(days=1),['HTTPError'],source='https://ilga.gov/Senate/Members/Details/3383')
            self.assertEqual(len(journal.data['incidents']),2)
            self.observe(journal,NOW,[],False)
            self.assertTrue(all(i['status']=='open' for i in journal.data['incidents']))

    def test_secrets_queries_userinfo_messages_and_unknown_fields_are_not_serialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=j.Journal(tmp,NOW)
            journal.observe('pdf','https://name:'+SECRET+'@'+'ilga.gov/House/Members/Details/3428?api_key='+SECRET+'#'+SECRET,
                NOW.isoformat(),[SECRET],False,SECRET,{'file':SECRET,'message':SECRET},
                {'error_message':SECRET,'Authorization':SECRET,'model_status':SECRET,'missing_fields':['status',SECRET,{}],
                 'response_id':SECRET,'prompt_tokens':100,'finish_reason':'length','diagnostics_available':True})
            journal.finish();raw=(Path(tmp)/'data/error-journal.json').read_text()
            self.assertNotIn(SECRET,raw);self.assertNotIn('api_key',raw);self.assertNotIn('Authorization',raw)
            incident=journal.data['incidents'][0]
            self.assertEqual(incident['source'],'https://ilga.gov/House/Members/Details/3428')
            self.assertEqual(incident['run_id'],'redacted');self.assertEqual(incident['code'],'unclassified-error')

    def test_persisted_unknown_payload_is_rejected_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=j.Journal(tmp,NOW);self.observe(journal,NOW,['HTTP_503']);journal.finish()
            path=Path(tmp)/'data/error-journal.json';data=json.loads(path.read_text());data['message']=SECRET
            path.write_text(json.dumps(data));before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'journal-schema'):j.Journal(tmp,NOW)
            self.assertEqual(before,path.read_bytes())

    def test_capacity_byte_limit_and_eviction_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=j.Journal(tmp,NOW)
            detail={key:next(iter(values)) for key,values in j.ENUMS.items()}
            detail.update({k:'a'*64 for k in j.HASHES});detail.update({k:100 for k in j.NUMBERS})
            for i in range(400):
                journal.observe('daily','https://ilga.gov/private-path-'+str(i),(NOW-timedelta(minutes=400-i)).isoformat(),
                    ['HTTP_503'],False,'123-1',{},detail)
            size=journal.finish()
            self.assertLessEqual(size,j.MAX_BYTES);self.assertLessEqual(len(journal.data['incidents']),64)
            self.assertLessEqual(len(journal.data['events']),128);self.assertLessEqual(len(journal.data['seen']),128)
            self.assertGreaterEqual(journal.data['evicted_open_incidents'],336)

    def test_retention_uses_recent_recovery_and_keeps_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=j.Journal(tmp,NOW)
            self.observe(journal,NOW-timedelta(days=100),['HTTP_503'])
            self.observe(journal,NOW,[],True)
            journal.finish();self.assertEqual(len(journal.data['incidents']),1)
            self.assertEqual(journal.data['incidents'][0]['status'],'resolved')
            later=j.Journal(tmp,NOW+timedelta(days=91));later.finish();self.assertFalse(later.data['incidents'])

    def test_legacy_pdf_diagnostics_remain_explicitly_not_captured(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=j.Journal(tmp,NOW)
            files={'rollcall':{'cases':[{'case_id':'sample','status':'attempted-invalid','error':'model-abstained',
                'response_id':'gen-1792451795-WQqzLXslfjFfPs2slTHS','completion_tokens':261}]},
                'data/rollcall-evaluation-ledger.json':{'entries':[{'case_id':'sample','attempted_at':NOW.isoformat()}]}}
            j.ingest(journal,files)
            d=journal.data['incidents'][0]['diagnostics']
            self.assertFalse(d['diagnostics_available']);self.assertEqual(d['model_status'],'not-captured')
            self.assertEqual(d['completion_tokens'],261)

    def test_receipt_cache_rollover_does_not_inflate_retained_incident(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal=j.Journal(tmp,NOW)
            self.observe(journal,NOW-timedelta(days=1),['HTTP_503'])
            for i in range(140):
                journal.observe('health','endpoint',(NOW-timedelta(minutes=140-i)).isoformat(),[],True,'123-1',{})
            journal.finish();journal=j.Journal(tmp,NOW)
            self.observe(journal,NOW-timedelta(days=1),['HTTP_503'])
            self.assertEqual(journal.data['incidents'][0]['occurrences'],1)

    def test_malformed_report_does_not_block_workflow_failure_and_recovers(self):
        for malformed in (b'{',b'\xff',b'[]'):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'data/daily-report.json';path.parent.mkdir();path.write_bytes(malformed)
                with patch.dict('os.environ',{'JOURNAL_COLLECTOR':'failure'},clear=True):
                    j.collect(tmp,NOW,'daily','failure')
                self.assertEqual(path.read_bytes(),malformed)
                data=j.Journal(tmp,NOW).data
                self.assertEqual({i['stage'] for i in data['incidents']},{'journal-input','collector'})
                path.write_text('{}')
                j.collect(tmp,NOW+timedelta(minutes=1),'daily','success')
                self.assertTrue(all(i['status']=='resolved' for i in j.Journal(tmp,NOW).data['incidents']))

    def test_finalizer_keeps_backup_and_git_independent_and_updates_source_sha(self):
        root=Path(__file__).resolve().parents[1]
        action=(root/'.github/actions/error-journal/action.yml').read_text()
        self.assertIn('continue-on-error: true',action)
        self.assertEqual(action.count("if: always() && steps.capture.outcome == 'success'"),2)
        self.assertNotIn('steps.backup.outcome',action)
        self.assertIn('git commit --only',action)
        self.assertIn('retention-days: 7',action)
        for name in ('daily','federal','illinois-recovery','media','pdf-extraction','rollcall-evaluation','openrouter-health'):
            text=(root/'.github/workflows'/f'{name}.yml').read_text()
            self.assertIn('uses: ./.github/actions/error-journal',text)
            self.assertIn('if: always()',text)
            if 'source_sha:' in text:self.assertIn('source_sha: ${{ steps.journal.outputs.sha }}',text)


class ModelDiagnosticTests(unittest.TestCase):
    def test_public_git_reference_exemption_is_exact(self):
        sha='abcdef0123'*4
        self.assertEqual(violations(json.dumps({'commit':sha})),[])
        self.assertIn('opaque-token-shape',violations(json.dumps({'message':sha})))
        self.assertIn('credential-shape',violations(json.dumps({'commit':SECRET})))

    def response(self,content,status='length'):
        return {'id':'gen-1792451795-WQqzLXslfjFfPs2slTHS','provider':'DeepInfra','model':'qwen/qwen3-32b',
                'usage':{'prompt_tokens':123,'completion_tokens':1000},'choices':[{'finish_reason':status,'message':{'content':content}}]}

    def test_status_shape_missing_fields_and_finish_reason_without_text(self):
        d=md.completion(self.response(json.dumps({'status':'EXTRACTED','secret-key-name':SECRET})),{'status','tally'})
        self.assertEqual(d['model_status'],'extracted');self.assertFalse(d['status_exact'])
        self.assertEqual(d['missing_fields'],['tally']);self.assertEqual(d['unexpected_field_count'],1)
        self.assertEqual(d['finish_reason'],'length');self.assertNotIn(SECRET,json.dumps(d));self.assertNotIn('secret-key-name',json.dumps(d))
        malformed=md.completion(self.response('```json\n'+SECRET),{'status'})
        self.assertTrue(malformed['code_fence']);self.assertEqual(malformed['json_parse'],'invalid')
        self.assertNotIn(SECRET,json.dumps(malformed))

    def test_unrecognized_status_is_hashed_and_http_messages_are_omitted(self):
        d=md.completion(self.response(json.dumps({'status':SECRET})),{'status'})
        self.assertEqual(d['model_status'],'other');self.assertNotIn(SECRET,json.dumps(d))
        error=HTTPError('https://openrouter.ai/?key='+SECRET,429,SECRET,{},io.BytesIO(json.dumps({
            'error':{'message':SECRET,'metadata':{'error_type':'rate_limit_exceeded','raw':SECRET}}}).encode()))
        d=md.http_error(error)
        self.assertEqual(d['http_status'],429);self.assertEqual(d['provider_error_type'],'rate_limit_exceeded')
        self.assertNotIn(SECRET,json.dumps(d))
