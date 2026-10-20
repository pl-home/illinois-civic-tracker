"""One-shot public homepage snapshot. No schedules, model calls or credentials.

Imports only selected public facts from explicit read-only archives. Calendar
pages are fetched separately, with source-level failures kept visible.
"""
import argparse
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from urllib.request import Request, build_opener

from .dashboard_sources import state_committees, state_committee_role, state_schedule, senate_schedule, house_schedule, open_slip_form
from .hearings import parse_hearing_details
from .http import Client, fingerprint, NoRedirect, source_error


def month_after(day):
    year, month = (day.year + 1, 1) if day.month == 12 else (day.year, day.month + 1)
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def public_url(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or parsed.username or parsed.password or any(
            key in parsed.query.casefold() for key in ('api_key', 'apikey', 'access_token', 'password')):
        raise ValueError('Nonpublic source URL')
    allowed = {'ilga.gov', 'www.ilga.gov', 'ftp.ilga.gov', 'www.congress.gov', 'clerk.house.gov', 'www.senate.gov', 'docs.house.gov'}
    if parsed.netloc not in allowed:
        raise ValueError('Unexpected public record host')
    return value


def event(ident, kind, when, title, detail, source, retrieved_at, **extra):
    date.fromisoformat(when)
    return {'id': ident, 'kind': kind, 'date': when, 'title': title, 'detail': detail,
            'source_url': public_url(source), 'source_retrieved_at': retrieved_at, **extra}


def vote_bill_url(vote, bills):
    """Keep the bill destination separate from the official roll-call source."""
    ident = vote.get('measure_id')
    source = bills.get(ident, {}).get('source_url')
    if source:
        return public_url(source)
    # Federal vote XML can identify a bill absent from the member-sponsorship
    # import. Build its canonical Congress.gov link from that exact identity.
    match = re.fullmatch(r'US-(\d+)-(HR|S|HJRES|SJRES|HCONRES|SCONRES|HRES|SRES)(\d+)', ident or '')
    if not match:
        return None  # Do not invent a bill for a nomination or unidentified amendment.
    types = {'HR': 'house-bill', 'S': 'senate-bill', 'HJRES': 'house-joint-resolution',
             'SJRES': 'senate-joint-resolution', 'HCONRES': 'house-concurrent-resolution',
             'SCONRES': 'senate-concurrent-resolution', 'HRES': 'house-resolution', 'SRES': 'senate-resolution'}
    return f'https://www.congress.gov/bill/{int(match[1])}/{types[match[2]]}/{int(match[3])}'


def state_events(archive, member, cutoff, as_of):
    who = member['official_id']; events = []; votes = {}; listings = []
    for bill in archive['bills'].values():
        source = bill['source_url']; evidence = bill.get('evidence', {})
        ident = bill['record_id']; title = bill['title']; retrieved = evidence.get('retrieved_at')
        associated = who in [str(v) for v in bill.get('current_target_sponsors', [])]
        for index, role in enumerate(bill.get('role_events', [])):
            if str(role.get('member_id')) != who:
                continue
            # Preserve the exact dated role action, including removals/alternate roles.
            events.append(event(f'{ident}-role-{who}-{index}', 'sponsorship', role['date'], title,
                role['action'], source, retrieved, measure=ident.split('-')[-1], role=role.get('role'),
                operation=role.get('operation'), source_sha256=evidence.get('sha256')))
        filing = bill.get('original_filing')
        if filing and re.search(r'(?<!\w)' + re.escape(member['name']) + r'(?!\w)', filing.get('action', '')):
            events.append(event(f'{ident}-filing-{who}', 'introduction', filing['date'], title,
                filing['action'], source, retrieved, measure=ident.split('-')[-1], source_sha256=evidence.get('sha256')))
        if associated:
            action = bill.get('displayed_last_action', {})
            if action.get('date'):
                events.append(event(f'{ident}-status-{who}', 'bill_status', action['date'], title,
                    action['action'], source, retrieved, measure=ident.split('-')[-1],
                    attribution='Action on an associated bill; not necessarily an action by this member.', source_sha256=evidence.get('sha256')))
    for vote in archive['votes'].values():
        if vote.get('verification') not in ('reconciled-official-pdf', 'official-csv'):
            continue
        for selected in vote['choices']:
            if str(selected.get('member_id')) != who:
                continue
            key = vote.get('roll_group') or vote['record_id']
            value = event(key + '-' + who, 'vote', vote['date'],
                archive['bills'].get(vote['measure_id'], {}).get('title', vote.get('label', vote['measure_id'])),
                vote.get('motion_context') or vote.get('label', ''), vote['source_url'],
                vote.get('evidence', {}).get('retrieved_at'), measure=vote['measure_id'].split('-')[-1],
                choice=selected['choice'], raw_choice=selected.get('raw'), scope=vote['scope'],
                bill_url=vote_bill_url(vote, archive['bills']),
                totals=vote.get('totals'), pdf_date=vote.get('pdf_date'),
                date_verification=vote.get('date_verification'), source_sha256=vote.get('evidence', {}).get('sha256'),
                attribution='Official floor-vote CSV; individual roll-call PDF not linked for this record.' if vote.get('verification') == 'official-csv' else None)
            if key in votes and (votes[key]['choice'], votes[key]['date'], votes[key]['detail']) != (value['choice'], value['date'], value['detail']):
                # Related PDFs with different contexts are not silently merged.
                key = vote['record_id']
            votes[key] = value
    return bound_events(events + list(votes.values()), cutoff, as_of), listings


def federal_events(archive, member, cutoff, as_of):
    who = member['official_id']; events = []; listings = []
    for bill in archive['bills'].values():
        for relation in bill.get('relations', []):
            if relation['member'] != who:
                continue
            ident = bill['record_id']; source = public_url(bill['source_url'])
            if relation['role'] == 'sponsored':
                events.append(event(ident + '-introduced-' + who, 'introduction', bill['introduced_date'],
                    bill['title'], 'Introduction date of a sponsor-listed measure; not a cosponsorship join date.', source, archive['collected_at'], measure=ident.split('-')[-1]))
            else:
                # The member API list does not establish the date cosponsorship began.
                listings.append({'measure': ident.split('-')[-1], 'title': bill['title'], 'role': relation['role'],
                    'source_url': source, 'bill_introduced_date': bill.get('introduced_date'), 'role_date': None,
                    'source_retrieved_at': archive['collected_at']})
    for vote in archive['votes'].values():
        if vote.get('verification') != 'reconciled-official-xml':
            continue
        for selected in vote['choices']:
            if selected.get('bioguide') == who:
                events.append(event(vote['record_id'] + '-' + who, 'vote', vote['date'], vote.get('description', ''),
                    vote['motion'], vote['source_url'], vote.get('evidence', {}).get('retrieved_at'),
                    measure=vote.get('measure'), choice=selected['choice'], raw_choice=selected['raw'],
                    scope='floor', result=vote.get('result'), totals=vote.get('totals'),
                    bill_url=vote_bill_url(vote, archive['bills']),
                    source_sha256=vote.get('evidence', {}).get('sha256')))
    listings.sort(key=lambda r: r.get('bill_introduced_date') or '', reverse=True)
    return bound_events(events, cutoff, as_of), listings[:6]


def bound_events(events, cutoff, as_of):
    # Keep all recent activity up to an explicit cap, plus older context by kind.
    ordered = sorted((e for e in events if e['date'] <= as_of), key=lambda e: (e['date'], e['id']), reverse=True)
    recent = [e for e in ordered if e['date'] >= cutoff]
    selected = {e['id']: e for e in recent[:100]}
    for kind in ('vote', 'sponsorship', 'introduction', 'bill_status'):
        for e in [e for e in ordered if e['kind'] == kind][:5]:
            selected[e['id']] = e
    # Committee votes remain visible even when more recent floor rows dominate.
    for e in [e for e in ordered if e.get('scope') == 'committee'][:2]:
        selected[e['id']] = e
    return {'events': sorted(selected.values(), key=lambda e: (e['date'], e['id']), reverse=True),
            'recent_total_in_import': len(recent), 'recent_truncated': len(recent) > 100,
            'latest_event_date': ordered[0]['date'] if ordered else None,
            'latest_vote_date': next((e['date'] for e in ordered if e['kind'] == 'vote'), None)}


def verify_recent_state_events(snapshot, client):
    """Reconfirm bounded recent role/filing facts; failures keep archive provenance."""
    cache = {}; receipts = []
    for member in snapshot['members']:
        if member['jurisdiction'] != 'IL':
            continue
        for item in member['events']:
            if item['kind'] not in ('sponsorship', 'introduction') or item['date'] < snapshot['recent_start']:
                continue
            try:
                measure = item['measure']
                typ, number = re.fullmatch(r'(HJR|SJR|HB|SB|HR|SR)(\d+)', measure).groups()
                code = {'HJR': 'HJ', 'SJR': 'SJ'}.get(typ, typ)
                url = f'https://ftp.ilga.gov/Legislation/104/BillStatus/XML/10400{code}{int(number):04d}.xml'
                if url not in cache:
                    if len(cache) >= 30:
                        raise ValueError('Recent XML verification request bound')
                    response = client.get(url)
                    tree = ET.fromstring(response['body']); rows = []; when = ''
                    for child in tree.find('actions'):
                        if child.tag == 'statusdate':
                            when = datetime.strptime(child.text, '%m/%d/%Y').date().isoformat()
                        elif child.tag == 'action':
                            rows.append((when, ' '.join((child.text or '').split())))
                    metadata = {**fingerprint(response), 'checked_at': datetime.now(timezone.utc).isoformat()}
                    cache[url] = (rows, metadata); receipts.append(metadata)
                rows, metadata = cache[url]
                if (item['date'], ' '.join(item['detail'].split())) not in rows:
                    raise ValueError('Current source does not confirm imported action')
                item.update(source_retrieved_at=metadata['checked_at'], source_sha256=metadata['sha256'],
                            verification_source_url=url, recent_source_verification='confirmed')
            except Exception as error:
                item['recent_source_verification'] = 'unconfirmed'
                snapshot['errors'].append({'source': 'Recent Illinois action verification', 'error': source_error(error)})
    snapshot['activity_verifications'] = receipts


def collect(root, state_path, federal_path, as_of):
    settings = json.loads((root / 'config/dashboard.json').read_text(encoding='utf-8'))
    from .changes import read
    from .hearing_changes import day as hearing_day, identity as hearing_identity
    from .hearing_collect import state_meetings
    previous = read(root/'data/dashboard.json', {'members': []})
    prior_members = {m['id']: m for m in previous['members']}
    hearing_options = read(root/'config/hearings.json')
    state = json.loads(state_path.read_text(encoding='utf-8'))
    federal = json.loads(federal_path.read_text(encoding='utf-8'))
    scratch = root / '.local'; scratch.mkdir(exist_ok=True)
    config = json.loads((root / 'config/project.json').read_text(encoding='utf-8'))
    client = Client(config, scratch)
    checked = datetime.now(timezone.utc).isoformat(); cutoff = (as_of - timedelta(days=settings['recent_days'] - 1)).isoformat()
    end = month_after(as_of)
    result = {'schema_version': 1, 'as_of': as_of.isoformat(), 'recent_start': cutoff,
        'calendar_end': end.isoformat(), 'generated_at': checked, 'automatic_refresh_enabled': False,
        'attendance_note': 'A committee meeting is not evidence that a member will attend.',
        'members': [], 'calendar_sources': [], 'errors': []}
    def fetch(url, name):
        cache = scratch / name
        if cache.exists() and time.time() - cache.stat().st_mtime < 1800:
            body = cache.read_bytes()
            metadata = {'url': url, 'sha256': hashlib.sha256(body).hexdigest(), 'same_session_cache': True,
                        'checked_at': datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc).isoformat()}
        else:
            response = client.get(url); body = response['body']; cache.write_bytes(body)
            metadata = {**fingerprint(response), 'checked_at': datetime.now(timezone.utc).isoformat()}
        result['calendar_sources'].append(metadata)
        return body, metadata
    # Federal feed/calendar reads use public GET only; no authentication/redirects.
    opener = build_opener(NoRedirect())
    def federal_fetch(url, name):
        public_url(url)
        cache = scratch / name
        if cache.exists() and time.time() - cache.stat().st_mtime < 1800:
            body = cache.read_bytes()
            result['calendar_sources'].append({'url': url, 'sha256': hashlib.sha256(body).hexdigest(), 'same_session_cache': True,
                'checked_at': datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc).isoformat()})
            return body
        time.sleep(1)
        request = Request(url, headers={'User-Agent': config['user_agent']})
        with opener.open(request, timeout=40) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError('Calendar size bound')
        cache.write_bytes(body)
        result['calendar_sources'].append({'url': url, 'sha256': hashlib.sha256(body).hexdigest(), 'checked_at': datetime.now(timezone.utc).isoformat()})
        return body
    senate_events = []; house_events = []; federal_health = {}
    try:
        senate_events = senate_schedule(federal_fetch('https://www.senate.gov/general/committee_schedules/hearings.xml', 'dashboard-senate-feed.xml'))
        federal_health['Senate'] = 'published_feed_checked'
    except Exception as error:
        federal_health['Senate'] = 'failed'; result['errors'].append({'source': 'Senate calendar', 'error': source_error(error)})
    try:
        start = as_of - timedelta(days=(as_of.weekday() + 1) % 7)
        while start <= end:
            finish = start + timedelta(days=6)
            url = f'https://docs.house.gov/Committee/Calendar/ByWeek.aspx?WeekOf={start:%m%d%Y}_{finish:%m%d%Y}'
            body = federal_fetch(url, f'dashboard-house-week-{start}.html')
            house_events.extend(house_schedule(body, url, start))
            start += timedelta(days=7)
        federal_health['House'] = 'published_weeks_checked'
    except Exception as error:
        federal_health['House'] = 'partial_or_failed'; result['errors'].append({'source': 'House calendar', 'error': source_error(error)})
    hearing_work = {}
    for member in settings['members']:
        data, listings = (state_events(state, member, cutoff, as_of.isoformat()) if member['jurisdiction'] == 'IL'
                          else federal_events(federal, member, cutoff, as_of.isoformat()))
        item = {**member, **data, 'sponsorship_listings': listings, 'meetings': [],
                'activity_source_checked_at': state['collected_at'] if member['jurisdiction'] == 'IL' else federal['collected_at'],
                'activity_coverage': 'Bounded import of prior official-source records; no claim of complete current coverage.',
                'calendar_checked_at': checked}
        if member['jurisdiction'] == 'IL':
            item['committees'] = []; item['calendar_health'] = 'checked'
            try:
                # These member pages were just fetched during schema inspection.
                cached = scratch / f'dashboard-member-{member["official_id"]}.html'
                if cached.exists() and time.time() - cached.stat().st_mtime < 3600:
                    body = cached.read_bytes()
                    result['calendar_sources'].append({'url': member['url'], 'sha256': hashlib.sha256(body).hexdigest(), 'checked_at': checked, 'same_session_cache': True})
                else:
                    body, _ = fetch(member['url'], cached.name)
                item['committees'] = state_committees(body, member['url'])
                for committee in item['committees']:
                    try:
                        roster_key = hashlib.sha256(committee['url'].encode()).hexdigest()
                        roster, role_metadata = fetch(committee['url'], f'dashboard-roster-{roster_key}.html')
                        committee.update(state_committee_role(roster, committee['url'], member['official_id']))
                        committee['role_checked_at'] = role_metadata['checked_at']
                    except Exception as error:
                        committee['role'] = None
                        result['errors'].append({'source': committee['url'], 'purpose': 'Committee role', 'error': source_error(error)})
                    try:
                        body, metadata = fetch(committee['schedule_url'], f'dashboard-committee-{committee["id"]}.html')
                        committee['checked_at'] = metadata['checked_at']; committee['health'] = 'checked'
                        item['meetings'].extend(state_meetings(committee, body, metadata,
                            prior_members.get(member['id'], {}).get('meetings', []), as_of, end,
                            fetch, hearing_options, hearing_work, result['errors']))
                        if committee['health'] != 'checked': item['calendar_health'] = 'partial_or_failed'
                    except Exception as error:
                        committee['health'] = 'failed'; item['calendar_health'] = 'partial_or_failed'
                        result['errors'].append({'source': committee['schedule_url'], 'error': source_error(error)})
            except Exception as error:
                item['calendar_health'] = 'failed'; result['errors'].append({'source': member['url'], 'error': source_error(error)})
        else:
            item['calendar_health'] = federal_health[member['chamber']]
            source_events = house_events if member['chamber'] == 'House' else senate_events
            for meeting in source_events:
                if not as_of <= date.fromisoformat(meeting['date_local'][:10]) <= end:
                    continue
                for committee in item['committees']:
                    if committee['match'].casefold() in meeting['committee_name'].casefold():
                        try:
                            hearing_key = hearing_identity(meeting, 'US')
                            proof_url = meeting.get('evidence_url', meeting['source_url'])
                            proof = next((p for p in reversed(result['calendar_sources']) if p['url'] == proof_url), None)
                            if proof is None: raise ValueError('Missing calendar receipt')
                            item['meetings'].append({**meeting, 'committee_url': committee['url'], 'items': [],
                                'hearing_key': hearing_key, 'evidence': proof})
                        except Exception:
                            item['calendar_health'] = 'partial_or_failed'
                            result['errors'].append({'source': meeting['source_url'], 'error': 'ambiguous-hearing-identity'})
        item['meetings'].sort(key=lambda m: (hearing_day(m), m['source_url']))
        result['members'].append(item)
    verify_recent_state_events(result, client)
    path = root / 'data/dashboard.json'
    path.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'members': len(result['members']), 'events': sum(len(m['events']) for m in result['members']),
                      'meetings': sum(len(m['meetings']) for m in result['members']), 'errors': result['errors']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-archive', type=Path, required=True)
    parser.add_argument('--federal-archive', type=Path, required=True)
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    args = parser.parse_args()
    collect(Path.cwd(), args.state_archive, args.federal_archive, args.as_of)


if __name__ == '__main__':
    main()
