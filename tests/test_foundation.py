import unittest,sys,csv,json,tempfile,ssl,hashlib
from unittest.mock import patch,MagicMock
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from civic_tracker.rules import ceremonial,shell
from civic_tracker.vote_csv import bill_id,motion,choice,read_csv
from civic_tracker.http import validate_url,Client,source_tls_context
from civic_tracker.privacy import violations
from civic_tracker.mail_test import self_address_pair,reserve,send
from civic_tracker.verify_pdf_sample import current_role,parse_sponsor_rows

class RulesTests(unittest.TestCase):
 def test_reviewed_export_counts_and_ceremonial_ids(self):
  fixtures=Path(__file__).parent/'fixtures'
  with (fixtures/'fritts-sponsorship-104.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
  self.assertEqual(len(rows),134)
  expected=json.loads((fixtures/'ceremonial-expected.json').read_text())['ids']
  self.assertEqual([r['Legislation'] for r in rows if ceremonial(r['ABR'])],expected)
  self.assertEqual(len(expected),24)
  for ident in ['HR0055','HR0112','HR0292','HR0316','HR0494','HJR0012','HJR0024']:
   self.assertFalse(ceremonial(next(r['ABR'] for r in rows if r['Legislation']==ident)))
 def test_shell_is_a_flag_not_a_rewrite_claim(self):
  self.assertTrue(shell('REGULATION-TECH',''))
  self.assertTrue(shell('$2 APPROPRIATION',''))
  self.assertTrue(shell('TITLE','Makes a technical change.'))
  self.assertFalse(shell('SUBSTANTIVE BILL','Ordinary amendment'))
 def test_memorial_and_substantive_resolution(self):
  self.assertTrue(ceremonial("DEPUTY MEM'L HWY"))
  self.assertFalse(ceremonial('NO TAX ON RETIREMENT INCOME'))

class PdfSampleTests(unittest.TestCase):
 def test_parenthesized_alternate_keeps_chief_roles(self):
  block='(Sen. Ram Villivalam-Neil Anderson, Other Member)'
  self.assertEqual(current_role(block,'Ram Villivalam',True),'Alt. Chief Sponsor')
  self.assertEqual(current_role(block,'Neil Anderson',True),'Alt. Chief Co-Sponsor')
  self.assertEqual(current_role(block,'Other Member',True),'Alt. Co-Sponsor')
  self.assertEqual(current_role('(Sen. Patrick J. Joyce and Neil Anderson)','Neil Anderson',True),'Alt. Co-Sponsor')
 def test_pdf_role_and_date_are_separate_columns(self):
  text='Sponsor Legislation Listing For Sample Legislator\nHB 00024 SHORT TITLE Alt. Chief Sponsor H Public Act . . . 104-0001 08/15/2025'
  row=parse_sponsor_rows(text,limit=1)[0]
  self.assertEqual((row['bill'],row['role'],row['date']),('HB24','Alt. Chief Sponsor','2025-08-15'))
 def test_empty_pdf_is_not_a_successful_sample(self):
  with self.assertRaises(ValueError):parse_sponsor_rows('Sponsor Legislation Listing For Sample Legislator\nNO DATA FOUND')

class VoteTests(unittest.TestCase):
 def test_narrow_motion_aliases(self):
  self.assertEqual(motion('HOUSE BILL / Third Reading / PASSED'),'THIRD READING')
  self.assertEqual(motion('CONCUR IN SENATE AMENDMENT # 2 / CONCURRED'),'CONCUR IN SENATE AMENDMENT NO 2')
  self.assertNotEqual(motion('CONCUR IN SENATE AMENDMENT #1'),motion('CONCUR IN SENATE AMENDMENT #2'))
 def test_nonvoting_choices_are_not_guessed(self):
  self.assertEqual(choice('Excused'),'excused');self.assertEqual(choice('Absent'),'absent')
  self.assertEqual(choice('No Vote'),'unknown:No Vote')
  self.assertNotEqual(choice('Not Voting'),choice('Excused'))
 def test_measure_ids_do_not_erase_motion_amendments(self):
  self.assertEqual(bill_id('HB0024 SCA1'),'HB24')
 def test_nay_count_uses_all_members_before_subject_filter(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'votes.csv'
   with path.open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['GA','Member','Chamber','Session','Legislation','Vote Type','Vote Date','Vote'])
    for name,vote in [('Fritts, Bradley','Yea'),('Other, Public','Nay')]:w.writerow(['104',name,'House','Regular','HB0024','Third Reading','2025-04-08',vote])
   data=read_csv(path);self.assertEqual(len(data['subjects']),1);self.assertEqual(data['subjects'][0]['nay_count'],1)

class PrivacyTests(unittest.TestCase):
 def test_addresses_and_credentials_are_rejected_without_echo(self):
  self.assertIn('email-address',violations('person'+chr(64)+'example.com'))
  self.assertIn('credential-shape',violations('ghp'+'_'+'x'*25))
  self.assertIn('opaque-token-shape',violations('a1'*20))
 def test_noreply_and_source_hashes_are_allowed(self):
  self.assertEqual(violations('123+project'+chr(64)+'users.noreply.github.com'),[])
  self.assertEqual(violations('abcdef0123456789'*4),[])
 def test_machine_profile_paths_are_rejected(self):
  value='C:'+chr(92)+'Users'+chr(92)+'example'
  self.assertIn('user-profile-path',violations(value))

class MailSafetyTests(unittest.TestCase):
 def test_only_same_mailbox_plus_alias_is_accepted(self):
  sender='civic.owner'+chr(64)+'gmail.com'
  self_address_pair(sender,'civicowner+tracker'+chr(64)+'gmail.com')
  for recipient in ['different+tracker'+chr(64)+'gmail.com',sender,'civicowner+tracker'+chr(64)+'other.example']:
   with self.assertRaises(ValueError):self_address_pair(sender,recipient)
 def test_existing_reservation_prevents_another_test(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'receipt.json'
   self.assertEqual(reserve(path),0);first=path.read_bytes()
   self.assertEqual(reserve(path),1);self.assertEqual(path.read_bytes(),first)
 def test_smtp_exception_is_not_written_to_receipt(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'receipt.json';reserve(path)
   settings={'GMAIL_USER':'owner'+chr(64)+'gmail.com','GMAIL_APP_PASSWORD':'synthetic-test-password','DIGEST_TO':'owner+test'+chr(64)+'gmail.com'}
   with patch.dict('os.environ',settings),patch('civic_tracker.mail_test.smtplib.SMTP',side_effect=RuntimeError('private exception contents')):
    self.assertEqual(send(path),1)
   data=path.read_text();self.assertNotIn('private exception contents',data);self.assertNotIn(settings['GMAIL_USER'],data)

class AccessTests(unittest.TestCase):
 def test_pinned_intermediate_rejects_changed_bytes(self):
  with tempfile.TemporaryDirectory() as temp:
   digest='a'*64;Path(temp,'issuer-'+digest+'.der').write_bytes(b'changed')
   config={'tls_intermediates':[{'hosts':['ilga.gov'],'url':'http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR40.crt','der_sha256':digest}]}
   with self.assertRaisesRegex(ValueError,'fingerprint'):source_tls_context(config,temp,'ilga.gov')
 def test_certificate_issuer_must_be_explicitly_allowed(self):
  with tempfile.TemporaryDirectory() as temp:
   config={'tls_intermediates':[{'hosts':['ilga.gov'],'url':'http://unrelated.example/cert','der_sha256':'a'*64}]}
   with self.assertRaisesRegex(ValueError,'Unapproved'):source_tls_context(config,temp,'ilga.gov')

 def test_logged_in_and_unapproved_hosts_are_rejected(self):
  for url in ['https://ilga.gov/MyLegislation','https://ilga.gov/account/settings','https://unrelated.example/resource','http://ftp.ilga.gov/']:
   with self.assertRaises(ValueError):validate_url(url)
 def test_rate_gate_cannot_be_configured_below_ten(self):
  with tempfile.TemporaryDirectory() as temp:
   with self.assertRaises(ValueError):Client({'main_site_min_interval_seconds':9},temp)
 def test_rate_clock_uses_the_recorded_attempt_start(self):
  with tempfile.TemporaryDirectory() as temp:
   current=[100.0]
   def sleep(seconds):current[0]+=seconds
   response=MagicMock();response.status=200;response.headers={};response.read.return_value=b'ok'
   opener=MagicMock();opener.open.return_value.__enter__.return_value=response
   config={'main_site_min_interval_seconds':20,'user_agent':'public-project','max_source_bytes':1024}
   with patch('civic_tracker.http.time.time',side_effect=lambda:current[0]),patch('civic_tracker.http.time.sleep',side_effect=sleep),patch('civic_tracker.http.build_opener',return_value=opener):
    client=Client(config,temp);client.get('https://ilga.gov/robots.txt')
    current[0]+=0.5;client.get('https://ilga.gov/robots.txt')
   self.assertGreaterEqual(client.events[1]['started_epoch']-client.events[0]['started_epoch'],20)
   clock=json.loads((Path(temp)/'main-request-clock.json').read_text())
   self.assertEqual(clock['started_epoch'],client.events[-1]['started_epoch'])
 def test_ftp_primary_is_allowed(self):validate_url('https://ftp.ilga.gov/Legislation/104/BillStatus/XML/')

if __name__=='__main__':unittest.main()
