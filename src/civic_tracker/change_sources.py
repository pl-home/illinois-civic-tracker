"""Small, read-only Stage A adapters for existing deterministic source receipts.

No evidence is fetched here. Completeness is scoped to the collector's actual
work, not inferred from a nonempty index or a source URL/status label alone.
"""
from collections import defaultdict
import re
from urllib.parse import urlsplit
from .changes import MEMBERS, digest, read

OFFICIAL = {v[1]: k for k, v in MEMBERS.items()}


def scope(ident, jurisdiction, checked, complete, facts, **extra):
    return {'id': ident, 'jurisdiction': jurisdiction, 'session': 104 if jurisdiction == 'IL' else 119,
            'checked_at': checked, 'complete': complete, 'facts': facts, 'adapter': 2, **extra}


def fact(key, kind, jurisdiction, members, title, detail, evidence, when=None, **extra):
    return {'key': key, 'kind': kind, 'jurisdiction': jurisdiction,
            'session': 104 if jurisdiction == 'IL' else 119, 'members': sorted(set(members)),
            'occurred_at': when, 'date_precision': ('timestamp' if 'T' in when else 'day') if when else 'unknown',
            'title': title, 'detail': detail, 'evidence': evidence, **extra}


def evidence(url, retrieved, binding, raw=None):
    result = {'url': url, 'retrieved_at': retrieved, 'binding': binding}
    if raw: result['sha256'] = raw
    return result


def illinois(archive, report):
    for ident, bill in sorted(archive.get('bills', {}).items()):
        proof = bill.get('evidence', {}); checked = proof.get('retrieved_at')
        ev = evidence(bill['source_url'], checked, 'official-bill', proof.get('sha256'))
        roles = bill.get('role_events', [])
        members = {OFFICIAL.get(str(who)) for who in bill.get('current_target_sponsors', [])}
        members.update(OFFICIAL.get(str(role.get('member_id'))) for role in roles)
        members.discard(None)
        if not members: continue
        rows = []; title = bill['title']
        rows.append(fact(ident + ':title', 'bill-title', 'IL', members, title,
                         'Official short title; a changed title requires review, not an automatic shell-bill conclusion.', ev, measure=ident))
        seen = set()
        for role in roles:
            member = OFFICIAL.get(str(role.get('member_id')))
            if not member: continue
            # No source action ID exists: exact normalized date/chamber/text is
            # the conservative identity, never an unstable array offset.
            key = ident + ':role:' + digest([member, role['date'], role.get('chamber'), ' '.join(role['action'].split())])[:24]
            if key in seen: continue
            seen.add(key)
            rows.append(fact(key, 'filing' if role.get('role') == 'original-filer' else 'sponsor-role', 'IL', [member],
                title, role['action'], ev, role['date'], measure=ident,
                role=role.get('role'), operation=role.get('operation')))
        # Full histories are retained going forward. Older archives contain
        # only roles + last action; upgrading a particular bill is quiet.
        actions = bill.get('actions') or [bill.get('displayed_last_action', {})]
        seen_actions = set()
        for action in actions:
            if not action.get('date') or not action.get('action'): continue
            if any(action == {k: r[k] for k in ('date', 'chamber', 'action')} for r in roles): continue
            key = ident + ':action:' + digest([action['date'], action.get('chamber'), ' '.join(action['action'].split())])[:24]
            if key in seen_actions: continue
            seen_actions.add(key)
            rows.append(fact(key, 'bill-action', 'IL', members, title, action['action'], ev, action['date'], measure=ident,
                attribution='Action on an associated measure; not necessarily an action by a tracked member.'))
        yield scope('ilga:bill:' + ident, 'IL', checked, bool(checked and proof.get('sha256')), rows,
                    adapter=3 if 'actions' in bill else 2, family='ilga-xml', baseline_on_add=False)
    csv = report.get('floor_csv', {}); checked = report.get('checked_at')
    csv_url = 'https://ilga.gov/documents/reports/static/104MemberVotes.csv'
    good = bool(csv.get('status') in (200, 304) and not any(e.get('source') == csv_url for e in report.get('errors', [])))
    rows = []
    for vote in archive.get('votes', {}).values():
        if vote.get('verification') != 'official-csv': continue  # PDF work stays deferred.
        proof = vote.get('evidence', {})
        for choice in vote.get('choices', []):
            who = OFFICIAL.get(str(choice.get('member_id')))
            if not who: continue
            rows.append(fact(vote['record_id'] + ':' + who, 'vote', 'IL', [who],
                vote.get('label') or vote['measure_id'], vote['motion_context'],
                evidence(vote['source_url'], proof.get('retrieved_at'), 'official-roll', proof.get('sha256')),
                vote['date'], measure=vote['measure_id'], roll_id=vote['record_id'], choice=choice['choice'],
                raw_choice=choice.get('raw'), vote_scope=vote['scope'], totals=vote.get('totals', {}),
                attribution='Official floor CSV; tally contains only source-derived nay count, not a full committee tally.'))
    yield scope('ilga:floor-csv:104', 'IL', checked, good, rows)


def federal(archive, report):
    for receipt in report.get('legislation_sources', []):
        source = receipt['source']; who, role = source.split(':'); member = OFFICIAL.get(who)
        if not member: continue
        checked = receipt.get('checked_at') or report.get('checked_at'); rows = []
        for ident, bill in archive.get('bills', {}).items():
            if {'member': who, 'role': role} not in bill.get('relations', []): continue
            ev = evidence(bill['source_url'], checked, 'official-bill')
            rows.append(fact(ident + ':role:' + member + ':' + role, 'sponsor-role', 'US', [member], bill['title'],
                'Listed as ' + role + '; this listing does not establish a cosponsorship join date.', ev,
                measure=ident, role=role, operation='listed'))
            if role == 'sponsored':
                rows.append(fact(ident + ':filing:' + member, 'filing', 'US', [member], bill['title'],
                    'Introduction/submission date of a sponsor-listed measure or amendment.', ev, bill.get('introduced_date'), measure=ident))
        yield scope('congress:119:' + source, 'US', checked, receipt.get('complete') is True, rows, removals=True)
    for receipt in report.get('vote_sources', []):
        chamber = 'HOUSE' if 'clerk.house.gov' in receipt['source'] else 'SENATE'
        for vote in archive.get('votes', {}).values():
            if not vote['record_id'].startswith('US-119-' + chamber + '-'): continue
            if vote.get('verification') != 'reconciled-official-xml': continue
            proof = vote.get('evidence', {}); rows = []
            for choice in vote.get('choices', []):
                who = OFFICIAL.get(choice.get('bioguide'))
                if not who: continue
                rows.append(fact(vote['record_id'] + ':' + who, 'vote', 'US', [who],
                    vote.get('description') or vote['record_id'], vote['motion'],
                    evidence(vote['source_url'], proof.get('retrieved_at'), 'official-roll', proof.get('sha256')),
                    vote['date'], measure=vote.get('measure_id'), roll_id=vote['record_id'],
                    choice=choice['choice'], raw_choice=choice.get('raw'), vote_scope='floor',
                    totals=vote.get('totals', {}), result=vote.get('result')))
            # Individual successful parsed roll receipts isolate a malformed
            # ballot and allow valid details from a partial index run. No claim
            # that every historical roll was rechecked; no absence deletion.
            yield scope('congress:roll:' + vote['record_id'], 'US', proof.get('retrieved_at'),
                bool(proof.get('retrieved_at') and proof.get('sha256')), rows,
                family='congress-roll-' + chamber, baseline_on_add=False)


def calendars(snapshot):
    proofs = {p['url']: p for p in snapshot.get('calendar_sources', [])}
    groups = {}
    for member in snapshot.get('members', []):
        for committee in member.get('committees', []):
            ident = 'calendar:' + committee['url']
            group = groups.setdefault(ident, {'members': [], 'committee': committee, 'rows': {},
                'jurisdiction': member['jurisdiction'], 'checked': member.get('calendar_checked_at'), 'good': True})
            group['members'].append(member['id'])
            good = member.get('calendar_health') not in {'failed', 'partial_or_failed'} and committee.get('health') != 'failed'
            group['good'] = group['good'] and good
            for meeting in member.get('meetings', []):
                if meeting.get('committee_url') != committee['url'] or meeting.get('retained_after_failure'): continue
                proof = proofs.get(meeting['source_url'])
                # House/Senate feed receipt may bind the parsed meeting even
                # when an individual detail page is not fetched.
                if not proof and member['jurisdiction'] == 'US':
                    proof = next((p for p in proofs.values() if
                        ('hearings.xml' in p['url'] if member['chamber'] == 'Senate' else 'docs.house.gov' in p['url'])), None)
                if not proof:
                    group['good'] = False
                    continue
                key = 'hearing:' + digest(meeting['source_url'])[:24]
                previous = group['rows'].get(key, {})
                group['rows'][key] = fact(key, 'hearing', member['jurisdiction'], previous.get('members', []) + [member['id']],
                    meeting.get('committee_name') or committee['name'], meeting.get('location') or 'Location not supplied',
                    evidence(meeting['source_url'], proof['checked_at'], 'official-calendar', proof.get('sha256')),
                    meeting['date_local'][:10], committee=committee['url'], local_time=meeting['date_local'],
                    agenda=sorted({r.get('measure', r.get('label', '')) for r in meeting.get('items', [])}),
                    attribution='Published schedule; membership does not establish attendance. Missing meetings never imply cancellation.')
    for ident, group in groups.items():
        yield scope(ident, group['jurisdiction'], group['checked'], group['good'], list(group['rows'].values()))


def publications(root, snapshot):
    state = read(root / 'data/communications-state.json', {'sources': {}})
    for ident, receipt in state['sources'].items():
        if receipt.get('status') == 'link-only': continue
        # Source duplicates (e.g. the same party post for two tracked members)
        # become one event with several member references.
        grouped = {}
        for item in receipt.get('items', []):
            if item.get('retained_after_failure'): continue
            jurisdiction = MEMBERS[item['member_id']][0]
            key = 'publication:' + digest([jurisdiction, item['url']])[:24]
            old = grouped.get(key, {})
            grouped[key] = fact(key, 'publication', jurisdiction, old.get('members', []) + [item['member_id']],
                item['title'], 'Published by ' + item['publisher'] + '; claims are attributed, not independently verified.',
                evidence(item['url'], receipt['checked_at'], 'publisher-listing'),
                item['published_at'], publisher=item['publisher'], publication_kind=item['kind'],
                listing_url=receipt['source_url'])
        # A configured publisher source must not mix federal/state identities.
        for jurisdiction in sorted({MEMBERS[m][0] for m in receipt.get('members', [])}):
            rows = [r for r in grouped.values() if r['jurisdiction'] == jurisdiction]
            yield scope('publisher:' + ident + ':' + jurisdiction, jurisdiction, receipt.get('checked_at'), receipt.get('status') == 'ok', rows)
    news = read(root / 'data/media-state.json', {'members': {}})
    for member in snapshot.get('members', []):
        receipt = news['members'].get(member['id'], {}); health = member.get('media_health', {})
        candidates = {r['id']: r for r in receipt.get('candidates', [])}
        rows = []
        for item in member.get('media_reports', []):
            if item['id'] not in candidates: continue
            rows.append(fact('news:' + digest(item['url'])[:24], 'publication', member['jurisdiction'], [member['id']],
                item['title'], 'News metadata with screened member relevance; article content is not independently verified.',
                evidence(item['url'], receipt.get('checked_at'), 'screened-news-metadata'), item['published_at'],
                publisher=item.get('publisher', item.get('source', 'News publisher')), publication_kind='news'))
        yield scope('news:' + member['id'], member['jurisdiction'], receipt.get('checked_at'),
                    receipt.get('status') == 'ok' and health.get('inference_status') == 'complete', rows)


def observations(root):
    report = read(root / 'data/daily-report.json', {}).get('sources', {})
    state = read(root / 'data/illinois-index.json', {})
    federal_archive = read(root / 'data/federal-index.json', {})
    snapshot = read(root / 'data/dashboard.json', {})
    return [*illinois(state, report.get('Illinois', {})), *federal(federal_archive, report.get('Federal', {})),
            *calendars(snapshot), *publications(root, snapshot)]
