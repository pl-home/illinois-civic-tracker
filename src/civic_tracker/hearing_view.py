"""Bounded, accessible hearing navigation and source-validated agenda detail."""
from collections import defaultdict
from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo
from .changes import read, empty, validate_fact, validated_events, digest, semantic
from .hearing_changes import day, slip_current


def e(value): return escape(str(value or ''), quote=True)


def time_label(meeting):
    value = meeting.get('date_local')
    if not value: return 'Date not announced · ' + (meeting.get('time_note') or 'check the official notice')
    if len(value) == 10: return value + ' · ' + (meeting.get('time_note') or 'Time not supplied')
    local = datetime.fromisoformat(value).replace(tzinfo=ZoneInfo(meeting.get('timezone', 'America/Chicago')))
    return local.astimezone(ZoneInfo('America/Chicago')).strftime('%b %d, %Y · %I:%M %p %Z')


def meeting_row(meeting, reference=None, role=None, history=(), anchor=None, agenda_limit=12):
    role = role or {}
    rows = []
    for item in meeting.get('items', [])[:agenda_limit]:
        label = item['bill'] + (' · ' + item['amendment'] if item.get('amendment') else '')
        contexts = item.get('contexts') or [{k: item.get(k) for k in ('motion','vote_motion','vote_result')}]
        details = '; '.join(' · '.join(filter(None, (c.get('motion'), c.get('vote_motion'), c.get('vote_result')))) for c in contexts)
        url = item.get('official_url')
        title = f'<a href="{e(url)}">{e(label)} ↗</a>' if url else e(label)
        rows.append(f'<li>{title}<p class="minor">{e(details)}</p></li>')
    count = len(meeting.get('items', [])); coverage = meeting.get('agenda_coverage', 'not-collected')
    if coverage != 'complete':
        agenda_note = 'Agenda not published in the supported notice table.' if coverage == 'not-published' else 'Bill-level agenda not collected from this calendar feed. Open the official notice.'
    else: agenda_note = 'Published agenda is empty.' if not count else 'HTML agenda context; this is not a member roll-call record.'
    remaining = f'<p class="minor">{count-len(rows)} further agenda items are available at the official notice.</p>' if count > len(rows) else ''
    docket = f'<details class="hearing-agenda"><summary>Agenda · {count} bill/amendment items</summary><p class="minor">{e(agenda_note)}</p><ul>{"".join(rows)}</ul>{remaining}</details>'
    slips = []
    for item in meeting.get('slip_items', meeting.get('items', [])):
        if reference and item.get('witness_slip_url') and slip_current(item, meeting, reference):
            slips.append(f'<li><a class="verified-slip" data-verified-at="{e(item["submission_checked_at"])}" data-notice="{e(meeting["source_url"])}" href="{e(item["witness_slip_url"])}">{e(item["bill"])} — open witness-slip form ↗</a><small>Verified {e(item["submission_checked_at"])}; availability can change.</small></li>')
    role_html = f'<p class="minor">Tracked member role: {e(role.get("role") or "not verified")}'
    role_html += f' · <a href="{e(role["role_source_url"])}">role source ↗</a>' if role and role.get('role_source_url') else ''
    role_html += '</p>'
    retained = '<p class="warning">Latest source check is incomplete; last-good notice retained with its original evidence date. Witness-form claims are disabled.</p>' if meeting.get('retained_after_failure') else ''
    notices = f'<blockquote>{e(meeting["status_notice"])}</blockquote>' if meeting.get('status_notice') else ''
    unconfirmed = '<p class="warning">Not in the checked schedule listing. The detail page does not confirm cancellation.</p>' if meeting.get('status') == 'unconfirmed' else ''
    revisions = ''.join(f'<li>Observed {e(r["observed_at"])} · {e(r["inclusion_reason"])}</li>' for r in history)
    revisions = f'<details><summary>Observed hearing changes ({len(history)} shown)</summary><ol>{revisions}</ol><p class="minor">Observation time is when the tracker found the revision, not when the committee made it. Full compact revisions remain in the repository.</p></details>' if revisions else '<p class="minor">Quiet baseline or no later material changes observed.</p>'
    attributes = f' id="{e(anchor)}" data-hearing="true" data-hearing-day="{e(day(meeting) or "9999")}" data-hearing-committee="{digest(meeting["committee_url"])[:20]}"' if anchor else ''
    return f'''<li class="meeting-row"{attributes}><time>{e(time_label(meeting))}</time><span class="tag">{e(meeting.get('status', 'scheduled'))}</span>{retained}{unconfirmed}
<strong><a href="{e(meeting['committee_url'])}">{e(meeting['committee_name'])} ↗</a></strong>{role_html}<p>Location: {e(meeting.get('location') or 'not supplied')}</p>{notices}
<a href="{e(meeting['source_url'])}">Official meeting details ↗</a><p class="minor">Notice posted: {e(meeting.get('posting_date_local') or 'not supplied')} · Source checked: {e(meeting.get('source_checked_at') or 'not supplied')}</p>{docket}
{'<ul class="slip-links">'+''.join(slips)+'</ul>' if slips else '<p class="minor">No current verified open witness-slip form in this collected docket.</p>'}{revisions}</li>'''


def sections(root, snapshot):
    options = read(root/'config/hearings.json'); ledger = read(root/'data/change-ledger.json', empty())
    quality = read(root/'data/change-quality-report.json', {})
    withheld = {s['id'] for s in quality.get('scopes', []) if s['status'] == 'withheld'}
    histories = defaultdict(list)
    for event in validated_events(ledger):
        if event['fact']['kind'] == 'hearing': histories[event['fact']['key']].append(event)
    members = {m['id']: m for m in snapshot['members']}
    reference = max([snapshot.get('generated_at') or '1970-01-01T00:00:00+00:00',
        snapshot.get('daily_refresh', {}).get('sources', {}).get('Calendars', {}).get('checked_at') or '',
        *[p.get('checked_at', '') for p in snapshot.get('calendar_sources', [])]])
    candidates = []
    for stored in ledger['facts'].values():
        f = stored['fact']
        if f['kind'] != 'hearing' or not f.get('hearing_key'): continue
        if stored['fingerprint'] != digest(semantic(f)): continue
        scope_id = next((s for s in ledger['scopes'] if s == 'calendar:' + f['committee']), None)
        scope = ledger['scopes'].get(scope_id)
        if not scope or validate_fact(f, scope): continue
        when = {'date_local': f.get('local_time'), 'timezone': f.get('timezone', 'America/Chicago')}
        date = day(when)
        if date and not snapshot['as_of'] <= date <= snapshot['calendar_end']: continue
        if not date and f['evidence']['retrieved_at'][:10] < (datetime.fromisoformat(snapshot['as_of'])-timedelta(days=7)).date().isoformat(): continue
        candidates.append((date or '9999', f, scope_id))
    output = defaultdict(list); navigation = []; dates = set(); committees = {}; used = 4000; omitted = 0
    for date, f, scope_id in sorted(candidates, key=lambda item: (item[0], item[1]['key'])):
        first_anchor = None
        ident = digest(f['committee'])[:20]
        # Account for escaped navigation/option labels, not just docket bodies.
        nav_reserve = 1000 + len(e(f['title']).encode()) + len(e(f.get('time_note')).encode())
        nav_reserve += 0 if ident in committees else 100 + len(e(f['title']).encode())
        nav_reserve += 0 if date in dates else 100
        for member_id in f['members']:
            if member_id not in members: continue
            member = members[member_id]
            role = next((c for c in member.get('committees', []) if c['url'] == f['committee']), {})
            raw = next((m for m in member.get('meetings', []) if m.get('hearing_key') == f['hearing_key']), {})
            stale = scope_id in withheld or role.get('health') in {'failed', 'partial'} or member.get('calendar_health') == 'failed'
            matching = raw.get('evidence', {}).get('sha256') == f['evidence'].get('sha256') and not stale
            view = {'date_local': f.get('local_time'), 'timezone': f.get('timezone', 'America/Chicago'),
                'time_note': f.get('time_note'), 'committee_url': f['committee'], 'committee_name': f['title'],
                'source_url': f['evidence']['url'], 'status': f['status'], 'status_notice': f.get('status_notice'),
                'posting_date_local': f.get('posting_date_local'), 'source_checked_at': f['evidence']['retrieved_at'],
                'location': f.get('location'), 'items': f.get('agenda', []), 'agenda_coverage': f['agenda_coverage'],
                'retained_after_failure': stale, 'slip_items': raw.get('items', []) if matching else []}
            anchor = 'notice-' + digest(f['hearing_key'])[:20] + '-' + member_id
            history = histories[f['key']][-options['public_hearing_revisions']:][::-1]
            html = meeting_row(view, reference, role, history, anchor, options['public_agenda_items_per_hearing'])
            overhead = nav_reserve if first_anchor is None else 0
            if used + len(html.encode()) + overhead > options['public_calendar_bytes']:
                html = meeting_row(view, reference, role, (), anchor, 0)
            if used + len(html.encode()) + overhead > options['public_calendar_bytes']:
                omitted += 1; continue
            used += len(html.encode()) + overhead
            output[member_id].append(html); first_anchor = first_anchor or anchor
        if first_anchor:
            ident = digest(f['committee'])[:20]; dates.add(date); committees[ident] = f['title']
            navigation.append(f'<li data-hearing-day="{e(date)}" data-hearing-committee="{ident}" class="hearing-nav-row"><a href="#{first_anchor}">{e(time_label({"date_local": f.get("local_time"), "timezone": f.get("timezone", "America/Chicago"), "time_note": f.get("time_note")}))} · {e(f["title"])} · {e(f["status"])}</a><span class="minor"> · {e(", ".join(members[m]["name"] for m in f["members"] if m in members))}</span></li>')
    date_options = ''.join(f'<option value="{e(d)}">{e(d if d != "9999" else "Date not announced")}</option>' for d in sorted(dates))
    committee_options = ''.join(f'<option value="{e(k)}">{e(v)}</option>' for k,v in sorted(committees.items(), key=lambda item:item[1]))
    body = ''.join(navigation) or '<li>No accepted posted hearings in this window. Source coverage may be incomplete; use the committee schedules below.</li>'
    nav = f'''<section id="hearings" class="dashboard-coverage"><h2>Find a committee hearing</h2><p>{e(snapshot['as_of'])} through {e(snapshot['calendar_end'])} · times converted to Central when published. A listed committee role does not establish attendance.</p>
<div class="hearing-filters"><label for="hearing-day">Day <select id="hearing-day"><option value="">All days</option>{date_options}</select></label><label for="hearing-committee">Committee <select id="hearing-committee"><option value="">All committees</option>{committee_options}</select></label><button id="hearing-reset" type="button">Reset filters</button></div><p id="hearing-filter-count" role="status" aria-live="polite">{len(navigation)} distinct hearing notices</p><ul>{body}</ul><p class="minor" id="hearing-no-match" hidden>No hearings match these filters.</p><p class="minor">{omitted} detail views omitted to keep the page small; use official notices for full dockets. Agenda disappearance is not postponement. A cancellation needs an explicit official notice. Missing hearings are not proof of inactivity.</p><noscript>All accepted notices and links remain available without JavaScript; use your browser's Find function for a date or committee.</noscript></section>'''
    for member_id, member in members.items():
        if any('calendar:' + c['url'] in withheld for c in member.get('committees', [])):
            output[member_id].insert(0, '<li class="warning">Some current hearing observations were withheld by source or identity checks. Last-good notices may be retained; open the committee schedules below for unresolved or newly published entries.</li>')
    return nav, {m: ''.join(rows) for m,rows in output.items()}
