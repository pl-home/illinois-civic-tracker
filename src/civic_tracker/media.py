"""Bounded public news discovery; model output can select IDs, never invent metadata."""
import argparse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
import json
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from . import media_inference as inference

UA = 'IllinoisCivicTracker/1.0 (+https://github.com/pl-home/illinois-civic-tracker)'


def load(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    temporary.replace(path)


def text(value, limit=320):
    value = html.unescape(re.sub(r'<[^>]*>', ' ', value or ''))
    value = re.sub(r'\S+@\S+', '[contact omitted]', value)
    return ' '.join(value.split())[:limit]


def host(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
        return ''
    return (parsed.hostname or '').removeprefix('www.').lower()


def article_url(url, publishers):
    try:
        domain = host(url)
        parts = urlsplit(url)
        if domain == 'news.google.com' and re.fullmatch(r'/(?:rss/)?articles/[A-Za-z0-9_-]{8,2000}', parts.path):
            return urlunsplit(('https', 'news.google.com', parts.path, '', ''))
        if domain in publishers and len(parts.path.strip('/')) > 3:
            return urlunsplit(('https', parts.netloc, parts.path, '', ''))
    except ValueError:
        pass
    return ''


def parse_feed(raw, member, config, now):
    """RSS metadata only; no article-body or paywall access, no claim of exhaustiveness."""
    if len(raw) > 1_000_000 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('feed-size-or-entity-bound')
    rows, seen = [], set()
    for item in ET.fromstring(raw).findall('./channel/item')[:150]:
        try:
            source = item.find('source')
            publisher_host = host(source.attrib.get('url', '')) if source is not None else ''
            if publisher_host not in config['publishers']:
                continue
            publisher = text(source.text, 80)
            title = text(item.findtext('title'), 240)
            suffix = ' - '+publisher
            if title.endswith(suffix):
                title = title[:-len(suffix)]
            snippet = text(item.findtext('description'))
            if not title or not publisher or re.search(r'(?i)^(?:editorial|opinion|letter|letters|endorsement)\b', title):
                continue
            content = (title+' '+snippet).casefold()
            if not any(re.search(r'\b'+re.escape(name)+r'\b', content) for name in config['name_anchors'][member['id']]):
                continue
            published = parsedate_to_datetime(item.findtext('pubDate'))
            if published.tzinfo is None or not now-timedelta(days=config['lookback_days']) <= published <= now:
                continue
            url = article_url(item.findtext('link') or '', config['publishers'])
            if not url:
                continue
            dedup = re.sub(r'\W+', ' ', title.casefold()).strip()
            if dedup in seen:
                continue
            seen.add(dedup)
            ident = hashlib.sha256((member['id']+'\n'+url+'\n'+title).encode()).hexdigest()[:24]
            rows.append({'id':ident, 'member_id':member['id'], 'member_name':member['name'],
                'title':title, 'snippet':snippet, 'publisher':publisher, 'publisher_host':publisher_host,
                'url':url, 'published_at':published.astimezone(timezone.utc).isoformat(),
                'link_route':'Google News' if host(url)=='news.google.com' else 'publisher'})
        except (ValueError, TypeError, AttributeError, OverflowError):
            continue
    return sorted(rows, key=lambda row:row['published_at'], reverse=True)[:30]


def fetch_feed(query):
    url = 'https://news.google.com/rss/search?'+urlencode({'q':query,'hl':'en-US','gl':'US','ceid':'US:en'})
    request = Request(url, headers={'User-Agent':UA})
    with urlopen(request, timeout=30) as response:
        if host(response.url) != 'news.google.com':
            raise ValueError('unexpected-feed-host')
        return response.read(1_000_001)


def case(row):
    return {key:row[key] for key in ('id','member_id','member_name','title','snippet')}


def check_size(root):
    if sum(path.stat().st_size for path in (root/'data').glob('*.json')) > 20_000_000:
        raise RuntimeError('public-data-size-budget-exceeded')


def prepare(root, now):
    config = load(root/'config/media.json')
    members = load(root/'config/dashboard.json')['members']
    previous = load(root/'data/media-state.json', {'members':{}})
    state = {'schema_version':1, 'checked_at':now.isoformat(), 'members':{}}
    cases = []
    for member in members:
        ident = member['id']
        try:
            rows = parse_feed(fetch_feed(config['queries'][ident]), member, config, now)
            receipt = {'status':'ok','checked_at':now.isoformat(),'candidates':rows,
                       'query':config['queries'][ident], 'lookback_days':config['lookback_days'],
                       'last_successful_checked_at':now.isoformat()}
        except Exception:
            rows = previous['members'].get(ident, {}).get('candidates', [])
            rows = [row for row in rows if now-timedelta(days=config['lookback_days']) <= datetime.fromisoformat(row['published_at']) <= now]
            receipt = {'status':'failed','checked_at':now.isoformat(),'error':'feed-unavailable-or-invalid','candidates':rows,
                       'query':config['queries'][ident], 'lookback_days':config['lookback_days'],
                       'last_successful_checked_at':previous['members'].get(ident,{}).get('last_successful_checked_at') or
                           (previous['members'].get(ident,{}).get('checked_at') if previous['members'].get(ident,{}).get('status')=='ok' else None)}
        state['members'][ident] = receipt
        all_cases = [case(row) for row in rows]
        inference.carry_forward_positives(root, all_cases)
        statuses = inference.cached_statuses(root, all_cases)
        known = inference.cached_decisions(root, all_cases)
        queued = 0
        for candidate in all_cases:
            if candidate['id'] not in known and statuses.get(candidate['id']) in (None, 'reconsider') and queued < config['candidates_per_member']:
                cases.append(candidate); queued += 1
    save(root/'data/media-state.json', state)
    from . import communications
    if (root/'config/communications.json').exists():communications.collect(root,now)
    report = inference.prepare(root, cases, now)
    check_size(root)
    apply(root, now)
    return {'status':report['status'],'candidates':len(cases),'sources':{k:v['status'] for k,v in state['members'].items()}}


def apply(root, now):
    config = load(root/'config/media.json')
    state = load(root/'data/media-state.json', {'members':{}})
    report = load(root/'data/media-inference-report.json', {})
    decisions = report.get('decisions', {})
    snapshot = load(root/'data/dashboard.json')
    from . import news_archive
    history = news_archive.update(root,snapshot,state,now)
    for member in snapshot['members']:
        source = state['members'].get(member['id'], {})
        rows = source.get('candidates', [])
        all_cases = [case(row) for row in rows]
        cached = inference.cached_decisions(root, all_cases)
        decisions_for_member = {**cached, **decisions}
        selected = [row for row in rows if decisions_for_member.get(row['id']) is True]
        selected.extend(row for row in history[member['id']] if row['id'] not in {r['id'] for r in selected})
        # Preserve previously screened rows through temporary source/model failure.
        known = {row['id'] for row in selected}
        for row in member.get('media_reports', []):
            if row['id'] not in known and row['id'] not in decisions_for_member:
                selected.append(row); known.add(row['id'])
        selected = [row for row in selected if now-timedelta(days=config['lookback_days']) <= datetime.fromisoformat(row['published_at']) <= now]
        selected.sort(key=lambda row:row['published_at'], reverse=True)
        member['media_reports'] = [{k:v for k,v in row.items() if k not in ('snippet','member_id','member_name')} for row in selected[:config['max_items']]]
        statuses = inference.cached_statuses(root,all_cases)
        pending = sum(row['id'] not in decisions_for_member and statuses.get(row['id']) in (None,'reconsider') for row in rows)
        withheld = sum(row['id'] not in decisions_for_member and statuses.get(row['id']) not in (None,'reconsider') for row in rows)
        member['media_health'] = {'source_status':source.get('status','unavailable'),
            'checked_at':source.get('checked_at'), 'inference_status':'partial' if pending or withheld else 'complete',
            'pending_candidates':pending, 'withheld_candidates':withheld,
            'screened_history_count':len(history[member['id']]),
            'lookback_days':source.get('lookback_days',90)}
        query=source.get('query', member.get('media_search', {}).get('query', config['queries'].get(member['id'],'')))
        member['media_search']={'query':query,
            'search_url':'https://news.google.com/search?'+urlencode({'q':query,'hl':'en-US','gl':'US','ceid':'US:en'}),
            'feed_url':'https://news.google.com/rss/search?'+urlencode({'q':query,'hl':'en-US','gl':'US','ceid':'US:en'}),
            'candidate_count':len(rows),
            'publisher_policy_url':'https://github.com/pl-home/illinois-civic-tracker/blob/main/config/media.json'}
    save(root/'data/dashboard.json', snapshot)
    from . import communications
    communications.apply(root,now)
    from . import usage
    usage.apply(root,now)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare','execute','refresh-communications','refresh-usage'])
    args = parser.parse_args(); root = Path.cwd(); now = datetime.now(timezone.utc)
    if args.command == 'prepare':
        report = prepare(root, now)
    elif args.command=='refresh-usage':
        from . import usage
        report=usage.apply(root,now)
        check_size(root)
    elif args.command=='refresh-communications':
        from . import communications
        report=communications.collect(root,now)
        apply(root,now)
        check_size(root)
    else:
        check_size(root)
        report = inference.execute(root, now)
        apply(root, now)
        report = {k:report[k] for k in ('status','model_calls','costs') if k in report}
    print(json.dumps(report))


if __name__ == '__main__':
    main()
