"""Offline Stage D acceptance. All non-live events below are synthetic fixtures."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import ast
import json
import tempfile
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup

from civic_tracker import digest as d
from civic_tracker.changes import empty, reconcile, packed
from civic_tracker.change_sources import fact, scope, evidence

ROOT = Path(__file__).resolve().parents[1]
BASE = '2026-10-19T13:00:00+00:00'
CHECKED = '2026-10-20T15:00:00+00:00'
ASOF = '2026-10-20T17:00:00+00:00'
BILL = 'https://ilga.gov/Legislation/BillStatus?DocNum=24&GAID=18&DocTypeID=HB&SessionID=114'
NOTICE = 'https://ilga.gov/House/hearings/details/3062/23132'
COMMITTEE = 'https://ilga.gov/House/Committees/Members/3062'


def role(key='role', **extra):
    return fact(key,'sponsor-role','IL',['fritts'],'SYNTHETIC · Housing review example',
        'Added Co-Sponsor Rep. Bradley Fritts',evidence(BILL,CHECKED,'official-bill','a'*64),'2026-10-20',
        measure='IL-104-HB24',role='co-sponsor',operation='added-or-changed',**extra)


def hearing(**extra):
    row = fact('hearing:IL-104-HOUSE-3062-23132','hearing','IL',['fritts'],'SYNTHETIC · Judiciary - Civil',
        'Published schedule; see the official notice.',evidence(NOTICE,BASE,'official-calendar','b'*64),'2026-10-25',
        committee=COMMITTEE,local_time='2026-10-25T08:00',timezone='America/Chicago',
        hearing_key='IL-104-HOUSE-3062-23132',location='Fixture room',agenda=[],agenda_coverage='complete',
        status='scheduled',status_basis='scheduled-listing',status_notice=None)
    row.update(extra);return row


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'data').mkdir();(self.root/'config').mkdir()
        for name in ('digest.json','hearings.json','relevance.json'):
            (self.root/'config'/name).write_bytes((ROOT/'config'/name).read_bytes())
        self.save('dashboard',{'members':[{'id':'fritts','name':'Bradley Fritts','calendar_health':'checked','meetings':[]}]})
        self.save('daily-report',{'sources':{'Illinois':{'status':'ok','checked_at':CHECKED}}})
        self.scopes = [scope('bill','IL',BASE,True,[]),scope('calendar:'+COMMITTEE,'IL',BASE,True,[hearing()],adapter=3)]
        self.ledger,self.quality = reconcile(empty(),self.scopes,BASE)
        self.quality['checked_at']=ASOF;self.flush()

    def save(self,name,value):
        (self.root/'data'/(name+'.json')).write_text(packed(value)+'\n',encoding='utf-8')

    def flush(self):
        self.save('change-ledger',self.ledger);self.save('change-quality-report',self.quality)

    def add(self,rows,checked=CHECKED):
        self.scopes[0]=scope('bill','IL',checked,True,rows)
        self.ledger,self.quality=reconcile(self.ledger,self.scopes,checked)
        self.quality['checked_at']=ASOF;self.flush()

    def test_normal_preview_has_reason_source_exact_revision_and_no_delivery(self):
        self.add([role()]);data=d.preview(self.root)
        self.assertEqual(len(data['sections']['members']),1);self.assertEqual(len(data['opportunities']),1)
        row=data['sections']['members'][0]
        self.assertEqual(data['selected_revision_ids'],[row['revision_id']])
        self.assertEqual(row['source_url'],BILL);self.assertTrue(row['reason']);self.assertEqual(row['source_date'],'2026-10-20')
        self.assertNotEqual(row['source_date'],row['observed_at'])
        self.assertEqual(data['delivery'],{'enabled':False,'state':'preview-only','attempts':0})
        files,report=d.artifacts(self.root)
        self.assertEqual(set(files),d.ARTIFACTS);self.assertFalse(report['delivery_enabled'])
        self.assertIn('Email delivery disabled',files['digest-preview.html'])
        self.assertIn('EMAIL DELIVERY DISABLED',files['digest-preview.txt'])

    def test_quiet_week_is_explicit_without_manufacturing_three_news_items(self):
        data=d.preview(self.root);self.assertTrue(data['quiet']);self.assertEqual(data['sections']['news'],[])
        self.assertIn('does not establish inactivity',d.render_text(data));self.assertEqual(data['selected_revision_ids'],[])

    def test_partial_sources_and_stale_notices_are_not_usable_opportunities(self):
        self.quality['scopes'][1]['status']='withheld';self.quality['status']='partial';self.flush()
        data=d.preview(self.root);self.assertEqual(data['health']['status'],'partial');self.assertEqual(data['opportunities'],[])
        self.assertEqual(data['omitted']['stale_or_withheld_hearings'],1)
        self.assertEqual(d.preview(self.root,'2026-10-22T17:00:00+00:00')['opportunities'],[])

    def test_baseline_and_late_backfill_cannot_become_this_weeks_new_activity(self):
        # This source was already baselined before the preview week began.
        self.ledger['scopes']['bill']['baseline_at']='2026-10-16T13:00:00+00:00'
        old=role();old['occurred_at']='2026-10-18';self.add([old])
        data=d.preview(self.root);self.assertEqual(data['sections']['members'],[])
        self.assertEqual(data['omitted']['late_historical_discovery'],1)
        old['occurred_at']='2025-01-01';self.add([old],checked='2026-10-20T16:00:00+00:00')
        # This is a correction to the previously accepted relationship, clearly
        # retained as a correction despite the old source-action date.
        data=d.preview(self.root);self.assertEqual(data['sections']['members'][0]['change'],'corrected')
        self.assertEqual(data['sections']['members'][0]['source_date'],'2025-01-01')
        self.assertIn('Change: corrected',d.render_text(data))
        self.assertIn('Change: corrected',d.render_html(data))

    def test_current_revisions_deduplicate_and_historical_replay_requires_frozen_inputs(self):
        self.add([role()]);first=d.preview(self.root)
        changed=role();changed['detail']='Removed Co-Sponsor Rep. Bradley Fritts';changed['operation']='removed'
        self.add([changed],'2026-10-20T18:00:00+00:00')
        with self.assertRaisesRegex(ValueError,'digest-historical-source-snapshot-required'):d.preview(self.root,ASOF)
        later=d.preview(self.root,'2026-10-20T19:00:00+00:00')
        self.assertEqual(len(later['selected_revision_ids']),1)
        self.assertTrue(later['selected_revision_ids'][0].endswith('-r2'))

    def test_invalid_facts_urls_fingerprints_and_unknown_vote_are_withheld(self):
        self.add([role()]);self.ledger['events'][0]['fact']['evidence']['url']='javascript:bad()';self.flush()
        self.assertEqual(d.preview(self.root)['selected_revision_ids'],[])
        self.assertTrue(d.preview(self.root)['quiet'])

    def test_untrusted_source_text_is_escaped_and_private_addresses_fail_closed(self):
        text=role();text['title']='<script>fixture()</script> Housing';self.add([text])
        files,_=d.artifacts(self.root);soup=BeautifulSoup(files['digest-preview.html'],'html.parser')
        self.assertFalse(soup.select('script'));self.assertIn('<script>fixture()</script>',soup.get_text())
        text['title']='Contact '+ 'private'+chr(64)+'example.org';self.add([text],'2026-10-20T16:00:00+00:00')
        with self.assertRaisesRegex(ValueError,'digest-sensitive-content'):d.artifacts(self.root)

    def test_week_boundary_dst_and_delayed_monday_keep_six_am_local(self):
        p=d.window('2026-11-02T13:00:00+00:00')
        self.assertTrue(p['complete_period']);self.assertEqual(p['start'],'2026-10-26T06:00:00-05:00')
        self.assertEqual(p['end'],'2026-11-02T06:00:00-06:00')
        self.assertEqual((d.timestamp(p['end'])-d.timestamp(p['start'])).total_seconds()/3600,169)
        self.assertEqual(p['cutoff'],p['end'])
        with self.assertRaises(ValueError):d.window(ASOF,'2026-10-27')

    def test_duplicate_future_or_held_revisions_and_noise_never_enter_preview(self):
        ceremonial=role('ceremony');ceremonial['title']='CONGRATS-FIXTURE'
        self.add([role(),ceremonial]);self.ledger['events'].append(deepcopy(self.ledger['events'][0]));self.flush()
        data=d.preview(self.root);self.assertEqual(len(data['selected_revision_ids']),1)
        self.assertEqual(data['omitted']['ceremony_or_no_opposition'],1)
        with self.assertRaisesRegex(ValueError,'digest-historical-source-snapshot-required'):d.preview(self.root,'2026-10-20T14:00:00+00:00')

    def test_later_unchanged_hearing_receipt_cannot_rewrite_an_earlier_preview(self):
        before=d.preview(self.root);self.assertEqual(len(before['opportunities']),1)
        changed=hearing();changed['evidence']['retrieved_at']='2026-10-20T18:00:00+00:00'
        self.scopes[1]=scope('calendar:'+COMMITTEE,'IL','2026-10-20T18:00:00+00:00',True,[changed],adapter=3)
        self.add([],'2026-10-20T18:00:00+00:00')
        with self.assertRaisesRegex(ValueError,'digest-historical-source-snapshot-required'):d.preview(self.root,ASOF)
        self.assertEqual(len(d.preview(self.root)['opportunities']),1)

    def test_root_relevance_configuration_is_the_one_rendered_and_fingerprinted(self):
        (self.root/'config/relevance.json').write_text('{"topics":{}}')
        self.add([role()]);data=d.preview(self.root)
        self.assertEqual(data['sections']['members'][0]['topics'],[])
        import hashlib
        self.assertEqual(data['input_sha256']['config/relevance.json'],hashlib.sha256((self.root/'config/relevance.json').read_bytes()).hexdigest())

    def test_exact_snapshot_cutoff_included_but_completed_week_end_excluded(self):
        self.add([role()],ASOF);self.assertEqual(len(d.preview(self.root)['selected_revision_ids']),1)
        # Move the event's observation to exactly the scheduled end. The later
        # preview remains current while selecting the completed earlier week.
        end='2026-10-26T11:00:00+00:00'
        self.ledger['events'][0]['observed_at']=end;self.flush()
        data=d.preview(self.root,'2026-10-26T13:00:00+00:00')
        self.assertEqual(data['selected_revision_ids'],[]);self.assertFalse(data['period']['cutoff_inclusive'])

    def prepare_form(self,**overrides):
        agenda={'id':'HB24:SFA2','bill':'HB24','amendment':'SFA2','official_url':BILL,
                'contexts':[{'motion':'Concur','vote_motion':'','vote_result':''}]}
        self.scopes[1]=scope('calendar:'+COMMITTEE,'IL',BASE,True,[hearing(agenda=[agenda])],adapter=3)
        self.ledger,self.quality=reconcile(empty(),self.scopes,BASE);self.quality['checked_at']=ASOF;self.flush()
        item={'bill':'HB24','amendment':'SFA2','submission_verified':True,'submission_checked_at':CHECKED,
              'witness_slip_url':'https://my.ilga.gov/WitnessSlip/Create/210820'}
        item.update(overrides)
        meeting={'hearing_key':'IL-104-HOUSE-3062-23132','source_url':NOTICE,
            'evidence':{'sha256':'b'*64},'status':'scheduled','items':[item]}
        self.save('dashboard',{'members':[{'id':'fritts','calendar_health':'checked','meetings':[meeting]}]})

    def test_only_fresh_matching_explicit_submission_form_is_published(self):
        self.prepare_form();data=d.preview(self.root)
        self.assertEqual(len(data['opportunities'][0]['witness_forms']),1)
        self.assertIn('verified open witness form',d.render_html(data))
        for changes in [{'submission_verified':False},{'submission_verified':'false'},
                        {'submission_checked_at':'2026-10-18T15:00:00+00:00'},
                        {'witness_slip_url':'https://my.ilga.gov/Hearing/Results/210820'},
                        {'bill':'HB25'},{'amendment':'SFA1'}]:
            self.prepare_form(**changes);self.assertEqual(d.preview(self.root)['opportunities'][0]['witness_forms'],[])

    def test_form_proof_from_another_notice_never_matches_on_hash_alone(self):
        self.prepare_form();snapshot=json.loads((self.root/'data/dashboard.json').read_text())
        snapshot['members'][0]['meetings'][0]['source_url']=NOTICE+'/wrong'
        self.save('dashboard',snapshot)
        self.assertEqual(d.preview(self.root)['opportunities'][0]['witness_forms'],[])

    def test_votes_keep_motion_raw_choice_tally_and_separate_bill_evidence_links(self):
        vote=fact('roll','vote','IL',['fritts'],'SYNTHETIC · Housing vote','Do Pass — fixture motion',
            evidence('https://ilga.gov/documents/reports/static/104MemberVotes.csv',CHECKED,'official-roll','c'*64),
            '2026-10-20',measure='IL-104-HB24',choice='no',raw_choice='N',vote_scope='floor',totals={'yes':10,'no':5})
        title=fact('bill-title','bill-title','IL',['fritts'],'SYNTHETIC · Housing vote','Official fixture short title',
            evidence(BILL,CHECKED,'official-bill','d'*64),measure='IL-104-HB24')
        self.add([vote,title]);data=d.preview(self.root);row=data['sections']['members'][0]
        self.assertEqual(row['choice'],'no');self.assertEqual(row['totals'],{'yes':10,'no':5})
        self.assertEqual(row['title_url'],BILL);self.assertNotEqual(row['title_url'],row['source_url'])
        html=d.render_html(data);self.assertIn('no (N)',html);self.assertIn('fixture motion',html)
        vote['choice']='yes';vote['totals']['no']=0
        self.add([vote,title],'2026-10-20T16:00:00+00:00')
        self.assertEqual(d.preview(self.root)['sections']['members'],[])

    def test_attributed_party_edit_is_separate_and_images_remain_held(self):
        url='https://leecountyilgop.org/'
        p={'key':'edit','kind':'party-change','jurisdiction':'LOCAL','session':None,'members':[],
            'entities':['lee-gop'],'occurred_at':None,'date_precision':'unknown',
            'title':'SYNTHETIC · County party meeting notice','detail':'Publisher page edit; event date unknown.',
            'evidence':{'url':url,'retrieved_at':CHECKED,'binding':'party-page','sha256':'e'*64},
            'publisher':'Lee County IL Republican Central Committee','categories':['event-meeting'],
            'reasons':['changed-span phrase: meeting'],'before_sha256':'d'*64,'after_sha256':'e'*64,
            'before_excerpt':'Synthetic previous meeting notice','after_excerpt':'Synthetic changed meeting notice',
            'observed_at':CHECKED,'previous_good_at':BASE,'after_gap':True}
        scoped={'id':'party-fixture','family':'party-pages','adapter':3,'jurisdiction':'LOCAL','session':None,
                'checked_at':BASE,'complete':True,'facts':[]}
        self.scopes.append(scoped);self.ledger,self.quality=reconcile(self.ledger,self.scopes,BASE)
        scoped.update(checked_at=CHECKED,facts=[p]);self.add([])
        data=d.preview(self.root);self.assertEqual(len(data['sections']['parties']),1)
        self.assertEqual(data['sections']['members'],[]);self.assertIsNone(data['sections']['parties'][0]['source_date'])
        self.assertEqual(data['sections']['parties'][0]['before_excerpt'],'Synthetic previous meeting notice')
        self.assertEqual(data['sections']['parties'][0]['after_excerpt'],'Synthetic changed meeting notice')
        self.assertIn('claims attributed',d.render_text(data));self.assertIn('collection gap',data['sections']['parties'][0]['reason'])
        self.assertIn('Before: Synthetic previous meeting notice',d.render_text(data))
        self.assertIn('What changed on the party page',d.render_html(data))
        p['categories']=['image-review'];p['reasons']=['image change; human visual review required']
        p['observed_at']='2026-10-20T16:00:00+00:00';p['evidence']['retrieved_at']=p['observed_at']
        scoped['checked_at']=p['observed_at'];self.add([],p['observed_at'])
        self.assertEqual(d.preview(self.root)['sections']['parties'],[])

    def test_cancellation_is_an_update_not_a_participation_opportunity(self):
        self.scopes[1]=scope('calendar:'+COMMITTEE,'IL',CHECKED,True,
            [hearing(status='canceled',status_basis='explicit-notice',status_notice='Canceled')],adapter=3)
        self.add([]);data=d.preview(self.root)
        self.assertEqual(data['opportunities'],[]);self.assertEqual(data['sections']['schedule'][0]['hearing_status'],'canceled')

    def test_news_and_direct_communications_have_separate_sections(self):
        items=[]
        for key,kind in [('news','news'),('office','office'),('party','party')]:
            item=fact(key,'publication','IL',['fritts'],'SYNTHETIC · Fritts fixture report',
                'Publisher metadata, not an independently verified claim.',evidence('https://example.org/'+key,CHECKED,'publisher-listing'),
                '2026-10-20',publisher='Fixture newsroom' if kind=='news' else 'Fixture office/party',publication_kind=kind)
            self.scopes.append(scope(key,'IL',BASE,True,[]));items.append(item)
        self.ledger,self.quality=reconcile(self.ledger,self.scopes,BASE)
        for scoped,item in zip(self.scopes[2:],items):scoped.update(checked_at=CHECKED,facts=[item])
        self.add([]);data=d.preview(self.root)
        self.assertEqual(len(data['sections']['news']),1);self.assertEqual(len(data['sections']['communications']),2)
        self.assertEqual(data['sections']['news'][0]['publisher'],'Fixture newsroom')

    def test_repeated_build_is_identical_and_never_mutates_source_or_financial_data(self):
        self.add([role()]);before={p.name:p.read_bytes() for p in (self.root/'data').iterdir()}
        output=self.root/'preview';report=d.build(self.root,output)
        first={p.name:p.read_bytes() for p in output.iterdir()};self.assertEqual(report,d.build(self.root,output))
        self.assertEqual(first,{p.name:p.read_bytes() for p in output.iterdir()})
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'data').iterdir()})
        (output/'.digest-preview.lock').write_text('fixture lock')
        with self.assertRaisesRegex(ValueError,'digest-preview-busy'):d.build(self.root,output)
        self.assertEqual(first,{p.name:p.read_bytes() for p in output.iterdir() if p.name!='.digest-preview.lock'})

    def test_limits_omissions_unsafe_output_and_config_cannot_enable_delivery(self):
        self.add([role(str(i)) for i in range(10)]);data=d.preview(self.root)
        self.assertEqual(len(data['sections']['members']),6);self.assertEqual(data['omitted']['bounded_events'],4)
        output=self.root/'unmanaged';output.mkdir();(output/'private.md').write_text('keep')
        with self.assertRaisesRegex(ValueError,'digest-output-not-owned'):d.build(self.root,output)
        self.assertEqual((output/'private.md').read_text(),'keep')
        config=json.loads((self.root/'config/digest.json').read_text());config['delivery_enabled']=True
        (self.root/'config/digest.json').write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError,'digest-preview-only-config'):d.preview(self.root)

    def test_preview_has_no_send_transport_secret_access_or_new_schedule(self):
        source=(ROOT/'src/civic_tracker/digest.py').read_text();tree=ast.parse(source)
        imports=[n.names[0].name for n in ast.walk(tree) if isinstance(n,ast.Import)]
        self.assertFalse(set(imports)&{'smtplib','imaplib','requests','socket'})
        self.assertNotIn('os.environ',source);self.assertNotIn('GMAIL_',source);self.assertNotIn('OPENROUTER_',source)
        self.assertNotIn('sendmail',source);self.assertNotIn('send_message',source)
        self.assertNotIn("choices=['send'",source)
        self.assertFalse((ROOT/'.github/workflows/digest.yml').exists())


if __name__=='__main__':unittest.main()
