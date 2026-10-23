"""Dated first-party metadata; source ownership determines attribution without a model."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import re
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
import ssl
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from .media import load, save, text, host, UA

KINDS = {'office':'Member office', 'campaign':'Campaign', 'party':'Party/caucus'}


def safe_link(url, source):
    """Only links on the reviewed publishing host; preserve a numeric WP post query."""
    if not isinstance(url,str) or not url.strip() or url.strip().startswith('#'):
        return ''
    url = urljoin(source['url'], url)
    try:
        parts = urlsplit(url)
        if host(url) != host(source['url']):
            return ''
        query = parts.query if re.fullmatch(r'p=\d{1,10}', parts.query) else ''
        if not parts.path.strip('/') and not query:
            return ''
        if any(parts.path.rstrip('/')==urlsplit(value).path.rstrip('/') and not query
               for value in (source['url'],source.get('listing_url',source['url']))):
            return ''
        return urlunsplit(('https', parts.netloc, parts.path, query, ''))
    except ValueError:
        return ''


def source_entries(raw, source):
    """Return title/link/date/brief-match-text; never infer missing dates."""
    if len(raw) > 1_000_000:
        raise ValueError('source-size-bound')
    fmt = source['format']
    entries = []
    if fmt == 'rss':
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('unsafe-feed-entities')
        channel = ET.fromstring(raw).find('channel')
        if channel is None:
            raise ValueError('unexpected-feed-structure')
        for item in channel.findall('item')[:100]:
            entries.append((item.findtext('title'), item.findtext('link'), item.findtext('pubDate'),
                text(item.findtext('description'), 3000), 'rss'))
    else:
        soup = BeautifulSoup(raw, 'html.parser')
        if fmt == 'fritts-html':
            for block in soup.select('.post-preview-details')[:40]:
                link = block.select_one('.post-preview-title a'); date = block.select_one('.post-preview-date')
                entries.append((link.get_text(' ',strip=True) if link else '', link.get('href') if link else None, date.get_text(' ',strip=True) if date else None, '', '%A, %B %d, %Y'))
        elif fmt == 'lahood-html':
            for block in soup.select('tr')[:120]:
                link = block.select_one('.recordListTitle a'); date = block.select_one('.recordListDate')
                if block.select_one('.recordListTitle,.recordListDate'):
                    entries.append((link.get_text(' ',strip=True) if link else '', link.get('href') if link else None, date.get_text(' ',strip=True) if date else None, '', '%m/%d/%y'))
        elif fmt == 'senate-html':
            for heading in soup.select('#press h2.title')[:50]:
                link = heading.select_one('a'); date = heading.find_previous_sibling()
                if not date or date.name!='span' or 'date' not in date.get('class',[]):date=None
                entries.append((link.get_text(' ',strip=True) if link else '', link.get('href') if link else None, date.get_text(' ',strip=True) if date else None, '', '%B %d, %Y'))
        elif fmt == 'party-html':
            for block in soup.select('.ArticleBlock')[:50]:
                link = block.select_one('a.ArticleTitle'); date = block.select_one('.Heading--time')
                snippet = block.select_one('.ArticleBlock__excerpt')
                entries.append((link.get_text(' ',strip=True) if link else '', link.get('href') if link else None, date.get_text(' ',strip=True) if date else None, text(snippet.get_text(' ',strip=True) if snippet else '',3000), '%m.%d.%Y'))
        else:
            raise ValueError('unreviewed-source-format')
        if not entries:
            raise ValueError('listing-structure-not-recognized')
    return entries


def parse(raw, source, config, now):
    entries = source_entries(raw, source)
    records=[]; rejected=0; seen=set(); latest=None
    for title, url, date, snippet, fmt in entries:
        try:
            title = text(title,240)
            url = safe_link(url or '',source)
            if not title or not url:
                raise ValueError('missing-metadata')
            published = parsedate_to_datetime(date) if fmt=='rss' else datetime.strptime(date,fmt)
            if fmt=='rss' and published.tzinfo is None:
                raise ValueError('missing-timezone')
            if fmt=='rss':
                if published>now:raise ValueError('future-date')
                published=published.astimezone(timezone.utc)
                published_at=published.isoformat()
            else:
                if published.date()>now.date():raise ValueError('future-date')
                published_at=published.date().isoformat()
            latest = max(latest or '',published_at[:10])
            if published.date() < (now-timedelta(days=config['lookback_days'])).date():
                continue
            for member_id in source['members']:
                anchors=config['name_anchors'][member_id]
                if source.get('require_name') and not any(re.search(r'\b'+re.escape(name)+r'\b',(title+' '+snippet).casefold()) for name in anchors):
                    continue
                key = (member_id,url)
                if key in seen:continue
                seen.add(key)
                records.append({'id':hashlib.sha256((source['id']+'\n'+member_id+'\n'+url).encode()).hexdigest()[:24],
                    'member_id':member_id, 'title':title, 'url':url, 'published_at':published_at,
                    'date_precision':'timestamp' if fmt=='rss' else 'day',
                    'source_id':source['id'], 'publisher':source['label'], 'kind':source['kind'],
                    'publisher_host':host(source['url']), 'source_url':source.get('listing_url',source['url'])})
        except (ValueError, TypeError, AttributeError, OverflowError):
            rejected+=1
    return {'items':sorted(records,key=lambda row:row['published_at'],reverse=True)[:60],
        'entries_checked':len(entries), 'rejected_entries':rejected, 'latest_source_date':latest}


class PublisherRedirect(HTTPRedirectHandler):
    def __init__(self, expected):self.expected=expected

    def redirect_request(self, request, fp, code, message, headers, newurl):
        if host(newurl)!=self.expected:
            raise ValueError('unexpected-publisher-redirect')
        return super().redirect_request(request,fp,code,message,headers,newurl)


def fetch(source):
    expected=host(source['url'])
    if not expected:raise ValueError('invalid-source-url')
    opener=build_opener(PublisherRedirect(expected))
    with opener.open(Request(source['url'],headers={'User-Agent':UA}),timeout=25) as response:
        if host(response.url)!=host(source['url']):
            raise ValueError('unexpected-publisher-redirect')
        return response.read(1_000_001)


def safe_failure(exc):
    """Return a bounded category/code without exposing provider text or URLs."""
    if isinstance(exc, HTTPError):
        code = exc.code if isinstance(exc.code, int) and 100 <= exc.code <= 599 else 0
        return {'category': 'http', 'code': f'HTTP_{code}' if code else 'HTTP_ERROR'}
    if isinstance(exc, ssl.SSLError):
        return {'category': 'tls', 'code': 'TLS_ERROR'}
    if isinstance(exc, TimeoutError):
        return {'category': 'timeout', 'code': 'TIMEOUT'}
    if isinstance(exc, URLError):
        reason = getattr(exc, 'reason', None)
        if isinstance(reason, TimeoutError):
            return {'category': 'timeout', 'code': 'TIMEOUT'}
        if isinstance(reason, ssl.SSLError):
            return {'category': 'tls', 'code': 'TLS_ERROR'}
        return {'category': 'transport', 'code': 'TRANSPORT_ERROR'}
    if isinstance(exc, ValueError):
        return {'category': 'parse', 'code': 'PARSE_ERROR'}
    return {'category': 'collection', 'code': 'COLLECTION_ERROR'}


def collect(root,now):
    config=load(root/'config/communications.json')
    news_config=load(root/'config/media.json')
    config['name_anchors']=news_config['name_anchors']
    if len(config['sources'])>min(config['max_sources'],16):
        raise ValueError('source-count-bound')
    previous=load(root/'data/communications-state.json',{'sources':{}})
    state={'schema_version':1,'checked_at':now.isoformat(),'sources':{}}
    for source in config['sources']:
        if source['kind'] not in KINDS:
            raise ValueError('unreviewed-publisher-kind')
        if source['format']=='link-only':
            result={'status':'link-only','items':[],'note':source['note']}
        else:
            try:
                result=parse(fetch(source),source,config,now)
                result['status']='partial' if result['rejected_entries'] else 'ok'
                if result['status']=='partial':
                    known={row['id'] for row in result['items']}
                    for row in previous['sources'].get(source['id'],{}).get('items',[]):
                        if row['id'] not in known and (now-timedelta(days=config['lookback_days'])).date().isoformat()<=row['published_at'][:10]<=now.date().isoformat():
                            result['items'].append({**row,'retained_after_failure':True})
                    result['items']=sorted(result['items'],key=lambda row:row['published_at'],reverse=True)[:60]
            except Exception as exc:
                old=previous['sources'].get(source['id'],{})
                items=[{**row,'retained_after_failure':True} for row in old.get('items',[])
                    if (now-timedelta(days=config['lookback_days'])).date().isoformat()<=row['published_at'][:10]<=now.date().isoformat()]
                failure=safe_failure(exc)
                result={'status':'failed','items':items,'error':'source-unavailable-or-listing-changed',
                    'error_category':failure['category'],'error_code':failure['code'],
                    'latest_source_date':old.get('latest_source_date')}
        result.update(checked_at=now.isoformat(),label=source['label'],kind=source['kind'],members=source['members'],
            source_url=source.get('listing_url',source['url']),note=source.get('note',result.get('note','')))
        state['sources'][source['id']]=result
    save(root/'data/communications-state.json',state)
    apply(root,now)
    return {'sources':{key:record['status'] for key,record in state['sources'].items()},'model_calls':0}


def apply(root,now):
    config=load(root/'config/communications.json',None)
    if not config:return
    state=load(root/'data/communications-state.json',{'sources':{}})
    snapshot=load(root/'data/dashboard.json')
    for member in snapshot['members']:
        sources=[source for source in config['sources'] if member['id'] in source['members']]
        receipts=[]; items=[]
        for source in sources:
            receipt=state['sources'].get(source['id'],{})
            receipts.append({'id':source['id'],'publisher':source['label'],'kind':source['kind'],
                'url':source.get('listing_url',source['url']), 'status':receipt.get('status','not-checked'),
                'checked_at':receipt.get('checked_at'), 'latest_source_date':receipt.get('latest_source_date'),
                'error_category':receipt.get('error_category'), 'error_code':receipt.get('error_code'),
                'note':receipt.get('note',source.get('note',''))})
            for row in receipt.get('items',[]):
                if row['member_id']==member['id'] and (now-timedelta(days=config['lookback_days'])).date().isoformat()<=row['published_at'][:10]<=now.date().isoformat():
                    items.append(row)
        selected=[]
        for kind in KINDS:
            group=sorted((row for row in items if row['kind']==kind),key=lambda row:row['published_at'],reverse=True)
            seen=set()
            for row in group:
                key=(row['publisher_host'],re.sub(r'\W+',' ',row['title'].casefold()).strip())
                if key in seen:continue
                seen.add(key); selected.append(row)
                if len(seen)>=config['max_per_kind']:break
        member['communications']=selected
        member['communication_sources']=receipts
        member['communications_checked_at']=state.get('checked_at')
    save(root/'data/dashboard.json',snapshot)
