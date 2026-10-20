from datetime import datetime, timezone, timedelta
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape
from bs4 import BeautifulSoup

from civic_tracker import media
from civic_tracker.dashboard import media_section, render
from civic_tracker.privacy import violations

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026,10,17,18,tzinfo=timezone.utc)
CONFIG = json.loads((ROOT/'config/media.json').read_text())
MEMBER = {'id':'fritts','name':'Bradley Fritts'}


def item(title='Brad Fritts discusses housing', publisher='Shaw Local', domain='https://www.shawlocal.com', date='Fri, 16 Oct 2026 12:00:00 GMT', url=None):
    url = url or 'https://news.google.com/rss/articles/'+('Ab12Cd34'*12)+'?oc=5'
    return '<item><title>'+escape(title+' - '+publisher)+'</title><link>'+escape(url)+'</link><pubDate>'+date+'</pubDate><source url="'+domain+'">'+publisher+'</source></item>'


def feed(*items):
    return ('<rss><channel>'+''.join(items)+'</channel></rss>').encode()


class MediaTests(unittest.TestCase):
    def test_sections_follow_witness_guidance_for_all_five_members(self):
        page, _ = render(ROOT)
        soup = BeautifulSoup(page,'html.parser')
        self.assertEqual(len(soup.select('.member-media')),5)
        for card in soup.select('.member-card'):
            self.assertEqual(card.select_one('.slip-note').find_next_sibling()['class'],['member-media'])

    def test_only_dated_named_allowlisted_reports_in_window(self):
        rows = media.parse_feed(feed(item(),item(domain='https://campaign.example'),item(date='Fri, 16 Jan 2026 12:00:00 GMT'),item(date='Sun, 18 Oct 2026 12:00:00 GMT'),item(title='Editorial: Fritts for office'),item(title='Unrelated traffic report'),item(url='javascript:alert(1)')),MEMBER,CONFIG,NOW)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['title'],'Brad Fritts discusses housing')
        self.assertNotIn('?',rows[0]['url'])
        self.assertEqual(rows[0]['publisher'],'Shaw Local')

    def test_sort_dedup_and_entity_bound(self):
        rows=media.parse_feed(feed(item(date='Thu, 15 Oct 2026 12:00:00 GMT'),item(title='Fritts announces public meeting')),MEMBER,CONFIG,NOW)
        self.assertEqual(rows[0]['title'],'Fritts announces public meeting')
        self.assertEqual(len(media.parse_feed(feed(item(),item()),MEMBER,CONFIG,NOW)),1)
        with self.assertRaises(ValueError):media.parse_feed(b'<!DOCTYPE rss><rss/>',MEMBER,CONFIG,NOW)

    def test_200_day_discovery_accepts_older_news_but_excludes_expired_and_future(self):
        def dated(age):
            return item(title=f'Fritts housing report age {age}',
                        date=(NOW-timedelta(days=age)).strftime('%a, %d %b %Y %H:%M:%S GMT'))
        rows=media.parse_feed(feed(*(dated(age) for age in (100,199,200,201,-1))),MEMBER,CONFIG,NOW)
        self.assertEqual(len(rows),3)
        self.assertEqual([r['title'] for r in rows], [f'Fritts housing report age {age}' for age in (100,199,200)])

    def test_homepage_90_day_and_member_200_day_windows_are_separate(self):
        row=media.parse_feed(feed(item()),MEMBER,CONFIG,NOW)[0]
        old={**row,'published_at':(NOW-timedelta(days=120)).isoformat()}
        member={**MEMBER,'media_reports':[old], 'media_health':{'lookback_days':200,'source_status':'ok',
                'inference_status':'complete','checked_at':NOW.isoformat()}}
        home=BeautifulSoup(media_section(member,as_of=NOW.isoformat()),'html.parser')
        history=BeautifulSoup(media_section(member,200,NOW.isoformat()),'html.parser')
        self.assertEqual(len(home.select('.media-row')),0)
        self.assertEqual(len(history.select('.media-row')),1)
        self.assertIn('last 200 days',history.get_text())
        self.assertIn('last 90 days',home.get_text())
        self.assertNotIn('has not completed',history.get_text())
        for age in (201,-1):
            member['media_reports']=[{**row,'published_at':(NOW-timedelta(days=age)).isoformat()}]
            self.assertNotIn('class="media-row"',media_section(member,200,NOW.isoformat()))

    def test_older_source_receipt_does_not_claim_a_completed_200_day_search(self):
        member={**MEMBER,'media_reports':[],'media_health':{'lookback_days':90,
                'source_status':'ok','inference_status':'complete','checked_at':NOW.isoformat()}}
        self.assertIn('200-day search has not completed',media_section(member,200,NOW.isoformat()))

    def test_window_change_reuses_existing_exact_case_cache_identity(self):
        narrow={**CONFIG,'lookback_days':90}
        old=media.parse_feed(feed(item()),MEMBER,narrow,NOW)[0]
        expanded=media.parse_feed(feed(item()),MEMBER,CONFIG,NOW)[0]
        self.assertEqual(media.case(old),media.case(expanded))
        self.assertEqual(media.inference._case_hash(media.case(old)),media.inference._case_hash(media.case(expanded)))

    def test_google_public_id_exception_still_rejects_secrets_and_other_hosts(self):
        public='Ab12Cd34'*12
        self.assertEqual(violations('https://news.google.com/rss/articles/'+public),[])
        self.assertIn('opaque-token-shape',violations('https://other.example/articles/'+public))
        secret='sk-'+'x'*30
        self.assertIn('credential-shape',violations('https://news.google.com/rss/articles/'+secret))

    def test_render_escapes_and_places_attribution(self):
        row=media.parse_feed(feed(item(title='Fritts <script>claim</script>')),MEMBER,CONFIG,NOW)[0]
        row['title']='<script>untrusted</script>'
        html=BeautifulSoup(media_section({**MEMBER,'media_reports':[row],'media_health':{'source_status':'ok','inference_status':'complete'}}),'html.parser')
        self.assertIsNone(html.find('script'))
        self.assertIn('Shaw Local',html.get_text())
        self.assertIn('via Google News',html.get_text())

    def test_apply_keeps_prior_screened_news_on_failure_prunes_expiry_and_rejects_false(self):
        row=media.parse_feed(feed(item()),MEMBER,CONFIG,NOW)[0]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            media.save(root/'config/media.json',CONFIG)
            media.save(root/'data/dashboard.json',{'members':[{**MEMBER,'media_reports':[row]}]})
            media.save(root/'data/media-state.json',{'members':{'fritts':{'status':'failed','candidates':[]}}})
            media.save(root/'data/media-inference-report.json',{'status':'blocked','decisions':{}})
            media.apply(root,NOW)
            self.assertEqual(len(media.load(root/'data/dashboard.json')['members'][0]['media_reports']),1)
            media.save(root/'data/media-inference-report.json',{'status':'complete','decisions':{row['id']:False}})
            media.apply(root,NOW)
            self.assertEqual(media.load(root/'data/dashboard.json')['members'][0]['media_reports'],[])

    def test_queue_advances_past_seen_rejections_and_unknowns(self):
        raw=feed(*(item(title=f'Fritts legislative report {i}') for i in range(7)))
        rows=media.parse_feed(raw,MEMBER,CONFIG,NOW)
        seen={row['id']:'invalid' if i==0 else 'valid' for i,row in enumerate(rows[:4])}
        seen[rows[4]['id']]='reconsider'
        rejected={row['id']:False for row in rows[1:4]}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            media.save(root/'config/media.json',CONFIG)
            media.save(root/'config/dashboard.json',{'members':[MEMBER]})
            media.save(root/'data/dashboard.json',{'members':[MEMBER]})
            with patch.object(media,'fetch_feed',return_value=raw), patch.object(media.inference,'cached_statuses',return_value=seen), patch.object(media.inference,'cached_decisions',return_value=rejected), patch.object(media.inference,'prepare',return_value={'status':'prepared'}) as prepare:
                media.prepare(root,NOW)
            queued=prepare.call_args.args[1]
            self.assertEqual({row['id'] for row in queued},{row['id'] for row in rows[4:]})
            health=media.load(root/'data/dashboard.json')['members'][0]['media_health']
            self.assertEqual(health['inference_status'],'partial')
            self.assertEqual(health['lookback_days'],200)
            source=media.load(root/'data/media-state.json')['members'][MEMBER['id']]
            self.assertEqual(source['query'],CONFIG['queries'][MEMBER['id']])
            self.assertEqual(source['lookback_days'],200)

    def test_queue_continues_past_three_accepted_reports_without_changing_request_bound(self):
        raw=feed(*(item(title=f'Fritts legislative report {i}') for i in range(7)))
        rows=media.parse_feed(raw,MEMBER,CONFIG,NOW)
        accepted={row['id']:True for row in rows[:3]}
        statuses={row['id']:'valid' for row in rows[:3]}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            media.save(root/'config/media.json',CONFIG)
            media.save(root/'config/dashboard.json',{'members':[MEMBER]})
            media.save(root/'data/dashboard.json',{'members':[MEMBER]})
            with patch.object(media,'fetch_feed',return_value=raw),patch.object(media.inference,'cached_statuses',return_value=statuses),patch.object(media.inference,'cached_decisions',return_value=accepted),patch.object(media.inference,'prepare',return_value={'status':'prepared'}) as prepare:
                media.prepare(root,NOW)
            self.assertEqual({c['id'] for c in prepare.call_args.args[1]}, {r['id'] for r in rows[3:]})
            self.assertEqual(len(prepare.call_args.args[1]),CONFIG['candidates_per_member'])

    def test_apply_preserves_older_screened_articles_without_relabeling_old_source_window(self):
        row=media.parse_feed(feed(item()),MEMBER,CONFIG,NOW)[0]
        row['published_at']=(NOW-timedelta(days=120)).isoformat()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            media.save(root/'config/media.json',CONFIG)
            media.save(root/'data/dashboard.json',{'members':[{**MEMBER,'media_reports':[row],
                'media_search':{'query':'Fritts when:90d'}}]})
            media.save(root/'data/media-state.json',{'members':{'fritts':{'status':'failed','candidates':[]}}})
            media.apply(root,NOW)
            member=media.load(root/'data/dashboard.json')['members'][0]
            self.assertEqual(len(member['media_reports']),1)
            self.assertEqual(member['media_health']['lookback_days'],90)
            self.assertEqual(member['media_search']['query'],'Fritts when:90d')


if __name__=='__main__':unittest.main()
