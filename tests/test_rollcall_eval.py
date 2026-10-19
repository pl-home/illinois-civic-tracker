from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock,patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from civic_tracker import rollcall_eval as r, usage
from civic_tracker.daily import save,load

NOW=datetime(2026,10,19,18,tzinfo=timezone.utc)


def sample():
    rows=[('Y Neighbor, One',40,100),('N Fritts, Bradley',370,100),
          ('P Person, Two',40,120),('NV Person, Three',370,120),('Y Person, Four',40,140)]
    words=[]
    for line,left,top in rows:
        for word in line.split():
            words.append({'text':word,'x0':left,'x1':left+len(word)*6,'top':top,'bottom':top+10});left+=len(word)*6+6
    native={'pages':['Labor & Commerce\nHouse Bill No. 1056 - House Floor Amendment No. 2\nRecommends Be Adopted\n'
        '2 YEAS 1 NAYS 1 PRESENT 1 NOT VOTING\nY Neighbor, One N Fritts, Bradley\nP Person, Two NV Person, Three\nY Person, Four'],
        'words':[words]}
    case={'id':'sample','member_id':'fritts','member_name':'Bradley Fritts','source_url':'https://ilga.gov/public.pdf','sha256':'a'*64,
          'expected':{'committee':'Labor & Commerce','measure':'House Bill No. 1056 - House Floor Amendment No. 2',
          'motion':'Recommends Be Adopted','raw_vote':'N','tally':{'yea':2,'nay':1,'present':1,'not_voting':1}}}
    return case,native


def setup(root):
    (root/'config').mkdir();(root/'data').mkdir();r.folder(root).mkdir(parents=True)
    case,native=sample();cases=[];entries=[]
    for i in range(6):
        c=deepcopy(case);c['id']='sample-'+str(i);cases.append(c)
        save(r.folder(root)/(c['id']+'.json'),native)
        entries.append({'case_id':c['id'],'attempted_at':NOW.isoformat(),'status':'reserved','reserved_usd':str(r.HOLD),
                        'charged_usd':None,'native_sha256':r.digest(native)})
    config={'batch_id':r.BATCH,'routine_enabled':False,'gold_visually_reviewed':True,'cases':cases}
    save(root/'config/rollcall-evaluation.json',config)
    save(root/'config/media.json',{'inference':{'daily_cap_usd':'0.02','weekly_cap_usd':'0.20','lifetime_cap_usd':'20'}})
    save(root/'data/dashboard.json',{'members':[{'id':'fritts'}]})
    save(r.ledger_path(root),{'batch_id':r.BATCH,'config_sha256':r.digest(config),'prompt_sha256':r.digest(r.PROMPT),'entries':entries})
    save(r.folder(root)/'owner.json',{'owned':True,'config_sha256':r.digest(config)})
    return case,native


class RollcallTests(unittest.TestCase):
    def test_columns_member_and_full_roster_counts(self):
        case,native=sample();answer=r.reference(case,native)
        checked=r.validate(answer,case,native)
        self.assertEqual(checked['named_roster_count'],5)
        self.assertEqual(checked['member_cell']['raw_vote'],'N')
        self.assertEqual(checked['roster_tally'],case['expected']['tally'])
        controls=r.controls(case,native)
        self.assertEqual(len(controls),7)
        self.assertTrue(all(c['rejected'] for c in controls))

    def test_abstention_boolean_tally_and_unknown_code_rejected(self):
        case,native=sample();answer=r.reference(case,native)
        for change in ['abstain','bool','code']:
            altered=deepcopy(answer)
            if change=='abstain':altered['status']='unverified'
            if change=='bool':altered['tally']['present']=True
            if change=='code':altered['member_vote']['raw_vote']='ABSENT'
            with self.assertRaises(ValueError):r.validate(altered,case,native)

    def test_payload_excludes_gold_and_plugins_and_is_bounded(self):
        case,native=sample();body=r.payload(case,native)
        self.assertNotIn('plugins',body);self.assertNotIn('tools',body)
        self.assertFalse(body['provider']['allow_fallbacks'])
        self.assertEqual(body['provider']['only'],['deepinfra/fp8'])
        self.assertNotIn('expected',json.dumps(body))
        # The expected N choice is not leaked in a target-name-only instruction.
        self.assertTrue(body['messages'][1]['content'].startswith('Target member: Bradley Fritts\nPAGE 1'))
        native['pages']=['x'*10000]
        with self.assertRaisesRegex(ValueError,'prompt-byte-bound'):r.payload(case,native)
        self.assertLess((Decimal(10512)*Decimal('0.10')+Decimal(1000)*Decimal('0.40'))/1000000,r.HOLD)

    def test_six_measured_calls_preserve_old_hold_and_do_not_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);case,native=setup(root)
            prior={'entries':[{'attempted_at':NOW.isoformat(),'reserved_usd':'0.005','charged_usd':None}]}
            save(root/'data/pdf-extraction-ledger.json',prior)
            response=MagicMock();response.read.return_value=json.dumps({'provider':'DeepInfra','model':'qwen/qwen3-32b',
                'usage':{'cost':0.0001},'choices':[{'message':{'content':json.dumps(r.reference(case,native))}}]}).encode()
            opener=MagicMock();opener.open.return_value.__enter__.return_value=response
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(r,'build_opener',return_value=opener):
                r.execute(root,NOW,clock=lambda:NOW)
                with self.assertRaisesRegex(ValueError,'batch-not-owned'):r.execute(root,NOW,clock=lambda:NOW)
            self.assertEqual(opener.open.call_count,6)
            self.assertEqual(load(root/'data/rollcall-evaluation-report.json')['validated'],6)
            self.assertEqual(usage.periods(root,NOW.date())['day']['charged_usd'],'0.0006')
            self.assertEqual(usage.periods(root,NOW.date())['day']['reserved_usd'],'0.005')
            self.assertEqual(load(root/'data/pdf-extraction-ledger.json'),prior)
            self.assertEqual(load(root/'data/dashboard.json')['members'],[{'id':'fritts'}])

    def test_transport_failure_stops_calls_holds_unknown_and_releases_unsent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);setup(root)
            opener=MagicMock();opener.open.side_effect=TimeoutError('private transport details')
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(r,'build_opener',return_value=opener):
                r.execute(root,NOW,clock=lambda:NOW)
            self.assertEqual(opener.open.call_count,1)
            budget=usage.periods(root,NOW.date())['day']
            self.assertEqual(budget['reserved_usd'],'0.0015')
            self.assertNotIn('private',json.dumps(load(root/'data/rollcall-evaluation-report.json')))
            entries=load(r.ledger_path(root))['entries']
            self.assertTrue(all(e['status']=='not-attempted' and e['charged_usd']=='0' for e in entries[1:]))

    def test_unparseable_usage_stops_before_further_paid_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);setup(root)
            response=MagicMock();response.read.return_value=b'not-json-private-details'
            opener=MagicMock();opener.open.return_value.__enter__.return_value=response
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(r,'build_opener',return_value=opener):
                r.execute(root,NOW,clock=lambda:NOW)
            self.assertEqual(opener.open.call_count,1)
            self.assertEqual(usage.periods(root,NOW.date())['day']['reserved_usd'],'0.0015')
            self.assertNotIn('private',json.dumps(load(root/'data/rollcall-evaluation-report.json')))

    def test_abstention_remains_rejected_with_safe_status_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);case,native=setup(root)
            answer=r.reference(case,native);answer['status']='unverified'
            response=MagicMock();response.read.return_value=json.dumps({'provider':'DeepInfra','model':'qwen/qwen3-32b',
                'usage':{'cost':0.0001},'choices':[{'message':{'content':json.dumps(answer)}}]}).encode()
            opener=MagicMock();opener.open.return_value.__enter__.return_value=response
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(r,'build_opener',return_value=opener):
                r.execute(root,NOW,clock=lambda:NOW)
            report=load(root/'data/rollcall-evaluation-report.json')
            self.assertEqual(report['validated'],0)
            self.assertTrue(all(row['model_status']=='unverified' and row['error']=='model-abstained' and 'output' not in row for row in report['cases']))

    def test_routing_deviation_stops_batch_and_invalid_output_is_not_published(self):
        for wrong_provider in (True,False):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);case,native=setup(root)
                answer=r.reference(case,native);answer['member_vote']['raw_vote']='Y'
                answer['member_vote']['name']='private invented text'
                response=MagicMock();response.read.return_value=json.dumps({'provider':'Wrong' if wrong_provider else 'DeepInfra',
                    'model':'qwen/qwen3-32b','usage':{'cost':0.0001},'choices':[{'message':{'content':json.dumps(answer)}}]}).encode()
                opener=MagicMock();opener.open.return_value.__enter__.return_value=response
                with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(r,'build_opener',return_value=opener):
                    r.execute(root,NOW,clock=lambda:NOW)
                report=load(root/'data/rollcall-evaluation-report.json')
                self.assertEqual(opener.open.call_count,1 if wrong_provider else 6)
                self.assertNotIn('private',json.dumps(report))
                self.assertTrue(all('output' not in row for row in report['cases']))

    def test_preflight_rejects_hash_changed_scanned_and_oversized_page_count(self):
        for mode in ('hash','scanned','pages'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);setup(root);r.ledger_path(root).unlink()
                config=load(root/'config/rollcall-evaluation.json');raw=b'%PDF-test'
                for i,case in enumerate(config['cases']):
                    case.update(member_id='fritts' if i<3 else 'arellano',sha256=hashlib.sha256(raw).hexdigest(),
                        source_url='https://ilga.gov/Documents/legislation/votehistory/104/house/committeevotes/test.pdf')
                save(root/'config/rollcall-evaluation.json',config);save(root/'config/project.json',{})
                document=MagicMock();page=MagicMock();page.extract_text.return_value=''
                document.pages=[page]* (3 if mode=='pages' else 1)
                library=MagicMock();library.open.return_value.__enter__.return_value=document
                client=MagicMock();client.get.return_value={'body':b'%PDF-changed' if mode=='hash' else raw}
                with patch.dict('sys.modules',{'pdfplumber':library}),patch.object(r,'Client',return_value=client),self.assertRaises(ValueError):
                    r.prepare(root,NOW)
                self.assertFalse(r.ledger_path(root).exists())

    def test_hash_date_and_budget_gates_before_network(self):
        for mode in ('native','config','next-day','budget'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);setup(root)
                if mode=='native':save(r.folder(root)/'sample-0.json',{'pages':['tampered'],'words':[]})
                if mode=='config':
                    config=load(root/'config/rollcall-evaluation.json');config['routine_enabled']=True;save(root/'config/rollcall-evaluation.json',config)
                if mode=='budget':save(root/'data/pdf-extraction-ledger.json',{'entries':[{'attempted_at':NOW.isoformat(),'reserved_usd':'0.015','charged_usd':None}]})
                with patch.object(r,'build_opener') as opening,self.assertRaises(ValueError):
                    r.execute(root,NOW+timedelta(days=1) if mode=='next-day' else NOW,clock=lambda:NOW)
                opening.assert_not_called()

    def test_day_rollover_makes_no_calls_and_settles_only_unsent_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);setup(root)
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(r,'build_opener') as opening:
                r.execute(root,NOW,clock=lambda:NOW+timedelta(days=1))
            opening.assert_not_called()
            self.assertEqual(usage.periods(root,NOW.date())['day']['liability_usd'],'0')

    def test_concurrent_execution_sends_one_batch_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);case,native=setup(root);barrier=Barrier(2);original=r.load
            def synchronized(path):
                value=original(path)
                if path.name=='owner.json':barrier.wait(timeout=5)
                return value
            response=MagicMock();response.read.return_value=json.dumps({'provider':'DeepInfra','model':'qwen/qwen3-32b',
                'usage':{'cost':0.0001},'choices':[{'message':{'content':json.dumps(r.reference(case,native))}}]}).encode()
            opener=MagicMock();opener.open.return_value.__enter__.return_value=response
            def execute():
                try:r.execute(root,NOW,clock=lambda:NOW);return 'finished'
                except ValueError:return 'blocked'
            with patch.dict('os.environ',{'OPENROUTER_API_KEY':'not-a-real-key'}),patch.object(r,'build_opener',return_value=opener),patch.object(r,'load',side_effect=synchronized),ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda _:execute(),range(2)))
            self.assertEqual(sorted(results),['blocked','finished']);self.assertEqual(opener.open.call_count,6)
