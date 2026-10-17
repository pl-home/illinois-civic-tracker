"""Render the member homepage from a bounded, source-attributed snapshot."""
from datetime import datetime
from html import escape
import json
from zoneinfo import ZoneInfo
from .rules import ceremonial


def e(value):
    return escape(str(value or ''), quote=True)


def activity_row(item, cutoff, as_of):
    older = item['date'] < cutoff
    labels = {'sponsorship': 'Sponsorship', 'introduction': 'Introduction / filing', 'bill_status': 'Related bill update', 'vote': 'Vote'}
    kind = labels[item['kind']]
    scope = ('Committee' if item.get('scope') == 'committee' else 'Floor') if item['kind'] == 'vote' else ''
    choice = item.get('raw_choice') or item.get('choice') or ''
    choice_label = {'yes': 'Yea', 'no': 'Nay', 'present': 'Present', 'not-voting': 'Not voting',
                    'excused': 'Excused', 'absent': 'Absent'}.get(item.get('choice'), 'Unresolved choice')
    # Y/N are retained as raw source values alongside the normalized choice.
    is_vote = item['kind'] == 'vote'
    vote = f'<a class="vote-choice" href="{e(item["source_url"])}" title="Open official roll-call record"><strong>{e(choice_label)} <small>({e(choice)})</small></strong></a>' if is_vote else ''
    title_text = f'{e(item.get("measure"))} · {e(item["title"])}'
    title_url = item.get('bill_url') if is_vote else item['source_url']
    title = f'<a href="{e(title_url)}">{title_text} ↗</a>' if title_url else title_text

    conflict = ''
    if item.get('pdf_date') and item['pdf_date'] != item['date']:
        conflict = f'<p class="warning">Source date conflict: index {e(item["date"])}; PDF {e(item["pdf_date"])}.</p>'
    return f'''<li class="activity-row"><div class="activity-date"><time>{e(item['date'])}</time><span class="tag">{e(scope)} {e(kind)}</span>{'<span class="older-tag">Outside recent window</span>' if older else ''}</div><div><p class="activity-title">{title}</p>{vote}<p class="activity-detail">{e(item['detail'])}</p>{f'<p class="minor">{e(item["attribution"])}</p>' if item.get('attribution') else ''}{conflict}</div></li>'''


def meeting_row(meeting):
    local = datetime.fromisoformat(meeting['date_local']).replace(tzinfo=ZoneInfo(meeting['timezone']))
    central = local.astimezone(ZoneInfo('America/Chicago'))
    date_text = central.strftime('%b %d, %Y · %I:%M %p %Z')
    slips = []
    for bill in meeting.get('items', []):
        if bill.get('witness_slip_url') and bill.get('submission_verified'):
            slips.append(f'<li><a href="{e(bill["witness_slip_url"])}">{e(bill["bill"])} — open witness-slip form ↗</a></li>')
    return f'''<li class="meeting-row"><time>{e(date_text)}</time><strong><a href="{e(meeting['committee_url'])}">{e(meeting['committee_name'])} ↗</a></strong><p>{e(meeting.get('description') or meeting.get('location'))}</p><a href="{e(meeting['source_url'])}">Official meeting details ↗</a>{'<ul class="slip-links">'+''.join(slips)+'</ul>' if slips else '<p class="minor">No verified open witness-slip form in this collected docket.</p>'}</li>'''


def member_card(member, snapshot):
    cutoff = snapshot['recent_start']; as_of = snapshot['as_of']
    quiet = sum(ceremonial(item['title']) for item in member['events'])
    visible = [item for item in member['events'] if not ceremonial(item['title'])]
    recent = [item for item in visible if cutoff <= item['date'] <= as_of and item['kind'] != 'vote']
    latest = [item for item in visible if item['kind'] in ('sponsorship', 'introduction')][:3]
    votes = [item for item in visible if item['kind'] == 'vote'][:4]
    committee_vote = next((item for item in visible if item.get('scope') == 'committee'), None)
    if committee_vote and committee_vote not in votes:
        votes.append(committee_vote)
    body = ''.join(activity_row(item, cutoff, as_of) for item in recent)
    if not body:
        body = '<li class="empty-source">No dated sponsorship or related-bill entries in this window in the imported records. This is not proof of inactivity.</li>'
    older = [item for item in latest if item['date'] < cutoff]
    if older:
        body += '<li><details class="older-context"><summary>Latest available sponsorship / filing entries (older)</summary><ul class="activity-list">' + ''.join(activity_row(item, cutoff, as_of) for item in older) + '</ul></details></li>'
    vote_body = ''.join(activity_row(item, cutoff, as_of) for item in votes) or '<li class="empty-source">Recorded vote coverage is unavailable.</li>'
    all_recent_votes = [item for item in visible if item['kind'] == 'vote' and cutoff <= item['date'] <= as_of]
    if len(all_recent_votes) > len(votes):
        vote_body += '<li><details class="older-context"><summary>All recent recorded votes (' + str(len(all_recent_votes)) + ')</summary><ul class="activity-list">' + ''.join(activity_row(item, cutoff, as_of) for item in all_recent_votes) + '</ul></details></li>'
    if member['calendar_health'] in ('failed', 'partial_or_failed'):
        calendar_note = 'Calendar coverage is incomplete. Open the official committee schedules to check dates.'
    else:
        calendar_note = 'No matching meetings are currently published in the calendar pages checked for this window. Sources may not yet post the full month.'
    meetings = ''.join(meeting_row(meeting) for meeting in member['meetings']) or f'<li class="empty-source">{e(calendar_note)}</li>'
    committee_links = []
    for committee in member.get('committees', []):
        schedule_link = f' · <a href="{e(committee["schedule_url"])}">Hearings ↗</a>' if committee.get('schedule_url') else ''
        warning = ' · check failed' if committee.get('health') == 'failed' else ''
        role = committee.get('role') or 'Role not verified'
        role_label = f'<a class="committee-role" href="{e(committee["role_source_url"])}" aria-label="Role source: {e(role)}">{e(role)}</a>' if committee.get('role_source_url') else f'<span class="committee-role">{e(role)}</span>'
        committee_links.append(f'<li><a href="{e(committee["url"])}">{e(committee["name"])} ↗</a> {role_label}{schedule_link}{warning}</li>')
    committees = ''.join(committee_links)
    listings = member.get('sponsorship_listings', [])
    listing_html = ''
    if listings:
        listing_html = '<details class="sponsorship-list"><summary>Cosponsorship listings · join dates unavailable</summary><p class="minor">These source listings do not establish when the member joined or whether the role later changed.</p><ul>' + ''.join(f'<li><a href="{e(row["source_url"])}">{e(row["measure"])} · {e(row["title"])}</a></li>' for row in listings) + '</ul></details>'
    member_links = f'<a href="{e(member["url"])}">Official member page ↗</a>'
    for kind in ('facebook', 'campaign'):
        link = member.get('public_links', {}).get(kind)
        if link:
            member_links += f'<a href="{e(link["url"])}">{e(link["label"])} ↗</a>'
    link_note = member.get('public_links', {}).get('note', '')
    member_links = '<nav class="member-public-links" aria-label="' + e(member['name']) + ' websites">' + member_links + (f'<small>{e(link_note)}</small>' if link_note else '') + '</nav>'
    recent_votes = sum(item['kind'] == 'vote' and item['date'] >= cutoff for item in member['events'])
    return f'''<article class="member-card" id="member-{e(member['id'])}" data-member="{e(member['id'])}"><header class="member-head"><div><p class="eyebrow">{e(member['office'])}</p><h2>{e(member['name'])}</h2></div>{member_links}</header><p class="source-line">Activity source snapshot: {e(member['activity_source_checked_at'][:10])} · Latest available vote: {e(member.get('latest_vote_date') or 'not loaded')} · {recent_votes} recorded votes in recent window</p><div class="member-columns"><section><h3>Recent sponsorship &amp; bill activity</h3><ul class="activity-list">{body}</ul>{listing_html}<h3>Latest recorded votes</h3><p class="minor">Choice applies to the motion shown. Floor and committee votes are distinct; older rows are labeled.</p><ul class="activity-list">{vote_body}</ul></section><section class="committee-column"><h3>Committee meetings · next month</h3><p class="minor">{e(snapshot['as_of'])} through {e(snapshot['calendar_end'])} · times shown in Central</p><ul class="meeting-list">{meetings}</ul><details class="committee-links" open><summary>Committee websites &amp; schedules ({len(member.get('committees', []))})</summary><ul>{committees}</ul></details><p class="minor">{e(snapshot['attendance_note'])}</p><p class="slip-note">{'Illinois witness slips appear only with a verified open submission form; historical results links are not submission forms.' if member['jurisdiction']=='IL' else 'Congress has no general Illinois-style witness-slip system. See each committee’s participation guidance.'}</p></section></div><footer class="member-foot">{e(member['activity_coverage'])}{f' {quiet} ceremonial entries remain in the public snapshot.' if quiet else ''}</footer></article>'''


def render(root):
    snapshot = json.loads((root / 'data/dashboard.json').read_text(encoding='utf-8'))
    if snapshot['schema_version'] != 1 or len(snapshot['members']) != 5:
        raise ValueError('Incomplete member dashboard schema')
    links = ''.join(f'<a href="#member-{e(m["id"])}">{e(m["name"])}</a>' for m in snapshot['members'])
    substitutions = {'AS_OF': e(snapshot['as_of']), 'RECENT_START': e(snapshot['recent_start']),
        'CALENDAR_END': e(snapshot['calendar_end']), 'MEMBER_LINKS': links,
        'MEMBERS': ''.join(member_card(m, snapshot) for m in snapshot['members']),
        'SOURCE_COUNT': str(len(snapshot['calendar_sources'])), 'ERROR_COUNT': str(len(snapshot['errors']))}
    template = (root / 'web/index.html').read_text(encoding='utf-8')
    for key, value in substitutions.items():
        template = template.replace('{{' + key + '}}', value)
    return template, snapshot
