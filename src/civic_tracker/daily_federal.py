"""Bounded daily refresh of Congress.gov member lists and official roll calls.

The caller owns persistence. This module returns normalized data and a compact
health report, retaining prior source facts whenever that source is incomplete.
"""
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import html
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
import xml.etree.ElementTree as ET


CONGRESS = 119
MEMBERS = {
    'L000585': ('Darin LaHood', 'House', None),
    'D000563': ('Richard J. Durbin', 'Senate', 'S253'),
    'D000622': ('Tammy Duckworth', 'Senate', 'S386'),
}
API_HOST = 'api.congress.gov'
HOUSE_HOST = 'clerk.house.gov'
SENATE_HOST = 'www.senate.gov'
API_BASE = f'https://{API_HOST}/v3'
MAX_API_ATTEMPTS = 500
MAX_VOTE_REQUESTS = 100
MAX_BYTES = 2_000_000
CHOICES = {'Yea': 'yes', 'Aye': 'yes', 'Nay': 'no', 'No': 'no',
           'Present': 'present', 'Not Voting': 'not-voting',
           'Guilty': 'guilty', 'Not Guilty': 'not-guilty'}
BILL_TYPES = {'HR': 'house-bill', 'S': 'senate-bill', 'HRES': 'house-resolution',
              'SRES': 'senate-resolution', 'HJRES': 'house-joint-resolution',
              'SJRES': 'senate-joint-resolution', 'HCONRES': 'house-concurrent-resolution',
              'SCONRES': 'senate-concurrent-resolution'}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('redirect refused')


def _stamp(now):
    return now.astimezone(timezone.utc).isoformat()


def _safe_source(url):
    p = urlsplit(url)
    if p.netloc == API_HOST:
        return 'Congress.gov API'
    return f'{p.scheme}://{p.netloc}{p.path}'


def _clean_next(url):
    p = urlsplit(url)
    if p.scheme != 'https' or p.netloc != API_HOST or not p.path.startswith('/v3/'):
        raise ValueError('unsafe pagination link')
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if k.casefold() not in ('api_key', 'apikey')]
    return urlunsplit(('https', API_HOST, p.path, urlencode(query), ''))


def _url_id(congress, typ, number):
    types = dict(BILL_TYPES)
    types.update(HAMDT='house-amendment', SAMDT='senate-amendment')
    if typ not in types:
        return None
    return f'https://www.congress.gov/{"amendment" if typ in ("HAMDT", "SAMDT") else "bill"}/{congress}/{types[typ]}/{number}'


def _measure_id(congress, text):
    m = re.fullmatch(r'\s*(H\s*\.?\s*CON\s*\.?\s*RES|S\s*\.?\s*CON\s*\.?\s*RES|H\s*\.?\s*J\s*\.?\s*RES|S\s*\.?\s*J\s*\.?\s*RES|H\s*\.?\s*RES|S\s*\.?\s*RES|H\s*\.?\s*R|S)\s*\.?\s*(\d+)\s*', text or '', re.I)
    if not m:
        return None
    typ = re.sub(r'[^A-Z]', '', m[1].upper())
    return f'US-{congress}-{typ}{int(m[2])}'


def _scalar(node, path):
    return (node.findtext(path) or '').strip()


def _valid_bill_date(row):
    value = row.get('introducedDate') or row.get('submittedDate')
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _safe_error(exc):
    """Return only a short allowlisted code or standard exception class."""
    code = str(exc)
    known = {
        'unsafe_source', 'unsafe pagination link', 'duplicate_pagination_url',
        'malformed_page', 'malformed_record', 'unsupported_record',
        'identity_mismatch', 'totals_missing', 'unknown_vote_label',
        'totals_mismatch', 'tracked_member_missing_or_duplicate',
        'incomplete_index', 'duplicate_index_id', 'vote_request_limit',
        'api_attempt_limit', 'source_size_limit', 'missing_api_key',
    }
    if code in known:
        return code.replace(' ', '_')
    if re.fullmatch(r'HTTP_[1-5][0-9]{2}', code):
        return code
    return type(exc).__name__


def normalize_choice(raw):
    """Normalize only exact official labels; leave new values explicitly unknown."""
    return CHOICES.get(raw, 'unknown:' + raw.strip())


def _parse_house(data, session, number, retrieved):
    root = ET.fromstring(data)
    meta = root.find('vote-metadata')
    if meta is None or int(_scalar(meta, 'congress')) != CONGRESS or int(_scalar(meta, 'rollcall-num')) != number:
        raise ValueError('identity_mismatch')
    if _scalar(meta, 'session') != {1: '1st', 2: '2nd'}[session]:
        raise ValueError('identity_mismatch')
    all_votes = root.findall('./vote-data/recorded-vote')
    totals = meta.find('./vote-totals/totals-by-vote')
    if totals is None:
        raise ValueError('totals_missing')
    expected = {k: int(_scalar(totals, p) or 0) for k, p in
                [('yes', 'yea-total'), ('no', 'nay-total'), ('present', 'present-total'), ('not-voting', 'not-voting-total')]}
    counts = Counter(normalize_choice(_scalar(v, 'vote')) for v in all_votes)
    # Unknown labels cannot be reconciled to official aggregate categories.
    if any(k.startswith('unknown:') for k in counts):
        raise ValueError('unknown_vote_label')
    if {k: v for k, v in counts.items() if v} != {k: v for k, v in expected.items() if v}:
        raise ValueError('totals_mismatch')
    choices = []
    for ident, (name, chamber, _) in MEMBERS.items():
        if chamber != 'House':
            continue
        found = [v for v in all_votes if v.find('legislator') is not None and v.find('legislator').get('name-id') == ident]
        if len(found) != 1:
            raise ValueError('tracked_member_missing_or_duplicate')
        raw = _scalar(found[0], 'vote')
        choices.append({'bioguide': ident, 'choice': normalize_choice(raw), 'raw': raw})
    dt = datetime.strptime(_scalar(meta, 'action-date'), '%d-%b-%Y').date().isoformat()
    measure = _scalar(meta, 'legis-num')
    source = f'https://clerk.house.gov/Votes/{1786 + 2 * CONGRESS + session}{number:03}'
    return {'record_id': f'US-{CONGRESS}-HOUSE-{session}-{number:05}', 'date': dt,
            'measure': measure, 'measure_id': _measure_id(CONGRESS, measure),
            'motion': _scalar(meta, 'vote-question'), 'description': _scalar(meta, 'vote-desc'),
            'source_url': source, 'verification': 'reconciled-official-xml', 'choices': choices,
            'totals': expected, 'evidence': {'retrieved_at': retrieved, 'sha256': hashlib.sha256(data).hexdigest()}}


def _parse_senate(data, session, number, retrieved):
    root = ET.fromstring(data)
    if (int(_scalar(root, 'congress')), int(_scalar(root, 'session')), int(_scalar(root, 'vote_number'))) != (CONGRESS, session, number):
        raise ValueError('identity_mismatch')
    rows = root.findall('./members/member')
    expected = {k: int(_scalar(root, p) or 0) for k, p in
                [('yes', 'count/yeas'), ('no', 'count/nays'), ('present', 'count/present'), ('not-voting', 'count/absent')]}
    counts = Counter(normalize_choice(_scalar(v, 'vote_cast')) for v in rows)
    if any(k.startswith('unknown:') for k in counts):
        raise ValueError('unknown_vote_label')
    reconciled = Counter(counts)
    reconciled['yes'] += reconciled.pop('guilty', 0)
    reconciled['no'] += reconciled.pop('not-guilty', 0)
    if {k: v for k, v in reconciled.items() if v} != {k: v for k, v in expected.items() if v}:
        raise ValueError('totals_mismatch')
    choices = []
    for ident, (name, chamber, lis) in MEMBERS.items():
        if chamber != 'Senate':
            continue
        found = [v for v in rows if _scalar(v, 'lis_member_id') == lis]
        if len(found) != 1 or _scalar(found[0], 'state') != 'IL':
            raise ValueError('tracked_member_missing_or_duplicate')
        raw = _scalar(found[0], 'vote_cast')
        choices.append({'bioguide': ident, 'choice': normalize_choice(raw), 'raw': raw})
    dt_text = re.sub(r'\s+', ' ', _scalar(root, 'vote_date'))
    dt = datetime.strptime(dt_text, '%B %d, %Y, %I:%M %p').date().isoformat()
    measure = _scalar(root, 'document/document_name') or (_scalar(root, 'document/document_type') + _scalar(root, 'document/document_number'))
    source = f'https://www.senate.gov/legislative/LIS/roll_call_votes/vote{CONGRESS}{session}/vote_{CONGRESS}_{session}_{number:05}.htm'
    return {'record_id': f'US-{CONGRESS}-SENATE-{session}-{number:05}', 'date': dt,
            'measure': measure, 'measure_id': _measure_id(CONGRESS, measure),
            'motion': _scalar(root, 'vote_question_text') or _scalar(root, 'question'),
            'description': _scalar(root, 'vote_title'), 'source_url': source,
            'verification': 'reconciled-official-xml', 'choices': choices, 'totals': expected,
            'evidence': {'retrieved_at': retrieved, 'sha256': hashlib.sha256(data).hexdigest()}}


def _copy_archive(previous):
    return {'collected_at': previous.get('collected_at'), 'bills': dict(previous.get('bills') or {}),
            'votes': dict(previous.get('votes') or {})}


def refresh(root, previous, now):
    """Fetch daily sources and return ``(archive, report)`` without disk writes."""
    del root  # Reserved for interface symmetry; no source data is read from disk.
    previous = previous or {}
    archive = _copy_archive(previous)
    report = {'status': 'ok', 'checked_at': _stamp(now), 'errors': [],
              'legislation_sources': [], 'vote_sources': [], 'unknown_records': []}
    api_attempts = 0
    vote_attempts = 0
    last_request = [0.0]
    opener = build_opener(NoRedirect())
    key = os.environ.get('CONGRESS_API_KEY', '').strip()

    def request(url, *, api=False):
        nonlocal api_attempts, vote_attempts
        host = urlsplit(url).netloc
        if host not in (API_HOST, HOUSE_HOST, SENATE_HOST):
            raise ValueError('unsafe_source')
        if api:
            if api_attempts >= MAX_API_ATTEMPTS:
                raise ValueError('api_attempt_limit')
            api_attempts += 1
        else:
            if vote_attempts >= MAX_VOTE_REQUESTS:
                raise ValueError('vote_request_limit')
            vote_attempts += 1
        delay = 1.0 - (time.monotonic() - last_request[0])
        if last_request[0] and delay > 0:
            time.sleep(delay)
        last_request[0] = time.monotonic()
        try:
            with opener.open(Request(url, headers={'User-Agent': 'Illinois Civic Tracker public data refresh'}), timeout=30) as response:
                body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError('source_size_limit')
            return body
        except HTTPError as exc:
            raise RuntimeError(f'HTTP_{exc.code}') from None
        except (URLError, TimeoutError, OSError) as exc:
            # Only the exception class is exposed; URL query and transport text stay private.
            raise RuntimeError(type(exc).__name__) from None

    if not key:
        report['errors'].append({'source': 'Congress.gov API', 'error': 'missing_api_key'})
        report['legislation_sources'].append({'complete': False, 'reason': 'missing_api_key'})
    else:
        for member, (name, _, _) in MEMBERS.items():
            for role in ('sponsored', 'cosponsored'):
                source_name = f'{member}:{role}'
                base = f'{API_BASE}/member/{member}/{role}-legislation?format=json&limit=250'
                page_url = base
                seen_urls = set()
                fresh_relations = {}
                source_error = None
                parse_incomplete = False
                complete = False
                pages = 0
                while page_url:
                    try:
                        clean = _clean_next(page_url) if page_url != base else base
                        if clean in seen_urls:
                            raise ValueError('duplicate_pagination_url')
                        seen_urls.add(clean)
                        query = list(parse_qsl(urlsplit(clean).query, keep_blank_values=True))
                        query.append(('api_key', key))
                        auth_url = urlunsplit(('https', API_HOST, urlsplit(clean).path, urlencode(query), ''))
                        payload = json.loads(request(auth_url, api=True))
                        rows_key = role + 'Legislation'
                        rows = payload.get(rows_key)
                        if not isinstance(rows, list):
                            raise ValueError('malformed_page')
                        pages += 1
                        for row in rows:
                            if not isinstance(row, dict) or not isinstance(row.get('congress'), int):
                                report['unknown_records'].append({'source': source_name, 'error': 'malformed_record'})
                                parse_incomplete = True
                                continue
                            if row['congress'] != CONGRESS:
                                continue
                            typ = str(row.get('type') or '').upper()
                            raw_number = row.get('number')
                            if row.get('amendmentNumber'):
                                typ = 'HAMDT' if '/hamdt/' in str(row.get('url', '')).lower() else ('SAMDT' if '/samdt/' in str(row.get('url', '')).lower() else '')
                                raw_number = row['amendmentNumber']
                            if typ not in (*BILL_TYPES, 'HAMDT', 'SAMDT') or not str(raw_number or '').isdigit():
                                report['unknown_records'].append({'source': source_name, 'error': 'unsupported_record'})
                                parse_incomplete = True
                                continue
                            introduced_date = _valid_bill_date(row)
                            if introduced_date is None:
                                report['unknown_records'].append({'source': source_name, 'error': 'unsupported_record'})
                                parse_incomplete = True
                                continue
                            number = str(int(raw_number))
                            ident = f'US-{CONGRESS}-{typ}{number}'
                            record = fresh_relations.setdefault(ident, {'record_id': ident,
                                'title': row.get('title') or row.get('latestTitle') or ident,
                                'introduced_date': introduced_date, 'source_url': _url_id(CONGRESS, typ, number),
                                'relations': []})
                            relation = {'member': member, 'role': 'sponsored' if role == 'sponsored' else 'cosponsored'}
                            if relation not in record['relations']:
                                record['relations'].append(relation)
                        nxt = payload.get('pagination', {}).get('next')
                        page_url = _clean_next(nxt) if nxt else None
                    except Exception as exc:
                        source_error = _safe_error(exc)
                        page_url = None
                if not source_error and parse_incomplete:
                    source_error = 'malformed_record'
                if source_error:
                    report['errors'].append({'source': 'Congress.gov API', 'error': source_error})
                if complete or (pages and not source_error):
                    for ident, bill in fresh_relations.items():
                        existing = archive['bills'].get(ident, {})
                        old_rels = [r for r in existing.get('relations', []) if not (r.get('member') == member and r.get('role') == role)]
                        bill['relations'] = old_rels + [r for r in bill['relations'] if r not in old_rels]
                        archive['bills'][ident] = bill
                    # Remove stale associations but retain the quiet bill record.
                    for ident, old_bill in list(archive['bills'].items()):
                        if ident not in fresh_relations and any(r.get('member') == member and r.get('role') == role for r in old_bill.get('relations', [])):
                            kept = [r for r in old_bill['relations'] if not (r.get('member') == member and r.get('role') == role)]
                            archive['bills'][ident] = {**old_bill, 'relations': kept}
                    complete = True
                else:
                    # Preserve the prior member/role links on incomplete paging.
                    for ident, bill in fresh_relations.items():
                        old_bill = archive['bills'].get(ident, bill)
                        rels = list(old_bill.get('relations', []))
                        rel = {'member': member, 'role': role}
                        if rel not in rels:
                            rels.append(rel)
                        archive['bills'][ident] = {**bill, **old_bill, 'relations': rels}
                report['legislation_sources'].append({'source': source_name, 'pages': pages, 'complete': complete})

    # Session two is the currently published 119th Congress session.
    session = 2
    year = 1786 + 2 * CONGRESS + session
    index_urls = {
        'House': f'https://clerk.house.gov/Votes/MemberVotes?CongressNum={CONGRESS}&Session=2nd',
        'Senate': f'https://www.senate.gov/legislative/LIS/roll_call_lists/vote_menu_{CONGRESS}_{session}.xml'}
    discovered = {}
    for chamber, url in index_urls.items():
        try:
            body = request(url)
            if chamber == 'Senate':
                menu = ET.fromstring(body)
                if (int(_scalar(menu, 'congress')), int(_scalar(menu, 'session'))) != (CONGRESS, session):
                    raise ValueError('identity_mismatch')
                nums = [int(_scalar(v, 'vote_number')) for v in menu.findall('./votes/vote')]
            else:
                text = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', body.decode('utf-8', 'replace'))).split())
                nums = [int(x) for x in re.findall(r'Roll Call Number:\s*(\d+)', text)]
                match = re.search(r'of\s+([\d,]+)\s+Results', text)
                if not match or not nums or int(match[1].replace(',', '')) != max(nums) or sorted(nums) != list(range(1, max(nums) + 1)):
                    raise ValueError('incomplete_index')
            if not nums or sorted(nums) != list(range(1, max(nums) + 1)):
                raise ValueError('incomplete_index')
            if len(nums) != len(set(nums)):
                raise ValueError('duplicate_index_id')
            discovered[chamber] = set(nums)
            report['vote_sources'].append({'source': _safe_source(url), 'complete': True, 'discovered': len(nums), 'selected': 0})
        except Exception as exc:
            code = _safe_error(exc)
            report['errors'].append({'source': _safe_source(url), 'error': code})
            report['vote_sources'].append({'source': _safe_source(url), 'complete': False, 'selected': 0})

    tasks_by_chamber = {}
    for chamber, nums in discovered.items():
        prefix = f'US-{CONGRESS}-{chamber.upper()}-{session}-'
        previous_nums = []
        for ident in archive['votes']:
            if ident.startswith(prefix):
                try: previous_nums.append(int(ident.rsplit('-', 1)[1]))
                except ValueError: pass
        chosen = set(nums - set(previous_nums)) | set(sorted((nums & set(previous_nums)), reverse=True)[:5])
        tasks_by_chamber[chamber] = []
        for number in sorted(chosen, reverse=True):
            if chamber == 'House':
                url = f'https://clerk.house.gov/evs/{year}/roll{number:03}.xml'
            else:
                url = f'https://www.senate.gov/legislative/LIS/roll_call_votes/vote{CONGRESS}{session}/vote_{CONGRESS}_{session}_{number:05}.xml'
            tasks_by_chamber[chamber].append((chamber, number, url))
    # Reserve two of the 100 vote requests for the official indexes.
    tasks = []
    capacity = max(0, MAX_VOTE_REQUESTS - vote_attempts)
    offsets = {chamber: 0 for chamber in tasks_by_chamber}
    while len(tasks) < capacity:
        advanced = False
        for chamber in ('House', 'Senate'):
            offset = offsets.get(chamber, 0)
            if offset < len(tasks_by_chamber.get(chamber, [])):
                tasks.append(tasks_by_chamber[chamber][offset])
                offsets[chamber] = offset + 1
                advanced = True
                if len(tasks) >= capacity:
                    break
        if not advanced:
            break
    pending_by_chamber = {
        chamber: max(0, len(rows) - sum(ch == chamber for ch, _, _ in tasks))
        for chamber, rows in tasks_by_chamber.items()
    }
    for item in report['vote_sources']:
        if item.get('complete'):
            chamber = 'House' if 'clerk.house.gov' in item['source'] else 'Senate'
            item['selected'] = sum(ch == chamber for ch, _, _ in tasks)
            item['pending'] = pending_by_chamber.get(chamber, 0)
            if item['pending']:
                item['complete'] = False
                report['errors'].append({'source': _safe_source(index_urls[chamber]), 'error': 'vote_request_limit'})
    parsed_by_chamber = Counter()
    for chamber, number, url in tasks:
        try:
            body = request(url)
            row = (_parse_house if chamber == 'House' else _parse_senate)(body, session, number, _stamp(now))
            archive['votes'][row['record_id']] = row
            parsed_by_chamber[chamber] += 1
        except Exception as exc:
            code = _safe_error(exc)
            report['errors'].append({'source': _safe_source(url), 'error': code})
            # Unknown/invalid records stay diagnostic and never replace last-good.
            report['unknown_records'].append({'source': _safe_source(url), 'error': code})
    for item in report['vote_sources']:
        if 'discovered' in item:
            chamber = 'House' if 'clerk.house.gov' in item['source'] else 'Senate'
            item['processed'] = parsed_by_chamber[chamber]
            item['complete'] = parsed_by_chamber[chamber] == item['selected'] and item.get('pending', 0) == 0
    if report['errors']:
        report['status'] = 'partial'
    # No report can label the whole archive checked when any independent source failed.
    archive['collected_at'] = _stamp(now) if report['status'] == 'ok' else previous.get('collected_at')
    report['api_attempts'] = api_attempts
    report['vote_requests'] = vote_attempts
    return archive, report
