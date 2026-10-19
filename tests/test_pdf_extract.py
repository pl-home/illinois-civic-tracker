from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import MagicMock,patch
from civic_tracker import pdf_extract as pdf, usage
from civic_tracker.daily import save,load

NOW=datetime(2026,10,19,18,tzinfo=timezone.utc)
PAGES=['Senate Committee Roll Call\nSenate Bill No. 2769\nDo Pass As Amended']
FIELDS={key:{'value':value,'quote':value,'page':1} for key,value in
        [('document_title','Senate Committee Roll Call'),('measure','Senate Bill No. 2769'),('motion','Do Pass As Amended')]}


class PDFTests(unittest.TestCase):
    def test_payload_has_free_parser_and_exact_provider_without_tools(self):
        body=pdf.payload({},b'%PDF-example')
        self.assertEqual(body['plugins'],[{'id':'file-parser','pdf':{'engine':'cloudflare-ai'}}])
        self.assertEqual(body['provider']['only'],['deepinfra/fp8'])
        self.assertFalse(body['provider']['allow_fallbacks'])
        self.assertNotIn('tools',body)
        self.assertEqual(body['max_tokens'],600)

    def test_evidence_requires_literal_quote_page_and_measure(self):
        self.assertEqual(pdf.validate_fields(FIELDS,PAGES),FIELDS)
        for changed in [dict(FIELDS,measure={'value':'HB5','quote':'House Bill 5','page':1}),
                        dict(FIELDS,measure={'value':'2769','quote':'Senate Bill No. 2769','page':2}),
                        dict(FIELDS,measure={'value':'','quote':'','page':1}),
                        dict(FIELDS,measure={'value':' ','quote':'','page':1})]:
            with self.assertRaises(ValueError):pdf.validate_fields(changed,PAGES)

    def setup_trial(self,root):
        (root/'config').mkdir();(root/'data').mkdir();(root/'.local').mkdir()
        save(root/'config/pdf-extraction.json',{'routine_enabled':False})
        save(root/'config/media.json',{'inference':{'daily_cap_usd':'0.02','weekly_cap_usd':'0.20','lifetime_cap_usd':'20'}})
        save(root/'data/dashboard.json',{'members':[]})
        data=b'%PDF-example';digest=hashlib.sha256(data).hexdigest()
        (root/'.local/pdf-source.pdf').write_bytes(data)
        save(root/'.local/pdf-local-pages.json',PAGES)
        save(root/'.local/pdf-owned.json',{'sha256':digest,'owned':True})
        save(root/'data/pdf-extraction-ledger.json',{'entries':[{'status':'reserved','attempted_at':NOW.isoformat(),
            'sha256':digest,'native_text_sha256':hashlib.sha256(json.dumps(PAGES,ensure_ascii=False).encode()).hexdigest(),
            'reserved_usd':'0.005','charged_usd':None}]})

    def test_success_records_exact_cost_in_shared_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_trial(root)
            response=MagicMock();response.read.return_value=json.dumps({'provider':'DeepInfra','model':'qwen/qwen3-32b',
                'id':'example-response','usage':{'cost':0.00014,'prompt_tokens':1000,'completion_tokens':200},
                'choices':[{'message':{'content':json.dumps(FIELDS)}}]}).encode()
            opener=MagicMock();opener.open.return_value.__enter__.return_value=response
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(pdf,'build_opener',return_value=opener):
                pdf.execute(root,NOW)
            self.assertEqual(usage.periods(root,NOW.date())['day']['charged_usd'],'0.00014')
            self.assertEqual(usage.periods(root,NOW.date())['day']['reserved_usd'],'0')
            self.assertTrue(load(root/'data/pdf-extraction-report.json')['fields_verified'])
            self.assertFalse(load(root/'.local/pdf-owned.json')['owned'])

    def test_unknown_charge_holds_budget_and_never_replays(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_trial(root)
            opener=MagicMock();opener.open.side_effect=TimeoutError('private exception details')
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(pdf,'build_opener',return_value=opener):
                pdf.execute(root,NOW)
                with self.assertRaisesRegex(ValueError,'request-not-owned'):pdf.execute(root,NOW)
            self.assertEqual(opener.open.call_count,1)
            self.assertEqual(usage.periods(root,NOW.date())['day']['reserved_usd'],'0.005')
            report=load(root/'data/pdf-extraction-report.json')
            self.assertNotIn('private',json.dumps(report));self.assertNotIn('not-a-real-key',json.dumps(report))

    def test_changed_source_and_next_day_cannot_execute(self):
        for changed in (True,False):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.setup_trial(root)
                if changed:(root/'.local/pdf-source.pdf').write_bytes(b'changed')
                with patch.object(pdf,'build_opener') as opening,self.assertRaises(ValueError):
                    pdf.execute(root,NOW if changed else NOW+timedelta(days=1))
                opening.assert_not_called()

    def test_changed_native_text_and_preclaimed_attempt_cannot_execute(self):
        for tampered in (True,False):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);self.setup_trial(root)
                if tampered:save(root/'.local/pdf-local-pages.json',['unrelated text'])
                else:(root/'.local/pdf-attempt.claim').write_text('already claimed')
                with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(pdf,'build_opener') as opening,self.assertRaises(ValueError):
                    pdf.execute(root,NOW)
                opening.assert_not_called()

    def test_concurrent_execution_has_one_paid_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_trial(root);barrier=Barrier(2)
            original_load=pdf.load
            def synchronized_load(path):
                result=original_load(path)
                if path.name=='pdf-owned.json':barrier.wait(timeout=5)
                return result
            response=MagicMock();response.read.return_value=json.dumps({'provider':'DeepInfra','model':'qwen/qwen3-32b',
                'usage':{'cost':0.00014},'choices':[{'message':{'content':json.dumps(FIELDS)}}]}).encode()
            opener=MagicMock();opener.open.return_value.__enter__.return_value=response
            def execute():
                try:pdf.execute(root,NOW);return 'finished'
                except ValueError:return 'blocked'
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(pdf,'build_opener',return_value=opener),patch.object(pdf,'load',side_effect=synchronized_load),ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda _:execute(),range(2)))
            self.assertEqual(sorted(results),['blocked','finished'])
            self.assertEqual(opener.open.call_count,1)
            self.assertEqual(original_load(root/'data/pdf-extraction-ledger.json')['entries'][0]['charged_usd'],'0.00014')


if __name__=='__main__':unittest.main()
