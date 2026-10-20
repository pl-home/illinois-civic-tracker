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


def meeting_row(meeting, reference=None):
    from .hearing_view import meeting_row as row
    return row(meeting, reference)



def media_section(member):
    health = member.get('media_health', {})
    reports = member.get('media_reports', [])
    rows = []
    for report in reports:
        # Never expose a script/data URL even if a stored snapshot is malformed.
        from urllib.parse import urlsplit
        link = urlsplit(report.get('url', ''))
        if link.scheme != 'https' or link.username or link.password:
            continue
        route = ' · via Google News' if report.get('link_route') == 'Google News' else ''
        rows.append(f'<li class="media-row"><time datetime="{e(report["published_at"])}">{e(report["published_at"][:10])}</time><strong><a href="{e(report["url"])}">{e(report["title"])} ↗</a></strong><p class="minor">{e(report["publisher"])}{route}</p></li>')
    body = ''.join(rows) or '<li class="empty-source">No eligible reports found in the last 90 days from the selected newsrooms. Coverage is incomplete.</li>'
    warning = ''
    if health.get('source_status') != 'ok' or health.get('inference_status') != 'complete':
        warning = '<p class="warning">News refresh or relevance screening is incomplete; previously screened reports may be retained.</p>'
    checked = health.get('checked_at') or 'not yet checked'
    search = member.get('media_search', {})
    method = ''
    if search:
        method = f'<details class="news-method"><summary>How we find news about {e(member["name"])}</summary><p>Exact Google News query: <code>{e(search["query"])}</code></p><p><a href="{e(search["search_url"])}">Open this news search ↗</a> · <a href="{e(search["feed_url"])}">RSS feed used by the tracker ↗</a></p><ol><li>Read up to 150 feed entries; keep dates within 90 days and publishers in the <a href="{e(search["publisher_policy_url"])}">reviewed newsroom list ↗</a>.</li><li>Require a member-name anchor in the headline or snippet; remove duplicate headlines and explicit opinion/editorial titles, then sort by publication date and retain up to 30 candidates.</li><li>Qwen screens headline relevance using supplied IDs only. Cached decisions are reused; up to four unseen candidates per member are considered per run within the shared daily budget.</li><li>Display the three newest accepted results found. This is indexed-feed coverage, not a search of every article or its full text.</li></ol><p class="minor">{e(search["candidate_count"])} eligible feed candidates at the latest check. Sections use the publishing source: a newsroom may republish a release, and its original authorship is not verified from feed metadata.</p></details>'
    return f'<section class="member-media" aria-label="Recent media reports about {e(member["name"])}"><h3>Recent media reports</h3><p class="minor">Up to three latest reports found · last 90 days · selected major and Illinois newsrooms. AI screens headline relevance; article content is not independently verified.</p>{warning}<ul class="media-list">{body}</ul><p class="minor">News checked: {e(checked)}. Links may route through Google News; publisher access terms apply.</p>{method}</section>'



def communications_section(member):
    kinds = {'office':'Member office', 'campaign':'Campaign releases', 'party':'Party / caucus'}
    parts=[]
    for kind,label in kinds.items():
        rows=[]
        for item in member.get('communications', []):
            if item['kind']!=kind:continue
            from urllib.parse import urlsplit
            link=urlsplit(item.get('url',''))
            if link.scheme!='https' or link.username or link.password:continue
            retained='<p class="warning">Retained from an earlier check; this source could not be fully refreshed.</p>' if item.get('retained_after_failure') else ''
            rows.append(f'<li class="communication-row"><time datetime="{e(item["published_at"])}">{e(item["published_at"][:10])}</time><strong><a href="{e(item["url"])}">{e(item["title"])} ↗</a></strong><p class="minor">{e(label)} · {e(item["publisher"])}</p>{retained}</li>')
        body=''.join(rows) or '<li class="empty-source">No dated matching items collected in the last 90 days. See source coverage below.</li>'
        parts.append(f'<div class="communication-group"><h4>{e(label)}</h4><ul class="communication-list">{body}</ul></div>')
    coverage=[]
    for source in member.get('communication_sources', []):
        latest=f' · latest source date {e(source["latest_source_date"])}' if source.get('latest_source_date') else ''
        note=f'<p class="minor">{e(source["note"])}</p>' if source.get('note') else ''
        coverage.append(f'<li><a href="{e(source["url"])}">{e(source["publisher"])} ↗</a> · {e(kinds[source["kind"]])} · {e(source["status"])}{latest}{note}</li>')
    checked=member.get('communications_checked_at') or 'not yet checked'
    failed=sum(source['status'] in ('failed','partial') for source in member.get('communication_sources', []))
    warning=f'<p class="warning">{failed} source check(s) are incomplete; earlier dated posts may be retained. See source coverage.</p>' if failed else ''
    return f'<section class="member-communications" aria-label="Direct communications about {e(member["name"])}"><h3>Member, campaign &amp; party communications</h3><p class="minor">Up to three latest items per source type · last 90 days. Published by the identified office, campaign or party; these are first-party statements, not independent news reports. Claims are attributed to their publisher.</p>{warning}{"".join(parts)}<details class="communication-coverage"><summary>Sources &amp; coverage</summary><ul>{"".join(coverage)}</ul><p class="minor">Source status “link-only” means a public link is provided but no dated feed is collected. Only the first listing/feed page is checked. Shared party items require a name match; general party announcements are not assigned to every member. Facebook, private newsletters and signup-only content are not collected. Missing items do not establish inactivity.</p></details><p class="minor">Communications checked: {e(checked)} · collection uses no model calls.</p></section>'


def member_card(member, snapshot, hearing_html=None):
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
    meetings = (hearing_html if hearing_html is not None else ''.join(meeting_row(meeting) for meeting in member['meetings'])) or f'<li class="empty-source">{e(calendar_note)}</li>'
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
    return f'''<article class="member-card" id="member-{e(member['id'])}" data-member="{e(member['id'])}"><header class="member-head"><div><p class="eyebrow">{e(member['office'])}</p><h2><a href="member-{e(member['id'])}.html">{e(member['name'])}</a></h2></div>{member_links}</header><p class="source-line">Activity source snapshot: {e(member['activity_source_checked_at'][:10])} · Latest available vote: {e(member.get('latest_vote_date') or 'not loaded')} · {recent_votes} recorded votes in recent window</p><div class="member-columns"><section><h3>Recent sponsorship &amp; bill activity</h3><ul class="activity-list">{body}</ul><p><a class="member-history-link" href="member-{e(member['id'])}.html">More sponsorship &amp; bill activity →</a></p>{listing_html}<h3>Latest recorded votes</h3><p class="minor">Choice applies to the motion shown. Floor and committee votes are distinct; older rows are labeled.</p><ul class="activity-list">{vote_body}</ul></section><section class="committee-column"><h3>Committee meetings · next month</h3><p class="minor">{e(snapshot['as_of'])} through {e(snapshot['calendar_end'])} · times shown in Central</p><ul class="meeting-list">{meetings}</ul><details class="committee-links" open><summary>Committee websites &amp; schedules ({len(member.get('committees', []))})</summary><ul>{committees}</ul></details><p class="minor">{e(snapshot['attendance_note'])}</p><p class="slip-note">{'Illinois witness slips appear only with a verified open submission form; historical results links are not submission forms.' if member['jurisdiction']=='IL' else 'Congress has no general Illinois-style witness-slip system. See each committee’s participation guidance.'}</p>{media_section(member)}{communications_section(member)}</section></div><footer class="member-foot">{e(member['activity_coverage'])}{f' {quiet} ceremonial entries remain in the public snapshot.' if quiet else ''}</footer></article>'''



def usage_panel(snapshot):
    from decimal import Decimal
    report=snapshot.get('inference_usage')
    if not report:
        return '<section class="usage-panel"><h2>AI usage &amp; budget</h2><p>Usage has not been calculated for this snapshot.</p></section>'
    cards=[]
    for key,label in (('week','This week'),('day','Today')):
        record=report[key]
        charged=Decimal(record['charged_usd']); held=Decimal(record['reserved_usd'])
        limit=Decimal(record['limit_usd']); used=Decimal(record['liability_usd'])
        amount=f'${charged:.5f}'; percent=f'{Decimal(record["used_percent"]):.1f}'
        pending=f' + ${held:.5f} held for unsettled requests' if held else ''
        cards.append(f'<div class="usage-period"><h3>{e(label)}</h3><p><strong>{e(amount)}</strong> / ${limit:.2f}{e(pending)}</p><meter min="0" max="{e(limit)}" value="{e(min(used,limit))}" aria-label="{e(label)} budget used">{e(percent)}%</meter><p class="minor">{e(percent)}% used including holds · ${Decimal(record["remaining_usd"]):.5f} available</p></div>')
    stamp=datetime.fromisoformat(report['as_of']).astimezone(ZoneInfo(report['timezone']))
    updated=stamp.strftime('%b %d, %Y · %I:%M %p %Z')
    warning='<p class="warning">Some entry dates are unknown; those amounts count conservatively in both current periods.</p>' if report['lifetime']['undated_entries'] else ''
    return f'<section class="usage-panel" aria-label="AI usage and budget"><div class="usage-heading"><h2>AI usage &amp; budget</h2><span>{e(report["week_start"])}–{e(report["week_end"])} · Monday–Sunday · Central</span></div><p class="minor">Recorded tracker inference, including earlier evaluations · calculated {e(updated)} · updated with the daily 01:00 Central refresh.</p><div class="usage-grid">{"".join(cards)}</div>{warning}<details><summary>Usage details</summary><p>Weekly charges: ${e(report["week"]["charged_usd"])}. Unsettled reservations: ${e(report["week"]["reserved_usd"])} across {e(report["week"]["unsettled_requests"])} request(s). Reservations count against the limits until charges are known.</p><p>{e(report["scope"])}</p><p>Lifetime recorded charges: ${e(report["lifetime"]["charged_usd"])} · lifetime ceiling ${Decimal(report["lifetime"]["limit_usd"]):.2f}. Earlier evaluation costs are included. Free source collection and cached decisions add no inference charge.</p><p>Calculated {e(updated)}. Recalculated with the daily 01:00 Central site refresh; this is a dated project ledger report, not live account billing.</p></details></section>'


def render(root):
    snapshot = json.loads((root / 'data/dashboard.json').read_text(encoding='utf-8'))
    if snapshot['schema_version'] != 1 or len(snapshot['members']) != 5:
        raise ValueError('Incomplete member dashboard schema')
    links = ''.join(f'<a href="#member-{e(m["id"])}">{e(m["name"])}</a>' for m in snapshot['members'])
    daily=snapshot.get('daily_refresh')
    health=''
    if daily:
        lines=''.join(f'<li><strong>{e(name)}</strong>: {e(report["status"])} · checked {e(report.get("checked_at"))}</li>' for name,report in daily['sources'].items())
        failures=''.join(f'<li>{e(err.get("source"))}: {e(err.get("error"))}</li>' for report in daily['sources'].values() for err in report.get('errors',[]))
        health=f'<details class="refresh-health" open><summary>Daily refresh · {e(daily["status"])} · starts 01:00 Central</summary><ul>{lines}</ul>'+('<p>Source failures; prior verified records retained:</p><ul>'+failures+'</ul>' if failures else '')+'<p>Illinois committee votes retain historical PDF coverage; daily committee-vote discovery is pending. GitHub may start jobs late; publication follows collection.</p></details>'
    automatic=snapshot.get('automatic_refresh_enabled',False)
    coverage=('Daily source refresh is enabled for 01:00 Central. Source dates and collection health below identify remaining gaps.' if automatic else 'Automatic refresh is not enabled.')
    from .change_feed import payload, render as change_panel
    from .changes import read
    from .hearing_view import sections
    hearing_navigation, hearing_cards = sections(root, snapshot)
    substitutions = {'CHANGE_FEED': change_panel(payload(root), read(root/'data/change-quality-report.json', {})),
        'HEARING_NAVIGATION': hearing_navigation,
        'INFERENCE_USAGE': usage_panel(snapshot), 'REFRESH_HEALTH': health, 'AUTO_REFRESH': coverage, 'AS_OF': e(snapshot['as_of']), 'RECENT_START': e(snapshot['recent_start']),
        'CALENDAR_END': e(snapshot['calendar_end']), 'MEMBER_LINKS': links,
        'MEMBERS': ''.join(member_card(m, snapshot, hearing_cards.get(m['id'], '')) for m in snapshot['members']),
        'SOURCE_COUNT': str(len(snapshot['calendar_sources'])), 'ERROR_COUNT': str(len(snapshot['errors']))}
    template = (root / 'web/index.html').read_text(encoding='utf-8')
    for key, value in substitutions.items():
        template = template.replace('{{' + key + '}}', value)
    return template, snapshot
