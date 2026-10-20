"""Member history must preserve the accepted-fact gate, chronology and privacy."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
from civic_tracker.changes import digest, semantic
from civic_tracker.dashboard import render
from civic_tracker.member_history import accepted_rows, build_pages, filename, row_html, PAGE_SIZE

ROOT = Path(__file__).resolve().parents[1]


class MemberHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads((ROOT/'data/dashboard.json').read_text())
        cls.ledger = json.loads((ROOT/'data/change-ledger.json').read_text())
        cls.pages, cls.report = build_pages(ROOT, cls.snapshot)

    def test_every_banner_and_more_link_lead_to_real_member_page(self):
        page = BeautifulSoup(render(ROOT)[0], 'html.parser')
        for member in self.snapshot['members']:
            card = page.select_one('#member-'+member['id'])
            for link in (card.select_one('h2 a'), card.select_one('.member-history-link')):
                self.assertEqual(link['href'], filename(member['id']))
                self.assertIn(link['href'], self.pages)

    def test_pages_exhaust_existing_history_once_with_order_and_valid_navigation(self):
        for member in self.snapshot['members']:
            ident = member['id']
            dated, undated, _ = accepted_rows(self.ledger, ident, self.snapshot['as_of'])
            self.assertGreater(len(dated), 5)
            for is_undated, rows in ((False, dated), (True, undated)):
                seen = []; number = 1
                while True:
                    page = BeautifulSoup(self.pages[filename(ident, number, is_undated)], 'html.parser')
                    actual = page.select('#history .activity-row')
                    self.assertLessEqual(len(actual), PAGE_SIZE)
                    seen.extend(r['id'] for r in actual)
                    self.assertIn(member['name'], page.h1.get_text())
                    for kind in ('facebook', 'campaign'):
                        self.assertIsNotNone(page.select_one('a[href="'+member['public_links'][kind]['url']+'"]'))
                    self.assertIsNone(page.find('script'))  # Works with scripts disabled.
                    for link in page.select('a[href^="member-"]'):
                        self.assertTrue(link['href'].split('#')[0] in self.pages,link['href'])
                        self.assertTrue(link['href'].startswith('member-'+ident))
                    if not page.select_one('.history-pagination a[rel="next"]'): break
                    number += 1
                self.assertEqual(seen, [r['id'] for r in rows])
                self.assertEqual(len(seen), len(set(seen)))
            self.assertTrue(all(r['fact']['occurred_at'][:10] <= self.snapshot['as_of'] for r in dated))
            self.assertLess(self.report['members'][ident]['earliest'], self.snapshot['recent_start'])

    def test_unknown_cosponsorship_dates_never_enter_dated_timeline(self):
        dated, undated, _ = accepted_rows(self.ledger, 'durbin', self.snapshot['as_of'])
        self.assertTrue(undated)
        self.assertTrue(all(r['fact']['occurred_at'] is None for r in undated))
        self.assertFalse(any(r['fact'].get('role') == 'cosponsored' for r in dated))
        html = BeautifulSoup(self.pages[filename('durbin', undated=True)], 'html.parser')
        self.assertIn('Date unknown', html.select_one('#history').get_text())
        self.assertIn('do not establish when a cosponsorship began or ended', html.get_text())

    def test_every_member_history_page_has_200_day_news_column(self):
        for name,html in self.pages.items():
            if '-news' in name: continue
            page=BeautifulSoup(html,'html.parser')
            columns=page.select_one('.member-history-columns')
            self.assertIsNotNone(columns.select_one('#history'),name)
            news=columns.select_one('aside.history-news .member-media')
            self.assertIsNotNone(news,name)
            self.assertIn('last 200 days',news.get_text(),name)
            self.assertLessEqual(len(news.select('.media-row')),5,name)
            self.assertIsNotNone(news.select_one('details.news-method'),name)
            self.assertIsNotNone(columns.select_one('.news-pagination'),name)

    def test_tampered_fingerprint_wrong_session_unsafe_url_and_identity_are_withheld(self):
        candidate = next((k, s) for k,s in self.ledger['facts'].items()
                         if s['fact']['kind']=='sponsor-role' and 'fritts' in s['fact']['members'])
        key, original = candidate
        cases = [lambda s:s.update(fingerprint='0'*64),
                 lambda s:s['fact'].update(session=105),
                 lambda s:s['fact']['evidence'].update(url='javascript:alert(1)'),
                 lambda s:s['fact'].update(key='wrong-key')]
        for mutate in cases:
            stored=deepcopy(original); mutate(stored)
            if stored['fingerprint'] != '0'*64: stored['fingerprint']=digest(semantic(stored['fact']))
            ledger={'facts':{key:stored}, 'scopes':self.ledger['scopes']}
            dated, undated, rejected=accepted_rows(ledger,'fritts',self.snapshot['as_of'])
            self.assertEqual((dated,undated,rejected),([],[],1))

    def test_removed_roles_remain_history_and_do_not_get_an_invented_date(self):
        key, stored = next((k,deepcopy(s)) for k,s in self.ledger['facts'].items()
                           if s['fact']['kind']=='sponsor-role' and 'durbin' in s['fact']['members'])
        stored['active']=False
        stored['fact'].update(operation='removed',detail='No longer in the complete source list; effective removal date unknown.')
        stored['fingerprint']=digest(semantic(stored['fact']))
        rows=accepted_rows({'facts':{key:stored},'scopes':self.ledger['scopes']},'durbin',self.snapshot['as_of'])
        self.assertEqual(len(rows[1]),1)
        self.assertIn('Removed',row_html(rows[1][0]))
        self.assertIn('Date unknown',row_html(rows[1][0]))

    def test_future_actions_are_excluded_and_related_actions_keep_attribution(self):
        dated, _, _ = accepted_rows(self.ledger,'fritts','2025-02-01')
        self.assertTrue(dated)
        self.assertTrue(all(r['fact']['occurred_at'][:10]<='2025-02-01' for r in dated))
        row=next(r for r in dated if r['fact']['kind']=='bill-action')
        self.assertIn('not necessarily an action by',row_html(row))

    def test_source_text_is_escaped_and_source_dates_remain_visible(self):
        dated, _, _ = accepted_rows(self.ledger,'fritts',self.snapshot['as_of'])
        row=deepcopy(dated[0]); row['fact']['title']='<script>bad()</script>'
        row['fact']['detail']='<img src=x onerror=bad()>'
        page=BeautifulSoup(row_html(row),'html.parser')
        self.assertIsNone(page.find('script')); self.assertIsNone(page.find('img'))
        self.assertIn(row['fact']['detail'],page.get_text())
        self.assertIn('Source checked '+row['fact']['evidence']['retrieved_at'][:10],page.get_text())

    def test_health_failure_and_size_growth_are_explicit(self):
        snapshot=deepcopy(self.snapshot)
        snapshot['daily_refresh']['sources']['Federal']['status']='failed'
        pages,_=build_pages(ROOT,snapshot)
        self.assertIn('Source coverage is incomplete',pages[filename('durbin')])
        with patch('civic_tracker.member_history.MAX_HISTORY_BYTES',10):
            with self.assertRaisesRegex(ValueError,'size-budget'):build_pages(ROOT,self.snapshot)
        with patch('civic_tracker.member_history.MAX_PAGES',1):
            with self.assertRaisesRegex(ValueError,'page-budget'):build_pages(ROOT,self.snapshot)

    def test_filename_rejects_unknown_members_and_path_traversal(self):
        for ident in ('../private','unknown'):
            with self.assertRaises(ValueError):filename(ident)
        for number in (0,-1,101,True):
            with self.assertRaises(ValueError):filename('fritts',number)


if __name__=='__main__':unittest.main()
