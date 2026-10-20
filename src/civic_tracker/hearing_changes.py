"""Deterministic hearing identity, agenda normalization and material revisions.

This module does not fetch sources or read PDFs. Absence from a listing is never
a cancellation. Compact contexts preserve multiple motions on one amendment.
"""
from datetime import datetime, timedelta, timezone
import re
from urllib.parse import urlsplit, parse_qs
from zoneinfo import ZoneInfo
from .changes import digest, measure_url, timestamp

STATUSES = {'scheduled', 'canceled', 'postponed', 'rescheduled', 'unconfirmed', 'unknown'}


def text(value):
    return ' '.join((value or '').split())


def explicit_status(value):
    """Recognize an assertion, not 'not canceled', policy text or a proposal."""
    value = text(value).casefold().rstrip('.!')
    match = re.fullmatch(r'(?:(?:this|the) )?(?:(?:committee )?(?:hearing|meeting) )?'
                         r'(?:(?:has been|is) )?(cancelled|canceled|postponed|rescheduled)'
                         r'(?:\s*[-:;].*|\s+(?:until|to|pending|due to|at)\b.*)?', value)
    return {'cancelled': 'canceled', 'canceled': 'canceled', 'postponed': 'postponed',
            'rescheduled': 'rescheduled'}.get(match[1]) if match else None


def identity(meeting, jurisdiction):
    p = urlsplit(meeting['source_url'])
    if jurisdiction == 'IL':
        match = re.fullmatch(r'/(House|Senate)/hearings/details/(\d+)/(\d+)/?', p.path, re.I)
        if p.hostname != 'ilga.gov' or not match: raise ValueError('hearing-identity')
        return f'IL-104-{match[1].upper()}-{match[2]}-{match[3]}'
    event = parse_qs(p.query).get('EventID')
    if p.hostname == 'docs.house.gov' and event and len(event) == 1 and event[0].isdigit():
        return 'US-119-HOUSE-' + event[0]
    if p.hostname == 'www.senate.gov' and meeting.get('committee_code') and text(meeting.get('description')):
        # Senate's feed exposes no durable hearing ID. A unique committee/topic
        # identity excludes time/room; collisions must be withheld, never joined.
        if meeting.get('identity_ambiguous'): raise ValueError('ambiguous-hearing-identity')
        return 'US-119-SENATE-' + digest([meeting['committee_code'], text(meeting['description']).casefold()])[:24]
    raise ValueError('hearing-identity')


def amendment(value):
    value = text(value).upper()
    if not value: return None
    value = re.sub(r'\bHOUSE\s+FLOOR\s+AMENDMENT\s*(?:NO\.?|NUMBER|#)?\s*', 'HFA', value)
    value = re.sub(r'\bSENATE\s+FLOOR\s+AMENDMENT\s*(?:NO\.?|NUMBER|#)?\s*', 'SFA', value)
    value = re.sub(r'\bHOUSE\s+COMMITTEE\s+AMENDMENT\s*(?:NO\.?|NUMBER|#)?\s*', 'HCA', value)
    value = re.sub(r'\bSENATE\s+COMMITTEE\s+AMENDMENT\s*(?:NO\.?|NUMBER|#)?\s*', 'SCA', value)
    match = re.fullmatch(r'(HFA|SFA|HCA|SCA)\s*#?\s*0*(\d+)', value)
    if not match: raise ValueError('unknown-amendment-identity')
    return match[1] + str(int(match[2]))


def agenda(items, jurisdiction):
    grouped = {}
    for item in items:
        bill = text(item['bill']).upper()
        if not re.fullmatch(r'(HB|SB|HR|SR|HJR|SJR|HJRCA|SJRCA)[1-9]\d*', bill): raise ValueError('agenda-bill-identity')
        ident = f'{jurisdiction}-{104 if jurisdiction == "IL" else 119}-' + bill
        if not measure_url(ident, item['official_url']): raise ValueError('agenda-session-evidence')
        amend = amendment(item.get('amendment')); key = bill + (':' + amend if amend else '')
        entry = grouped.setdefault(key, {'id': key, 'bill': bill, 'amendment': amend,
            'official_url': item['official_url'], 'contexts': []})
        context = {k: text(item.get(k)) for k in ('motion', 'vote_motion', 'vote_result')}
        # Results are context, not committee roll calls or member choices.
        context['status'] = explicit_status(context['vote_result'])
        if context not in entry['contexts']: entry['contexts'].append(context)
    for entry in grouped.values():
        entry['contexts'].sort(key=lambda c: (c['motion'], c['vote_motion'], c['vote_result']))
    return sorted(grouped.values(), key=lambda item: item['id'])


def day(meeting):
    value = meeting.get('date_local') or meeting.get('last_known_date_local')
    if not value: return ''
    if len(value) == 10: return value
    local = datetime.fromisoformat(value).replace(tzinfo=ZoneInfo(meeting.get('timezone', 'America/Chicago')))
    return local.astimezone(ZoneInfo('America/Chicago')).date().isoformat()


def clear_slips(snapshot):
    for member in snapshot.get('members', []):
        for meeting in member.get('meetings', []):
            for item in meeting.get('items', []): item['submission_verified'] = False


def retain_failed(snapshot, previous, as_of):
    """One fallback for daily and manual runs, including whole-compile failure."""
    old_members = {m['id']: m for m in previous.get('members', [])}
    for member in snapshot.get('members', []):
        if member.get('calendar_health') not in {'failed', 'partial_or_failed'}: continue
        old = old_members.get(member['id'], {})
        if not member.get('committees'): member['committees'] = old.get('committees', [])
        failed = {c['url'] for c in member['committees'] if c.get('health') in {'failed', 'partial'}}
        present = {m.get('hearing_key') or m['source_url'] for m in member.get('meetings', [])}
        for meeting in old.get('meetings', []):
            key = meeting.get('hearing_key') or meeting['source_url']
            if (member['calendar_health'] == 'failed' or member['jurisdiction'] == 'US' or meeting.get('committee_url') in failed):
                if key not in present and as_of <= day(meeting) <= snapshot['calendar_end']:
                    member['meetings'].append({**meeting, 'retained_after_failure': True,
                        'items': [{**i, 'submission_verified': False} for i in meeting.get('items', [])]})
        member['meetings'].sort(key=lambda m: (day(m), m['source_url']))


def slip_current(item, meeting, reference, hours=24):
    try:
        age = (timestamp(reference) - timestamp(item['submission_checked_at'])).total_seconds()
        return bool(item.get('submission_verified') and not meeting.get('retained_after_failure')
                    and meeting.get('status', 'scheduled') in {'scheduled', 'rescheduled'}
                    and 0 <= age <= hours * 3600)
    except (KeyError, ValueError, TypeError, AttributeError): return False


def delta(old, new):
    changes = []
    for field, label in [('local_time', 'time-changed'), ('location', 'location-changed'), ('status', 'status-changed')]:
        if old.get(field) != new.get(field):
            changes.append({'type': label, 'before': old.get(field), 'after': new.get(field)})
    if old.get('status_notice') != new.get('status_notice') and old.get('status') == new.get('status'):
        changes.append({'type': 'notice-updated'})
    # No agenda removals from unknown, failed or merely listing-only coverage.
    if old.get('agenda_coverage') == new.get('agenda_coverage') == 'complete':
        before = {item['id']: item for item in old.get('agenda', [])}
        after = {item['id']: item for item in new.get('agenda', [])}
        for key in sorted(after.keys() - before.keys()): changes.append({'type': 'agenda-added', 'item': key})
        for key in sorted(before.keys() - after.keys()): changes.append({'type': 'agenda-removed', 'item': key})
        for key in sorted(before.keys() & after.keys()):
            if before[key]['contexts'] != after[key]['contexts']:
                newly_postponed = any(c.get('status') == 'postponed' for c in after[key]['contexts']) and not any(c.get('status') == 'postponed' for c in before[key]['contexts'])
                changes.append({'type': 'bill-postponed' if newly_postponed else 'agenda-item-updated', 'item': key})
    return changes


def describe(changes):
    labels = {'time-changed': 'Hearing time/date changed', 'location-changed': 'Location changed',
              'agenda-added': 'Agenda added', 'agenda-removed': 'Removed from published agenda',
              'bill-postponed': 'Bill explicitly postponed', 'agenda-item-updated': 'Agenda item updated',
              'notice-updated': 'Official notice updated'}
    parts = []
    for change in changes:
        if change['type'] == 'status-changed': parts.append('Hearing status: ' + str(change['after']))
        else: parts.append(labels[change['type']] + (': ' + change['item'] if 'item' in change else ''))
    return '; '.join(parts)
