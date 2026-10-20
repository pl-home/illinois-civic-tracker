"""Small rolling news display cache, bound to exact accepted screening cases."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re

from . import media

MAX_REPORTS = 100
MAX_BYTES = 1_000_000


def coverage(root, source):
    cases = [media.case(row) for row in source.get('candidates',[])]
    known = media.inference.cached_decisions(root,cases)
    statuses = media.inference.cached_statuses(root,cases)
    pending = sum(c['id'] not in known and statuses.get(c['id']) in (None,'reconsider') for c in cases)
    withheld = sum(c['id'] not in known and statuses.get(c['id']) not in (None,'reconsider') for c in cases)
    return {'pending_candidates':pending,'withheld_candidates':withheld,
            'inference_status':'partial' if pending or withheld else 'complete'}


def reference(member, as_of):
    values = []
    for value in (as_of, member.get('media_health', {}).get('checked_at')):
        if value:
            stamp = datetime.fromisoformat(value)
            if stamp.tzinfo is None:
                stamp = stamp.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            values.append(stamp)
    return max(values)


def select(root, member, rows, now):
    """Never promote an unscreened row or a wrong-member/cache identity."""
    config = media.load(root/'config/media.json')
    valid = []
    for row in rows:
        try:
            case = media.case(row)
            media.inference._validate_case(case)
            expected = hashlib.sha256((member['id']+'\n'+row['url']+'\n'+row['title']).encode()).hexdigest()[:24]
            published = datetime.fromisoformat(row['published_at'])
            if (case['member_id'] != member['id'] or case['member_name'] != member['name']
                    or case['id'] != expected or row.get('publisher_host') not in config['publishers']
                    or not isinstance(row.get('publisher'),str) or not 1 <= len(row['publisher']) <= 80
                    or media.article_url(row['url'],config['publishers']) != row['url']
                    or published.tzinfo is None or not now-timedelta(days=200) <= published <= now):
                continue
            valid.append(row)
        except (KeyError, TypeError, ValueError, media.inference.MediaError):
            continue
    decisions = media.inference.cached_decisions(root, [media.case(r) for r in valid])
    # Source observations win ties, but their dates are not publication dates.
    valid.sort(key=lambda r:(r['published_at'],r.get('source_checked_at') or '',r['id']),reverse=True)
    result = []; urls = set(); headlines = set()
    for row in valid:
        headline = re.sub(r'\W+',' ',row['title'].casefold()).strip()
        if decisions.get(row['id']) is not True or row['url'] in urls or headline in headlines:
            continue
        urls.add(row['url']); headlines.add(headline)
        result.append({key:row[key] for key in ('id','member_id','member_name','title','snippet','publisher',
                      'publisher_host','url','published_at','link_route','source_checked_at') if key in row})
    return result[:MAX_REPORTS]


def reports(root, member, as_of, archive=None, state=None):
    archive = archive if archive is not None else media.load(root/'data/media-history.json', {'members':{}})
    state = state if state is not None else media.load(root/'data/media-state.json', {'members':{}})
    prior = archive['members'].get(member['id'],{}).get('reports',[])
    source = state['members'].get(member['id'],{})
    checked = (source.get('last_successful_checked_at') or
               (source.get('checked_at') if source.get('status') == 'ok' else None))
    by_id = {r['id']:r for r in prior}
    for row in source.get('candidates',[]):
        if source.get('status') != 'ok' and row['id'] in by_id:
            continue  # A failed attempt cannot refresh retained evidence dates.
        by_id[row['id']] = {**row,'source_checked_at':checked}
    return select(root,member,list(by_id.values()),reference(member,as_of))


def update(root, snapshot, state, now):
    archive = media.load(root/'data/media-history.json', {'schema_version':1,'members':{}})
    result = {'schema_version':1,'lookback_days':200,'max_reports_per_member':MAX_REPORTS,
              'checked_at':now.isoformat(),'members':{}}
    for member in snapshot['members']:
        selected = reports(root,member,now.isoformat(),archive,state)
        result['members'][member['id']] = {'reports':selected}
    content = json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n'
    other_bytes = sum(p.stat().st_size for p in (root/'data').glob('*.json') if p.name!='media-history.json')
    if len(content.encode()) > MAX_BYTES or other_bytes+len(content.encode()) > 20_000_000:
        raise ValueError('news-history-size-budget-exceeded')
    target = root/'data/media-history.json'; temporary = target.with_suffix('.tmp')
    temporary.write_text(content,encoding='utf-8',newline='\n'); temporary.replace(target)
    return {member:row['reports'] for member,row in result['members'].items()}
