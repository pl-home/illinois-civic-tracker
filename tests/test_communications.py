from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
from civic_tracker import communications as com
from civic_tracker import media
from civic_tracker.dashboard import communications_section, render

NOW=datetime(2026,10,17,18,tzinfo=timezone.utc)
ROOT=Path(__file__).resolve().parents[1]
CONFIG={'lookback_days':90,'name_anchors':{'fritts':['fritts']}}
SOURCE={'id':'office','members':['fritts'],'kind':'office','label':'Member office','url':'https://office.example/news','format':'senate-html'}


class CommunicationsTests(unittest.TestCase):
    def test_listing_date_is_adjacent_and_missing_date_is_not_borrowed(self):
        raw=b'<div id="press"><span class="date">October 10, 2026</span><h2 class="title"><a href="/release">Office release</a></h2><p>body</p><h2 class="title"><a href="/undated">Undated</a></h2></div>'
        result=com.parse(raw,SOURCE,CONFIG,NOW)
        self.assertEqual(len(result['items']),1)
        self.assertEqual(result['items'][0]['published_at'],'2026-10-10')
        self.assertEqual(result['items'][0]['date_precision'],'day')
        self.assertEqual(result['entries_checked'],2)
        self.assertEqual(result['rejected_entries'],1)

    def test_party_requires_name_but_member_office_does_not(self):
        raw=b'<rss><channel><item><title>New program</title><link>https://office.example/release</link><pubDate>Fri, 16 Oct 2026 12:00:00 GMT</pubDate><description>Other member statement</description></item></channel></rss>'
        source={**SOURCE,'format':'rss'}
        self.assertEqual(len(com.parse(raw,source,CONFIG,NOW)['items']),1)
        self.assertEqual(com.parse(raw,{**source,'kind':'party','require_name':True},CONFIG,NOW)['items'],[])
        named=raw.replace(b'Other member',b'Rep. Fritts')
        self.assertEqual(len(com.parse(named,{**source,'kind':'party','require_name':True},CONFIG,NOW)['items']),1)

    def test_wrong_host_invalid_and_future_dates_are_not_repaired(self):
        source={**SOURCE,'format':'rss'}
        raw=b'<rss><channel><item><title>Office release</title><link>https://office.example/release</link><pubDate>Wed, 280 Oct 2026 12:00:00 EST</pubDate></item><item><title>Future</title><link>https://office.example/future</link><pubDate>Sun, 18 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'
        result=com.parse(raw,source,CONFIG,NOW)
        self.assertEqual(result['items'],[])
        self.assertEqual(result['rejected_entries'],2)
        self.assertEqual(com.safe_link('https://other.example/release',SOURCE),'')
        self.assertEqual(com.safe_link('javascript:alert(1)',SOURCE),'')
        self.assertEqual(com.safe_link('',SOURCE),'')
        self.assertEqual(com.safe_link('#comments',SOURCE),'')
        self.assertEqual(com.safe_link('/news',SOURCE),'')
        self.assertEqual(com.safe_link('https://office.example/?p=12',SOURCE),'https://office.example/?p=12')

    def test_failed_source_retains_prior_items_without_touching_inference(self):
        source={**SOURCE,'format':'rss'}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            media.save(root/'config/communications.json',{'sources':[source],'max_sources':16,'lookback_days':90,'max_per_kind':3})
            media.save(root/'config/media.json',{'name_anchors':CONFIG['name_anchors']})
            media.save(root/'data/dashboard.json',{'members':[{'id':'fritts','name':'Bradley Fritts'}]})
            row={'id':'sample','member_id':'fritts','title':'Release','url':'https://office.example/release','published_at':'2026-10-10','kind':'office','publisher':'Member office','publisher_host':'office.example'}
            media.save(root/'data/communications-state.json',{'sources':{'office':{'items':[row]}}})
            ledger=root/'data/media-inference-ledger.json';media.save(ledger,{'unchanged':True});before=ledger.read_bytes()
            with patch.object(com,'fetch',side_effect=RuntimeError):report=com.collect(root,NOW)
            self.assertEqual(ledger.read_bytes(),before)
            self.assertEqual(report['model_calls'],0)
            result=media.load(root/'data/dashboard.json')['members'][0]
            self.assertTrue(result['communications'][0]['retained_after_failure'])
            self.assertEqual(result['communication_sources'][0]['status'],'failed')

    def test_partial_listing_retains_old_entries_and_marks_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            media.save(root/'config/communications.json',{'sources':[SOURCE],'max_sources':16,'lookback_days':90,'max_per_kind':3})
            media.save(root/'config/media.json',{'name_anchors':CONFIG['name_anchors']})
            media.save(root/'data/dashboard.json',{'members':[{'id':'fritts','name':'Bradley Fritts'}]})
            row={'id':'sample','member_id':'fritts','title':'Prior release','url':'https://office.example/previous','published_at':'2026-10-10','kind':'office','publisher':'Member office','publisher_host':'office.example'}
            media.save(root/'data/communications-state.json',{'sources':{'office':{'items':[row]}}})
            raw=b'<div id="press"><span class="date">October 15, 2026</span><h2 class="title"><a href="/new">New release</a></h2><p>body</p><h2 class="title"><a href="/previous">Prior release</a></h2></div>'
            with patch.object(com,'fetch',return_value=raw):report=com.collect(root,NOW)
            self.assertEqual(report['sources']['office'],'partial')
            result=media.load(root/'data/dashboard.json')['members'][0]
            self.assertEqual(len(result['communications']),2)
            self.assertTrue(next(row for row in result['communications'] if row['id']=='sample')['retained_after_failure'])

    def test_sections_are_separate_and_searches_are_visible(self):
        page,_=render(ROOT);soup=BeautifulSoup(page,'html.parser')
        self.assertEqual(len(soup.select('.member-communications')),5)
        for card in soup.select('.member-card'):
            self.assertIsNotNone(card.select_one('.member-communications h4'))
            self.assertFalse(card.select_one('.member-media').select('.communication-row'))


if __name__=='__main__':unittest.main()
