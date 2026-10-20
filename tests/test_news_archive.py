from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup
from civic_tracker import media, news_archive
from civic_tracker.member_history import build_pages, news_filename

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026,10,20,14,tzinfo=timezone.utc)
MEMBER = {'id':'fritts','name':'Bradley Fritts','office':'Illinois House · District 74',
          'jurisdiction':'IL','url':'https://ilga.gov/House/Members/Details/3428',
          'media_health':{'checked_at':NOW.isoformat(),'lookback_days':200,'source_status':'ok','inference_status':'complete'}}


def report(number, age=None):
    row={'member_id':MEMBER['id'],'member_name':MEMBER['name'],'title':f'Fritts housing report {number}',
         'snippet':'Fritts discusses housing legislation.','publisher':'Shaw Local','publisher_host':'shawlocal.com',
         'url':f'https://www.shawlocal.com/news/report-{number}',
         'published_at':(NOW-timedelta(days=number if age is None else age)).isoformat(),'link_route':'publisher'}
    row['id']=hashlib.sha256((row['member_id']+'\n'+row['url']+'\n'+row['title']).encode()).hexdigest()[:24]
    return row


class NewsArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        media.save(self.root/'config/media.json',media.load(ROOT/'config/media.json'))
        (self.root/'web').mkdir();(self.root/'web/styles.css').write_text('body{color:black}')

    def accept(self, rows, value=True):
        path=self.root/'data/media-inference-cache.json'; cache=media.load(path,{})
        for row in rows:
            cache[media.inference._case_hash(media.case(row))]={'status':'valid','relevant':value}
        media.save(path,cache)

    def state(self, rows):
        return {'members':{'fritts':{'status':'ok','checked_at':NOW.isoformat(),
                'last_successful_checked_at':NOW.isoformat(),'candidates':rows}}}

    def test_more_than_three_are_retained_and_pages_exhaust_news_once_in_date_order(self):
        rows=[report(n) for n in range(12)];self.accept(rows)
        state=self.state(rows);media.save(self.root/'data/media-state.json',state)
        snapshot={'as_of':NOW.date().isoformat(),'members':[deepcopy(MEMBER)]}
        saved=news_archive.update(self.root,snapshot,state,NOW)
        self.assertEqual(len(saved['fritts']),12)
        pages,counts=build_pages(self.root,snapshot)
        self.assertEqual(counts['members']['fritts']['news_pages'],3)
        seen=[]
        for number,expected in ((1,5),(2,5),(3,2)):
            page=BeautifulSoup(pages[news_filename('fritts',number)],'html.parser')
            articles=page.select('.media-row')
            self.assertEqual(len(articles),expected)
            seen.extend(row.select_one('a')['href'] for row in articles)
            self.assertIsNone(page.find('script'))
            for link in page.select('.news-pagination a'):
                self.assertIn(link['href'].split('#')[0],pages)
            self.assertIsNotNone(page.select_one('a[rel="next"]') if number<3 else page.select_one('a[rel="prev"]'))
        self.assertEqual(seen,[r['url'] for r in rows])
        self.assertEqual(len(seen),len(set(seen)))
        card=BeautifulSoup(pages['member-fritts.html'],'html.parser')
        self.assertEqual(len(card.select('.history-news .media-row')),5)
        self.assertIn('Older coverage',card.select_one('.news-pagination').get_text())

    def test_uncached_rejected_wrong_member_tampered_identity_and_bad_urls_are_withheld(self):
        row=report(1);self.accept([row])
        for key,value in (('member_id','durbin'),('member_name','Another Person'),('id','0'*24),
                          ('url','javascript:alert(1)'),('publisher_host','campaign.example')):
            changed={**row,key:value}
            self.assertEqual(news_archive.select(self.root,MEMBER,[changed],NOW),[],key)
        self.assertEqual(news_archive.select(self.root,MEMBER,[report(2)],NOW),[])
        self.accept([row],False)
        self.assertEqual(news_archive.select(self.root,MEMBER,[row],NOW),[])

    def test_expiry_future_and_member_rolling_limit_do_not_touch_financial_history(self):
        rows=[report(n) for n in range(101)]+[report(300,201),report(301,-1)]
        self.accept(rows)
        financial=self.root/'data/media-inference-ledger.json';media.save(financial,{'batches':[{'status':'unknown','reserved_usd':'0.002'}]})
        before=financial.read_bytes()
        selected=news_archive.select(self.root,MEMBER,rows,NOW)
        self.assertEqual(len(selected),100)
        self.assertEqual(selected[-1]['id'],rows[99]['id'])
        self.assertEqual(financial.read_bytes(),before)

    def test_feed_failure_keeps_prior_source_dates_and_rejected_cache_invalidates_stored_article(self):
        row=report(1);self.accept([row]);snapshot={'members':[deepcopy(MEMBER)]}
        news_archive.update(self.root,snapshot,self.state([row]),NOW)
        failed={'members':{'fritts':{'status':'failed','checked_at':(NOW+timedelta(days=1)).isoformat(),'candidates':[]}}}
        saved=news_archive.update(self.root,snapshot,failed,NOW+timedelta(days=1))
        self.assertEqual(saved['fritts'][0]['source_checked_at'],NOW.isoformat())
        self.accept([row],False)
        self.assertEqual(news_archive.update(self.root,snapshot,failed,NOW+timedelta(days=1))['fritts'],[])

    def test_rolling_store_is_atomic_and_fails_closed_at_its_size_bound(self):
        row=report(1);self.accept([row]);snapshot={'members':[deepcopy(MEMBER)]}
        news_archive.update(self.root,snapshot,self.state([row]),NOW)
        target=self.root/'data/media-history.json';before=target.read_bytes()
        with patch.object(news_archive,'MAX_BYTES',10):
            with self.assertRaisesRegex(ValueError,'size-budget'):news_archive.update(self.root,snapshot,self.state([row]),NOW)
        self.assertEqual(target.read_bytes(),before)

    def test_news_filenames_reject_unknown_member_and_out_of_range_pages(self):
        for member,number in (('../private',1),('unknown',1),('fritts',0),('fritts',21),('fritts',True)):
            with self.assertRaises(ValueError):news_filename(member,number)


if __name__=='__main__':unittest.main()
