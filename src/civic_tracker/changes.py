"""Versioned, offline change ledger. No HTTP, models, PDF reading or delivery.

Facts are compact source-adapter projections, not a second source archive. One
atomic ledger holds accepted facts, completion cursors and immutable revisions.
Incomplete scopes cannot replace facts. See docs/CHANGE_FEED.md and provenance.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

VERSION = 1
POLICY = 'stage-a-1'
KINDS = {'filing', 'sponsor-role', 'bill-action', 'bill-title', 'vote', 'hearing', 'publication'}
CHOICES = {'yes', 'no', 'present', 'absent', 'excused', 'not-voting'}
MEMBERS = {'fritts': ('IL', '3428'), 'arellano': ('IL', '3383'),
           'lahood': ('US', 'L000585'), 'durbin': ('US', 'D000563'), 'duckworth': ('US', 'D000622')}
MAX_LEDGER = 10_000_000
MAX_EXCEPTIONS = 64


def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return sha256(packed(value).encode()).hexdigest()


def read(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else deepcopy(default)


def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timezone-required')
    return dt.astimezone(timezone.utc)


def public_url(value):
    p = urlsplit(value)
    if (p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None, 443)
            or any(c.isspace() or ord(c) < 32 for c in value)
            or any(re.search(r'key|token|password|secret|auth', key, re.I) for key in parse_qs(p.query))):
        raise ValueError('unsafe-url')
    return value


def measure_url(measure, url):
    """Bind the actual measure/session to the URL, rather than trusting a label."""
    p = urlsplit(public_url(url)); query = {k.casefold(): v for k, v in parse_qs(p.query).items()}
    m = re.fullmatch(r'(IL|US)-(\d+)-([A-Z]+)(\d+)', measure)
    if not m:
        return False
    jurisdiction, session, typ, num = m.groups()
    if jurisdiction == 'IL':
        if p.hostname not in {'ilga.gov', 'www.ilga.gov', 'ftp.ilga.gov'}:
            return False
        code = {'HJR': 'HJ', 'SJR': 'SJ', 'HJRCA': 'HC', 'SJRCA': 'SC', 'JSR': 'JS'}.get(typ, typ)
        xml = f'/Legislation/{session}/BillStatus/XML/{session}00{code}{int(num):04d}.xml'
        # GA104's ILGA service identifiers are explicit reviewed configuration.
        return (p.path.casefold() == xml.casefold() or
                (session == '104' and p.path.casefold() == '/legislation/billstatus'
                 and query.get('docnum') == [str(int(num))] and query.get('doctypeid') == [typ]
                 and query.get('gaid') == ['18'] and query.get('sessionid') == ['114']))
    types = {'HR': 'house-bill', 'S': 'senate-bill', 'HRES': 'house-resolution', 'SRES': 'senate-resolution',
             'HJRES': 'house-joint-resolution', 'SJRES': 'senate-joint-resolution',
             'HCONRES': 'house-concurrent-resolution', 'SCONRES': 'senate-concurrent-resolution'}
    if typ in {'SAMDT', 'HAMDT'}:
        chamber = 'senate' if typ == 'SAMDT' else 'house'
        return p.hostname == 'www.congress.gov' and p.path.rstrip('/') == f'/amendment/{session}/{chamber}-amendment/{int(num)}'
    return p.hostname == 'www.congress.gov' and p.path.rstrip('/') == f'/bill/{session}/{types.get(typ)}/{int(num)}'


def semantic(fact):
    # Transport hashes/retrieval dates are provenance, never material changes.
    excluded = {'evidence'}
    # A current bill title/member association is display context on historical
    # actions, not a correction to every past action. Title has its own fact.
    if fact.get('kind') in {'filing', 'sponsor-role', 'bill-action', 'vote'}: excluded.add('title')
    if fact.get('kind') in {'bill-action', 'bill-title'}: excluded.add('members')
    return {k: ' '.join(v.split()) if k in {'title', 'detail'} and isinstance(v, str) else v
            for k, v in fact.items() if k not in excluded}


def validate_fact(fact, scope):
    """Shared gate for ledger ingestion and every new feed publication path.

    Adapter proof means parsed official records or attributed publisher metadata;
    it is explicitly not an independent verification of a publisher's claims.
    """
    errors = []
    try:
        if fact['kind'] not in KINDS: errors.append('unknown-kind')
        if fact['jurisdiction'] != scope['jurisdiction'] or fact['session'] != scope['session']:
            errors.append('source-session-mismatch')
        if (fact['jurisdiction'], fact['session']) not in {('IL', 104), ('US', 119)}:
            errors.append('source-session-mismatch')
        if not fact['members'] or len(set(fact['members'])) != len(fact['members']): errors.append('member-reference')
        for member in fact['members']:
            if member not in MEMBERS or MEMBERS[member][0] != fact['jurisdiction']: errors.append('member-reference')
        if not isinstance(fact['key'], str) or len(fact['key']) > 250: errors.append('fact-identity')
        if not fact['title'] or len(fact['title']) > 2000 or len(fact['detail']) > 2000: errors.append('field-bound')
        if any(ord(c) < 32 and c not in '\n\r\t' for value in (fact['title'], fact['detail']) for c in value): errors.append('field-control')
        when = fact['occurred_at']
        precision = fact['date_precision']
        if precision not in {'day', 'timestamp', 'unknown'}: errors.append('date-precision')
        elif precision == 'unknown':
            if when is not None: errors.append('date-precision')
        elif precision == 'timestamp': timestamp(when)
        else: datetime.strptime(when, '%Y-%m-%d')
        if when and when[:10] > scope['checked_at'][:10] and fact['kind'] != 'hearing': errors.append('future-action')
        measure = fact.get('measure')
        if measure and not re.fullmatch(re.escape(fact['jurisdiction']) + '-' + re.escape(str(fact['session'])) + r'-[A-Z]+[1-9]\d*', measure):
            errors.append('measure-reference')
        evidence = fact['evidence']
        public_url(evidence['url']); timestamp(evidence['retrieved_at'])
        if evidence['binding'] not in {'official-bill', 'official-roll', 'official-calendar', 'publisher-listing', 'screened-news-metadata'}:
            errors.append('evidence-binding')
        raw_hash = evidence.get('sha256')
        if raw_hash is not None and not re.fullmatch(r'[0-9a-f]{64}', raw_hash): errors.append('evidence-hash')
        if fact['kind'] in {'filing', 'sponsor-role', 'bill-action', 'bill-title'}:
            if not measure or not measure_url(measure, evidence['url']) or evidence['binding'] != 'official-bill': errors.append('measure-evidence-mismatch')
        if fact['kind'] == 'sponsor-role':
            if fact.get('role') not in {'original-filer', 'chief-co-sponsor', 'chief-sponsor', 'co-sponsor', 'sponsor', 'sponsored', 'cosponsored'}:
                errors.append('missing-role')
            if fact.get('operation') not in {'filed', 'added-or-changed', 'removed', 'listed'}: errors.append('unknown-operation')
        if fact['kind'] == 'vote':
            if fact.get('choice') not in CHOICES: errors.append('unknown-choice')
            if fact.get('vote_scope') not in {'floor', 'committee'}: errors.append('vote-scope')
            if evidence['binding'] != 'official-roll' or not raw_hash: errors.append('vote-evidence')
            p = urlsplit(evidence['url'])
            if fact['jurisdiction'] == 'IL':
                if p.hostname not in {'ilga.gov', 'www.ilga.gov'} or p.path.casefold() != '/documents/reports/static/104membervotes.csv': errors.append('vote-evidence')
            else:
                m = re.fullmatch(r'US-119-(HOUSE|SENATE)-(1|2)-(\d+)', fact.get('roll_id', ''))
                if not m: errors.append('roll-identity')
                elif m[1] == 'HOUSE':
                    number = p.path.removeprefix(f'/Votes/{2024+int(m[2])}')
                    if (p.hostname != 'clerk.house.gov' or not p.path.startswith(f'/Votes/{2024+int(m[2])}')
                            or not number.isdigit() or int(number) != int(m[3])): errors.append('roll-evidence-mismatch')
                elif (p.hostname != 'www.senate.gov' or not re.fullmatch(
                        rf'/legislative/LIS/roll_call_votes/vote119{m[2]}/vote_119_{m[2]}_{int(m[3]):05d}\.(?:xml|htm)', p.path)):
                    errors.append('roll-evidence-mismatch')
            totals = fact.get('totals', {})
            if not totals or any(k not in CHOICES or type(v) is not int or v < 0 for k, v in totals.items()): errors.append('tally-schema')
            if fact.get('choice') in totals and totals[fact['choice']] == 0: errors.append('choice-tally-conflict')
        if fact['kind'] == 'hearing':
            if not fact.get('committee') or evidence['binding'] != 'official-calendar' or not raw_hash: errors.append('committee-reference')
            if urlsplit(evidence['url']).hostname not in {'ilga.gov', 'www.ilga.gov', 'www.senate.gov', 'docs.house.gov'}: errors.append('calendar-evidence')
        if fact['kind'] == 'publication':
            if not fact.get('publisher') or fact.get('publication_kind') not in {'news', 'office', 'campaign', 'party'}: errors.append('publisher-reference')
            if evidence['binding'] not in {'publisher-listing', 'screened-news-metadata'}: errors.append('publication-evidence')
    except (KeyError, ValueError, TypeError, AttributeError):
        errors.append('fact-schema')
    return sorted(set(errors))


def empty():
    return {'schema_version': VERSION, 'policy': POLICY, 'scopes': {}, 'facts': {}, 'events': [], 'exceptions': []}


def event_revision(fact, scope_id, now, previous=None, operation=None):
    fingerprint = digest(semantic(fact))
    eid = 'change-' + digest([scope_id, fact['key']])[:24]
    revision = (previous['revision'] + 1) if previous else 1
    rid = eid + '-r' + str(revision)
    occurred = fact['occurred_at']
    historical = occurred is not None and occurred[:10] < (timestamp(now) - timedelta(days=30)).date().isoformat()
    reason = ('correction to a previously accepted fact' if previous else
              'historical record first observed after baseline' if historical else
              'new source-dated activity' if occurred else 'new listing; action date not established')
    if operation == 'removed': reason = 'relationship absent from a complete member-role listing; removal date unknown'
    return {'id': eid, 'revision_id': rid, 'revision': revision,
            'supersedes': previous.get('revision_id') if previous else None,
            'previous_fingerprint': previous['fingerprint'] if previous else None,
            'previous_fact': previous['fact'] if previous else None,
            'scope': scope_id, 'fingerprint': fingerprint, 'fact': fact,
            'first_observed_at': previous.get('first_observed_at', now) if previous else now,
            'observed_at': now, 'change': operation or ('corrected' if previous else 'added'),
            'validation': 'adapter-bound', 'policy': POLICY, 'inclusion_reason': reason,
            'eligible': (not historical or previous is not None or operation == 'removed')
                        and not (fact['kind'] == 'bill-title' and previous is None)}


def reconcile(ledger, observations, now):
    timestamp(now)
    if ledger['schema_version'] != VERSION or ledger['policy'] != POLICY: raise ValueError('ledger-version-review-required')
    result = deepcopy(ledger); report = {'schema_version': VERSION, 'checked_at': now, 'status': 'ok',
        'added_revisions': 0, 'baselined_facts': 0, 'unchanged_facts': 0, 'scopes': [], 'errors': []}
    seen_scopes = set()
    established_families = {s.get('family') for s in ledger['scopes'].values()}
    for scope in observations:
        ident = scope['id']; old_scope = result['scopes'].get(ident)
        errors = []
        if ident in seen_scopes: errors.append('duplicate-scope')
        seen_scopes.add(ident)
        try:
            checked = timestamp(scope['checked_at'])
            if old_scope and checked < timestamp(old_scope['checked_at']): errors.append('source-regression')
        except (ValueError, TypeError, AttributeError): errors.append('source-time')
        if scope.get('complete') is not True: errors.append('incomplete-scope')
        incoming = {}
        for fact in scope['facts']:
            codes = validate_fact(fact, scope)
            key = fact.get('key', 'unknown')
            if key in incoming: codes.append('duplicate-fact')
            incoming[key] = fact
            errors.extend(codes)
        fp = digest({key: digest(semantic(fact)) for key, fact in incoming.items()})
        if (old_scope and old_scope['adapter'] == scope['adapter']
                and scope['checked_at'] == old_scope['checked_at'] and fp != old_scope['fingerprint']):
            errors.append('conflicting-replay')
        if errors:
            codes = sorted(set(errors)); report['status'] = 'partial'
            safe_id = digest(ident)[:20]
            report['errors'].append({'source': 'scope-' + safe_id, 'codes': codes})
            result['exceptions'] = [e for e in result['exceptions'] if e['scope_id'] != safe_id]
            result['exceptions'].append({'scope_id': safe_id, 'codes': codes, 'checked_at': now})
            report['scopes'].append({'id': ident, 'status': 'withheld', 'fact_count': len(incoming)})
            continue
        result['exceptions'] = [e for e in result['exceptions'] if e['scope_id'] != digest(ident)[:20]]
        migration = old_scope is not None and old_scope['adapter'] != scope['adapter']
        baseline = (old_scope is None and (scope.get('baseline_on_add', True)
                    or scope.get('family') not in established_families)) or migration
        current_keys = set()
        for key, fact in sorted(incoming.items()):
            stored_key = ident + '|' + key; current_keys.add(stored_key)
            old = result['facts'].get(stored_key)
            fingerprint = digest(semantic(fact))
            if old and old['fingerprint'] == fingerprint and old.get('active', True):
                old['fact'] = fact
                report['unchanged_facts'] += 1
                continue
            if baseline:
                revision = {'revision': old['revision'] if old else 0,
                            'revision_id': old.get('revision_id') if old else 'change-' + digest([ident, fact['key']])[:24] + '-r0',
                            'first_observed_at': old.get('first_observed_at', now) if old else now}
                report['baselined_facts'] += 1
            else:
                revision = event_revision(fact, ident, now, old)
                baseline_at = old_scope['baseline_at'] if old_scope else min(
                    (s['baseline_at'] for s in ledger['scopes'].values() if s.get('family') == scope.get('family')), default=now)
                # A recovered/backfilled source date before (or indistinguishable
                # at day precision from) the baseline is history, not a new alert.
                baseline_day = timestamp(baseline_at).astimezone(ZoneInfo('America/Chicago')).date().isoformat()
                before_baseline = (timestamp(fact['occurred_at']) <= timestamp(baseline_at)
                    if fact.get('occurred_at') and fact['date_precision'] == 'timestamp'
                    else bool(fact.get('occurred_at') and fact['occurred_at'][:10] <= baseline_day))
                if not old and before_baseline:
                    revision['eligible'] = False
                    revision['inclusion_reason'] = 'source date on or before the initial baseline; retained as history'
                result['events'].append(revision); report['added_revisions'] += 1
            result['facts'][stored_key] = {'fingerprint': fingerprint, 'fact': fact, 'active': True,
                **{k: revision[k] for k in ('revision', 'revision_id', 'first_observed_at')}}
        # Only authoritative complete relationship lists support absence/removal.
        # Historical actions, bounded calendars and news lists are append-only.
        if not baseline and scope.get('removals') is True:
            for key, old in list(result['facts'].items()):
                if (key.startswith(ident + '|') and key not in current_keys and old.get('active', True)
                        and old['fact']['kind'] == 'sponsor-role'):
                    removed = {**old['fact'], 'operation': 'removed', 'occurred_at': None, 'date_precision': 'unknown',
                               'detail': 'No longer present in this complete source listing; effective removal date is unknown.',
                               'evidence': {**old['fact']['evidence'], 'retrieved_at': scope['checked_at']}}
                    rev = event_revision(removed, ident, now, old, 'removed')
                    result['events'].append(rev); report['added_revisions'] += 1
                    result['facts'][key] = {**old, 'active': False, 'fingerprint': rev['fingerprint'], 'fact': removed,
                        **{k: rev[k] for k in ('revision', 'revision_id', 'first_observed_at')}}
        result['scopes'][ident] = {'adapter': scope['adapter'], 'jurisdiction': scope['jurisdiction'],
            'session': scope['session'], 'family': scope.get('family', ident), 'checked_at': scope['checked_at'], 'fingerprint': fp,
            'fact_count': len(incoming), 'baseline_at': old_scope['baseline_at'] if old_scope else now,
            'reconcile_missing': scope.get('removals') is True}
        report['scopes'].append({'id': ident, 'status': 'baseline' if baseline else 'accepted', 'fact_count': len(incoming),
            'previous_fact_count': old_scope['fact_count'] if old_scope else None})
    for ident, previous in ledger['scopes'].items():
        if ident in seen_scopes: continue
        safe_id = digest(ident)[:20]
        report['status'] = 'partial'
        report['errors'].append({'source': 'scope-' + safe_id, 'codes': ['scope-not-observed']})
        report['scopes'].append({'id': ident, 'status': 'withheld', 'fact_count': previous['fact_count']})
        result['exceptions'] = [e for e in result['exceptions'] if e['scope_id'] != safe_id]
        result['exceptions'].append({'scope_id': safe_id, 'codes': ['scope-not-observed'], 'checked_at': now})
    result['exceptions'] = result['exceptions'][-MAX_EXCEPTIONS:]
    report['accepted_facts'] = len(result['facts']); report['event_revisions'] = len(result['events'])
    report['withheld_scopes'] = sum(s['status'] == 'withheld' for s in report['scopes'])
    report['limits'] = {'ledger_bytes': MAX_LEDGER, 'exception_entries': MAX_EXCEPTIONS}
    if len(packed(result).encode()) > MAX_LEDGER: raise ValueError('change-ledger-size-budget')
    return result, report


def public_events(ledger, limit=60):
    """One selection/gate for the new HTML, JSON, Atom and future digest input."""
    latest = {}
    for event in ledger['events']:
        scope = ledger['scopes'].get(event['scope'])
        # Use the observation time, not the action date, for structural checks.
        if (scope and event['policy'] == POLICY and event['validation'] == 'adapter-bound'
                and event['fingerprint'] == digest(semantic(event['fact']))
                and not validate_fact(event['fact'], {**scope, 'checked_at': event['observed_at']})):
            latest[event['id']] = event
    return sorted((e for e in latest.values() if e['eligible']),
                  key=lambda e: (e['observed_at'], e['revision_id']), reverse=True)[:limit]


def collect(root, now):
    from .change_sources import observations
    ledger_path = root / 'data/change-ledger.json'
    ledger, report = reconcile(read(ledger_path, empty()), observations(root), now)
    report['projected_data_bytes'] = 0
    replacements = {ledger_path.name: ledger, 'change-quality-report.json': report}
    other_bytes = sum(p.stat().st_size for p in (root/'data').glob('*.json') if p.name not in replacements)
    for _ in range(3):
        report['projected_data_bytes'] = other_bytes + sum(len((packed(value)+'\n').encode()) for value in replacements.values())
    limit = read(root/'config/daily.json')['max_data_bytes']
    if report['projected_data_bytes'] > limit: raise ValueError('public-data-size-budget-exceeded')
    # Save the entire transaction once. A crash can only leave the old ledger or
    # the complete new state; never a watermark committed ahead of its events.
    for path, value in [(ledger_path, ledger), (root / 'data/change-quality-report.json', report)]:
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(packed(value) + '\n', encoding='utf-8', newline='\n')
        temporary.replace(path)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['collect'])
    parser.parse_args()
    report = collect(Path.cwd(), datetime.now(timezone.utc).isoformat())
    print(json.dumps({k: report[k] for k in ('status', 'accepted_facts', 'added_revisions', 'baselined_facts', 'withheld_scopes')}))


if __name__ == '__main__': main()
