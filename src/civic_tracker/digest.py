"""Deterministic Stage D previews. No sender, network, secret access or model calls.

This module reads accepted facts/revisions and existing public source receipts.
It has no delivery transport. A preview manifest is not a send/delivery ledger.
"""
import argparse
from collections import Counter
from datetime import datetime, time, timedelta
from hashlib import sha256
from html import escape
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from .changes import (digest, empty, packed, public_url, read, timestamp,
                      validate_fact, validated_events, semantic)
from .relevance import explain
from .hearing_changes import slip_current
from .hearing_view import time_label
from .change_feed import write_if_changed
from .privacy import violations

NAMES = {'fritts': 'Bradley Fritts', 'arellano': 'Li Arellano, Jr.', 'lahood': 'Darin LaHood',
         'durbin': 'Dick Durbin', 'duckworth': 'Tammy Duckworth',
         'lee-democrats': 'Lee County Democrats', 'lee-gop': 'Lee County IL Republicans'}
SECTIONS = {'schedule': 'Schedule and agenda revisions', 'members': 'Noteworthy member activity',
            'parties': 'Attributed county-party changes', 'news': 'Independent newsroom metadata',
            'communications': 'Office, campaign and party communications'}
FILES = ('data/change-ledger.json', 'data/change-quality-report.json', 'data/dashboard.json',
         'data/daily-report.json', 'data/party-state.json', 'data/mentions-state.json',
         'data/media-state.json', 'data/communications-state.json', 'config/digest.json',
         'config/relevance.json', 'config/hearings.json', 'config/communications.json')
ARTIFACTS = {'digest-preview.html', 'digest-preview.txt', 'digest-preview.json', 'digest-preview.css'}
ZONE = ZoneInfo('America/Chicago')


def e(value): return escape(str(value), quote=True)


def window(as_of, week_ending=None):
    local = timestamp(as_of).astimezone(ZONE)
    day = datetime.strptime(week_ending, '%Y-%m-%d').date() if week_ending else local.date() + timedelta(days=(7-local.weekday()) % 7)
    if day.weekday() != 0: raise ValueError('digest-week-ending-must-be-monday')
    end = datetime.combine(day, time(6), ZONE); start = end - timedelta(days=7)
    cutoff = min(local, end)
    if cutoff < start: raise ValueError('digest-period-not-started')
    return {'start': start.isoformat(), 'end': end.isoformat(), 'cutoff': cutoff.isoformat(),
            'cutoff_inclusive': local < end,
            'as_of': local.isoformat(), 'complete_period': local >= end,
            'opportunity_end': (local + timedelta(days=10)).isoformat(),
            'timezone': 'America/Chicago', 'definition': 'Monday 06:00 to Monday 06:00 Central; end exclusive'}


def fresh(when, as_of, hours):
    try: return 0 <= (timestamp(as_of)-timestamp(when)).total_seconds() <= hours*3600
    except (ValueError, TypeError, AttributeError): return False


def fact_rows(ledger):
    for key, stored in sorted(ledger['facts'].items()):
        scope_id, separator, fact_key = key.partition('|'); fact = stored.get('fact', {})
        scope = ledger['scopes'].get(scope_id)
        if (separator and fact_key == fact.get('key') and scope and stored.get('active', True)
                and stored.get('fingerprint') == digest(semantic(fact)) and not validate_fact(fact, scope)):
            yield scope_id, stored


def event_row(event, titles, withheld, relevance_config):
    f = event['fact']; relevance = explain(f,relevance_config)
    title_url = titles.get(f.get('measure')) or f['evidence']['url']
    return {'id': event['id'], 'revision_id': event['revision_id'], 'revision': event['revision'],
        'scope': event['scope'], 'kind': f['kind'], 'measure': f.get('measure'),
        'subjects': [NAMES[m] for m in f['members'] or f.get('entities', [])],
        'title': f['title'], 'detail': f['detail'][:650], 'source_url': public_url(f['evidence']['url']),
        'title_url': public_url(title_url), 'source_date': f['occurred_at'], 'date_precision': f['date_precision'],
        'evidence_checked_at': f['evidence']['retrieved_at'], 'first_observed_at': event['first_observed_at'],
        'observed_at': event['observed_at'], 'digest_eligible': True, 'change': event['change'],
        'reason': event['inclusion_reason'], 'topics': relevance['topics'], 'stance': 'not inferred',
        'latest_scope_withheld': event['scope'] in withheld, 'publisher': f.get('publisher'),
        'choice': f.get('choice'), 'raw_choice': f.get('raw_choice'), 'vote_scope': f.get('vote_scope'),
        'totals': f.get('totals'), 'hearing_status': f.get('status') if f['kind']=='hearing' else None,
        # Party collectors retain bounded, readable excerpts around the changed
        # span. Keep them in the digest row so a reader can understand the edit
        # without opening the full shared ledger or storing a page archive.
        'before_excerpt': f.get('before_excerpt') if f['kind'] == 'party-change' else None,
        'after_excerpt': f.get('after_excerpt') if f['kind'] == 'party-change' else None}


def opportunities(ledger, snapshot, withheld, as_of, config):
    rows = []; omitted = Counter(); now = timestamp(as_of); end = now + timedelta(days=config['opportunity_days'])
    for scope_id, stored in fact_rows(ledger):
        f = stored['fact']
        if f['kind'] != 'hearing' or not f.get('hearing_key'): continue
        value = f.get('local_time')
        if not value: omitted['undated_hearings'] += 1; continue
        try:
            start = datetime.fromisoformat(value)
            if start.tzinfo is None: start = start.replace(tzinfo=ZoneInfo(f.get('timezone', 'America/Chicago')))
        except (ValueError, KeyError): omitted['invalid_hearing_time'] += 1; continue
        # Date-only notices on today's date remain qualified as time unknown.
        if len(value) == 10:
            inside = now.astimezone(ZONE).date() <= start.astimezone(ZONE).date() <= end.astimezone(ZONE).date()
        else: inside = now <= start <= end
        if not inside: continue
        if f['status'] not in {'scheduled', 'rescheduled'}: omitted['non_usable_hearings'] += 1; continue
        if (scope_id in withheld or not fresh(f['evidence']['retrieved_at'], as_of, config['source_fresh_hours'])):
            omitted['stale_or_withheld_hearings'] += 1; continue
        raw_meetings = [m for member in snapshot.get('members', []) if member['id'] in f['members']
                        and member.get('calendar_health') not in {'failed', 'partial_or_failed'}
                        for m in member.get('meetings', []) if m.get('hearing_key') == f['hearing_key']
                        and m.get('source_url') == f['evidence']['url']
                        and m.get('evidence', {}).get('sha256') == f['evidence'].get('sha256')]
        forms = {}; agenda = {a['id']: a for a in f.get('agenda', [])}
        for meeting in raw_meetings:
            for item in meeting.get('items', []):
                # A witness claim also needs matching bill/amendment identity,
                # the existing expiry gate, and the reviewed submission URL shape.
                from .hearing_changes import amendment
                key = item.get('bill', '') + (':' + amendment(item['amendment']) if item.get('amendment') else '')
                if key not in agenda or item.get('submission_verified') is not True or not slip_current(item, meeting, as_of): continue
                url = item.get('witness_slip_url', '')
                from urllib.parse import urlsplit
                p = urlsplit(public_url(url))
                if p.hostname != 'my.ilga.gov' or '/WitnessSlip/Create/' not in p.path: continue
                forms[url] = {'bill': item['bill'], 'url': url, 'checked_at': item['submission_checked_at']}
        rows.append({'id': f['hearing_key'], 'revision_id': stored['revision_id'], 'scope': scope_id,
            'title': f['title'], 'subjects': [NAMES[m] for m in f['members']],
            'when': time_label({'date_local': value, 'timezone': f.get('timezone', 'America/Chicago'), 'time_note': f.get('time_note')}),
            'local_time': value, 'status': f['status'], 'source_url': public_url(f['evidence']['url']),
            'committee_url': public_url(f['committee']), 'evidence_checked_at': f['evidence']['retrieved_at'],
            'reason': 'accepted posted notice within the next ten days; committee membership does not establish attendance',
            'agenda': [{'id': a['id'], 'url': public_url(a['official_url'])} for a in f.get('agenda', [])[:config['max_agenda_items']]],
            'agenda_omitted': max(0, len(f.get('agenda', []))-config['max_agenda_items']),
            'agenda_coverage': f.get('agenda_coverage'), 'witness_forms': sorted(forms.values(), key=lambda x:x['url'])[:6]})
    rows.sort(key=lambda x:(x['local_time'], x['id']))
    omitted['bounded_hearings'] = max(0, len(rows)-config['max_hearings'])
    return rows[:config['max_hearings']], omitted


def health(inputs, as_of, config, quality):
    rows = []
    def add(label, status, when, source=None):
        if status == 'link-only': state = 'link only; no dated collection'
        elif status not in {'ok', 'checked', 'complete'}: state = 'partial or unavailable'
        else: state = 'ok' if fresh(when, as_of, config['source_fresh_hours']) else 'stale or not checked'
        rows.append({'label': label, 'status': state, 'checked_at': when, 'source_url': source})
    for label, report in inputs.get('data/daily-report.json', {}).get('sources', {}).items():
        add(label, report.get('status'), report.get('checked_at'))
    for p in inputs.get('data/party-state.json', {}).get('pages', {}).values():
        add(p['publisher'] + ' · ' + p['label'], p['status'], p['checked_at'], public_url(p['url']))
    for label, p in inputs.get('data/mentions-state.json', {}).get('sources', {}).items():
        add('Capitol Fax headline check · ' + label, p['status'], p['checked_at'], public_url(p['url']))
    for label, p in inputs.get('data/media-state.json', {}).get('members', {}).items():
        add('News discovery · ' + NAMES[label], p.get('status'), p.get('checked_at'))
    snapshot = inputs.get('data/dashboard.json', {})
    receipts = inputs.get('data/media-state.json', {}).get('members', {})
    for member in snapshot.get('members', []):
        if member.get('media_health'):
            add('News relevance screening · ' + NAMES[member['id']], member['media_health'].get('inference_status'),
                receipts.get(member['id'], {}).get('checked_at'))
    labels = {p['id']:p['label'] for p in inputs.get('config/communications.json', {'sources':[]})['sources']}
    for ident, p in inputs.get('data/communications-state.json', {}).get('sources', {}).items():
        add('Direct communication · ' + labels.get(ident, ident),
            p.get('status'), p.get('checked_at'))
    rows.sort(key=lambda r:(r['status']=='ok', r['label']))
    return {'status': 'partial' if quality.get('status') != 'ok' or any(r['status']!='ok' for r in rows) else 'ok',
        'withheld_scopes': sorted(s['id'] for s in quality.get('scopes', []) if s['status']=='withheld'),
        'rows': rows[:48], 'omitted_rows': max(0,len(rows)-48), 'quality_checked_at': quality.get('checked_at'),
        'limits': 'Missing entries do not establish inactivity. Source failures retain prior accepted records. PDF work remains deferred.'}


def preview(root, as_of=None, week_ending=None):
    # Read each input once: rendered content and recorded fingerprints describe
    # the same bytes even if another process replaces a source file later.
    raw_inputs = {name:(root/name).read_bytes() for name in FILES if (root/name).exists()}
    inputs = {name:json.loads(raw) for name,raw in raw_inputs.items()}
    config = inputs['config/digest.json']; relevance_config = inputs['config/relevance.json']
    if (config.get('schema_version') != 1 or config.get('delivery_enabled') is not False
            or config.get('timezone') != 'America/Chicago' or config.get('opportunity_days') != 10):
        raise ValueError('digest-preview-only-config')
    if (not 1 <= config['max_events'] <= 20 or not 1 <= config['max_per_section'] <= 6
            or not 1 <= config['max_hearings'] <= 8 or not 1 <= config['max_agenda_items'] <= 6
            or not 1 <= config['max_artifact_bytes'] <= 90000
            or not 1 <= config['source_fresh_hours'] <= 48): raise ValueError('digest-config-bound')
    ledger = inputs.get('data/change-ledger.json', empty()); quality = inputs.get('data/change-quality-report.json', {})
    # Mutable current baselines do not retain every earlier proof. A historical
    # replay needs the frozen input revision, not a backdated current snapshot.
    clocks = []
    def clocks_in(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {'checked_at','retrieved_at','observed_at','generated_at','submission_checked_at'} and child:
                    clocks.append(timestamp(child))
                elif isinstance(child,(dict,list)): clocks_in(child)
        elif isinstance(value,list):
            for child in value: clocks_in(child)
    for name,value in inputs.items():
        if name.startswith('data/'): clocks_in(value)
    if not clocks: raise ValueError('digest-source-reference-required')
    reference = max(clocks)
    if as_of and timestamp(as_of) < reference: raise ValueError('digest-historical-source-snapshot-required')
    as_of = as_of or reference.isoformat()
    period = window(as_of, week_ending); start = timestamp(period['start']); cutoff = timestamp(period['cutoff'])
    withheld = {s['id'] for s in quality.get('scopes', []) if s['status']=='withheld'}
    titles = {s['fact']['measure']:s['fact']['evidence']['url'] for _,s in fact_rows(ledger) if s['fact']['kind']=='bill-title'}
    latest = {}
    for event in validated_events(ledger):
        observed = timestamp(event['observed_at'])
        if observed < cutoff or (observed == cutoff and period['cutoff_inclusive']):
            old = latest.get(event['id'])
            if old is None or event['revision'] > old['revision']: latest[event['id']] = event
    omitted = Counter(); sections = {k:[] for k in SECTIONS}; selected = []
    for event in sorted(latest.values(), key=lambda r:(r['observed_at'], r['revision_id']), reverse=True):
        f = event['fact']
        if timestamp(event['observed_at']) < start: continue
        if not event['eligible']: omitted['baseline_history_or_held_review'] += 1; continue
        if explain(f,relevance_config)['hidden']: omitted['ceremony_or_no_opposition'] += 1; continue
        if f['occurred_at'] and f['kind'] != 'hearing' and event['change']=='added':
            old_date = (timestamp(f['occurred_at']) < start if f['date_precision']=='timestamp'
                        else f['occurred_at'] < start.astimezone(ZONE).date().isoformat())
            if old_date: omitted['late_historical_discovery'] += 1; continue
        section = ('schedule' if f['kind']=='hearing' else 'parties' if f['kind']=='party-change'
                   else 'news' if f.get('publication_kind')=='news'
                   else 'communications' if f['kind']=='publication' else 'members')
        if len(selected) >= config['max_events'] or len(sections[section]) >= config['max_per_section']:
            omitted['bounded_events'] += 1; continue
        row = event_row(event, titles, withheld, relevance_config); sections[section].append(row); selected.append(row['revision_id'])
    snapshot = inputs.get('data/dashboard.json', {})
    upcoming, hearing_omissions = opportunities(ledger, snapshot, withheld, as_of, config)
    omitted.update(hearing_omissions)
    fingerprints = {name:sha256(raw).hexdigest() for name,raw in raw_inputs.items()}
    data = {'schema_version':1, 'policy':'stage-d-preview-1', 'delivery':{'enabled':False,'state':'preview-only','attempts':0},
        'period':period, 'opportunities':upcoming, 'sections':sections, 'selected_revision_ids':selected,
        'health':health(inputs,as_of,config,quality), 'omitted':dict(sorted(omitted.items())),
        'quiet':not selected, 'input_sha256':fingerprints, 'model_calls':0,
        'limits':{'artifact_bytes':config['max_artifact_bytes']},
        'method':'Accepted shared revisions only; quiet hearing baselines may supply future notices. No scraping, generated bill synopsis, inferred stance or delivery.'}
    data['preview_id'] = 'digest-' + digest(data)[:24]
    return data


CSS = "body{font:16px/1.55 system-ui,sans-serif;color:#243b3b;background:#f7f6f1;margin:0}main{max-width:850px;margin:32px auto;padding:28px;background:#fff;border:1px solid #ddd}h1,h2{font-family:Georgia,serif}h2{border-top:1px solid #ddd;padding-top:20px}a{color:#245b55}li{margin:16px 0}.banner{background:#fff2cd;padding:14px;border-left:4px solid #b4841a}.minor{font-size:13px;color:#596661}.health{font-size:14px}pre{white-space:pre-wrap}"


def render_text(data):
    p = data['period']; lines = ['ILLINOIS CIVIC TRACKER · DIGEST PREVIEW', 'EMAIL DELIVERY DISABLED — review only; no message was sent.',
        'Preview: ' + data['preview_id'], 'Activity window: ' + p['start'] + ' to ' + p['cutoff'] + (' (snapshot cutoff included).' if p['cutoff_inclusive'] else ' (end exclusive).'),
        'Week ending: ' + p['end'] + (' · complete period' if p['complete_period'] else ' · week so far'),
        'Prepared from source receipts as of ' + p['as_of'] + '. Activity windows and hearing times use America/Chicago; evidence timestamps retain their offsets.',
        'Source health: ' + data['health']['status'] + '. Missing entries do not establish inactivity.',
        '', 'NEXT TEN DAYS · POSTED HEARINGS & PARTICIPATION LINKS']
    for row in data['opportunities']:
        lines += [row['when'] + ' · ' + row['title'] + ' · ' + row['status'], ', '.join(row['subjects']),
                  'Official notice: ' + row['source_url'], 'Committee: ' + row['committee_url'], 'Why included: ' + row['reason']]
        for a in row['agenda']: lines += ['Agenda ' + a['id'] + ': ' + a['url']]
        for form in row['witness_forms']: lines += ['Verified open witness form · ' + form['bill'] + ': ' + form['url'] + ' · checked ' + form['checked_at']]
        if not row['witness_forms']: lines += ['No current verified open witness form in this collected notice.']
        lines += ['Source checked: ' + row['evidence_checked_at'], '']
    if not data['opportunities']: lines += ['No fresh accepted upcoming notices in this window. Use official committee schedules; coverage may be incomplete.']
    for key, title in SECTIONS.items():
        lines += ['', title.upper()]
        for row in data['sections'][key]:
            lines += [', '.join(row['subjects']) + ' · ' + row['title'], 'Change: ' + row['change'], row['detail'],
                'Source: ' + row['source_url'], 'Source date: ' + (row['source_date'] or 'unknown') + ' (' + row['date_precision'] + ')',
                'First observed: ' + row['first_observed_at'] + ' · revision observed: ' + row['observed_at'],
                'Why included: ' + row['reason'], 'Revision: ' + row['revision_id']]
            if row['before_excerpt'] or row['after_excerpt']:
                lines += ['Before: ' + (row['before_excerpt'] or '[unavailable]'),
                          'After: ' + (row['after_excerpt'] or '[unavailable]')]
            if row['publisher']: lines += ['Published by ' + row['publisher'] + '; claims attributed, not independently verified.']
            if row['choice']: lines += ['Recorded ' + str(row['vote_scope']) + ' choice: ' + row['choice'] + ' · raw: ' + str(row['raw_choice']) + ' · tally: ' + packed(row['totals'])]
            if row['latest_scope_withheld']: lines += ['Latest scope check incomplete; last accepted evidence retained.']
            for topic in row['topics']: lines += ['Topic ' + topic['topic'] + ': ' + '; '.join(topic['reasons']) + ' (stance not inferred)']
            lines += ['']
        if not data['sections'][key]: lines += ['No accepted new items selected for this period. This does not establish inactivity.']
    lines += ['', 'SOURCE HEALTH & LIMITS', str(len(data['health']['withheld_scopes'])) + ' withheld source scopes.']
    for row in data['health']['rows']: lines += [row['label'] + ': ' + row['status'] + ' · checked ' + str(row['checked_at']) + (' · ' + row['source_url'] if row['source_url'] else '')]
    lines += ['Omission audit: ' + packed(data['omitted']), data['health']['limits'], data['method'],
              'Quiet baselines and older backfill are not activity today. A page edit does not establish an event date.',
              'No email, outreach, witness slip, model request or PDF extraction is performed by this preview.']
    return '\n'.join(lines) + '\n'


def render_html(data):
    p = data['period']; pieces = [f'<nav><a href="./">Tracker home</a> · <a href="digest-preview.txt">Plain text ↓</a> · <a href="digest-preview.json">Selection manifest ↓</a></nav><h1>Weekly digest preview</h1><p class="banner"><strong>Email delivery disabled.</strong> Review only. No message was sent.</p>',
        f'<p>Week ending {e(p["end"])} · {"complete period" if p["complete_period"] else "week so far"}<br>Activity: {e(p["start"])} through {e(p["cutoff"])} ({"snapshot cutoff included" if p["cutoff_inclusive"] else "end exclusive"}).<br>Prepared as of {e(p["as_of"])} · America/Chicago.</p>',
        f'<p>Source health: <strong>{e(data["health"]["status"])}</strong>. Missing entries do not establish inactivity.</p>',
        '<h2>Next ten days · posted hearings &amp; participation links</h2><ul>']
    for row in data['opportunities']:
        items = ''.join(f'<li><a href="{e(a["url"])}">{e(a["id"])}</a></li>' for a in row['agenda'])
        forms = ''.join(f'<p><a href="{e(f["url"])}">{e(f["bill"])} · verified open witness form</a> · checked {e(f["checked_at"])}</p>' for f in row['witness_forms'])
        pieces += [f'<li><strong>{e(row["when"])} · <a href="{e(row["source_url"])}">{e(row["title"])}</a></strong><p>{e(", ".join(row["subjects"]))} · {e(row["status"])} · <a href="{e(row["committee_url"])}">Committee website</a></p><p>{e(row["reason"])}</p><ul>{items}</ul>{forms or "<p>No current verified open witness form in this collected notice.</p>"}<p class="minor">Source checked {e(row["evidence_checked_at"])} · agenda coverage {e(row["agenda_coverage"])} · {row["agenda_omitted"]} additional agenda items at the notice.</p></li>']
    if not data['opportunities']: pieces += ['<li>No fresh accepted upcoming notices in this window. Use official committee schedules; coverage may be incomplete.</li>']
    pieces += ['</ul>']
    for key, title in SECTIONS.items():
        pieces += [f'<h2>{e(title)}</h2><ul>']
        for row in data['sections'][key]:
            choice = f'<p>Recorded {e(row["vote_scope"])} choice: <a href="{e(row["source_url"])}">{e(row["choice"])} ({e(row["raw_choice"])})</a> · tally {e(packed(row["totals"]))}</p>' if row['choice'] else ''
            attribution = f'<p>Published by {e(row["publisher"])}; claims attributed, not independently verified.</p>' if row['publisher'] else ''
            warning = '<p>Latest scope check incomplete; last accepted evidence retained.</p>' if row['latest_scope_withheld'] else ''
            topics = '; '.join(t['topic'] + ': ' + ', '.join(t['reasons']) for t in row['topics'])
            diff = ''
            if row['before_excerpt'] or row['after_excerpt']:
                diff = f'<details><summary>What changed on the party page</summary><p><strong>Before:</strong> {e(row["before_excerpt"] or "[unavailable]")}<br><strong>After:</strong> {e(row["after_excerpt"] or "[unavailable]")}</p><p class="minor">These are bounded excerpts around the changed span; the tracker does not retain a full page archive.</p></details>'
            pieces += [f'<li><p class="minor">{e(", ".join(row["subjects"]))} · {e(row["kind"])} · Change: {e(row["change"])}</p><strong><a href="{e(row["title_url"])}">{e(row["title"])}</a></strong><p>{e(row["detail"])}</p>{diff}{choice}{attribution}{warning}<p>Why included: {e(row["reason"])}</p><p class="minor">Source date: {e(row["source_date"] or "unknown")} ({e(row["date_precision"])}). First observed {e(row["first_observed_at"])}; revision observed {e(row["observed_at"])}.<br>{e(topics)} Stance is not inferred.<br>Revision {e(row["revision_id"])} · <a href="{e(row["source_url"])}">Source evidence</a></p></li>']
        if not data['sections'][key]: pieces += ['<li>No accepted new items selected for this period. This does not establish inactivity.</li>']
        pieces += ['</ul>']
    pieces += [f'<h2>Source health &amp; limits</h2><p>{len(data["health"]["withheld_scopes"])} withheld source scopes. This is a preview of accepted records, not complete activity coverage.</p><details><summary>Source check dates and coverage</summary><ul class="health">']
    for row in data['health']['rows']:
        label = f'<a href="{e(row["source_url"])}">{e(row["label"])}</a>' if row['source_url'] else e(row['label'])
        pieces += [f'<li>{label}: {e(row["status"])} · checked {e(row["checked_at"])}</li>']
    pieces += [f'</ul><p>{data["health"]["omitted_rows"]} additional source rows omitted from this bounded view.</p></details><details><summary>Selection and omission audit</summary><p>{e(packed(data["omitted"]))}</p><p>{e(data["method"])}</p><p>Preview {e(data["preview_id"])} · exact revision IDs, windows and input fingerprints are in the selection manifest.</p></details>',
        '<p class="minor">Quiet baselines and recovered backfill are not new activity today. Image/unclear party edits remain held for review. Source dates and observation dates are distinct; a page edit does not establish an event date. Published hearing notices do not prove attendance, and open-form availability can change. No stance is inferred. PDF work remains deferred.</p><p class="banner">Email delivery is disabled. This preview contains no recipient and is not a delivery attempt.</p>']
    csp = "default-src 'none'; style-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'"
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta http-equiv="Content-Security-Policy" content="' + e(csp) + '"><title>Digest preview · Illinois civic tracker</title><link rel="stylesheet" href="digest-preview.css"></head><body><main>' + ''.join(pieces) + '</main></body></html>\n'


def artifacts(root, as_of=None, week_ending=None):
    data = preview(root, as_of, week_ending)
    output = {'digest-preview.html':render_html(data), 'digest-preview.txt':render_text(data),
              'digest-preview.json':packed(data)+'\n', 'digest-preview.css':CSS+'\n'}
    if any(violations(value) for value in output.values()): raise ValueError('digest-sensitive-content')
    size = sum(len(v.encode()) for v in output.values())
    if size > data['limits']['artifact_bytes']: raise ValueError('digest-artifact-size-budget')
    return output, {'preview_id':data['preview_id'], 'artifact_bytes':size,
                    'selected_revisions':len(data['selected_revision_ids']), 'opportunities':len(data['opportunities']),
                    'delivery_enabled':False, 'model_calls':0}


def build(root, output, as_of=None, week_ending=None):
    contents, report = artifacts(root, as_of, week_ending)
    if output.is_symlink(): raise ValueError('digest-output-not-owned')
    output.mkdir(parents=True,exist_ok=True); lock = output/'.digest-preview.lock'
    try: fd = os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError: raise ValueError('digest-preview-busy') from None
    try:
        if any(p.is_symlink() or not p.is_file() or p.name not in ARTIFACTS|{lock.name} for p in output.iterdir()):
            raise ValueError('digest-output-not-owned')
        for name, content in contents.items(): write_if_changed(output/name,content)
    finally: os.close(fd); lock.unlink()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('command',choices=['preview'])
    parser.add_argument('--as-of'); parser.add_argument('--week-ending'); parser.add_argument('--output',type=Path,default=Path('.local/digest-preview'))
    args = parser.parse_args(); print(json.dumps(build(Path.cwd(),args.output,args.as_of,args.week_ending)))


if __name__=='__main__': main()
