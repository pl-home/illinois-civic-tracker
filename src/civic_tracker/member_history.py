"""Static, paginated bill history from accepted facts; no collection or model calls."""
from collections import Counter
from hashlib import sha256
from html import escape
import math

from .changes import MEMBERS, digest, empty, read, semantic, validate_fact
from .rules import ceremonial

PAGE_SIZE = 25
MAX_PAGES = 100  # Per member, per dated/undated section; fail closed on growth.
MAX_HISTORY_BYTES = 3_000_000
KINDS = {'filing', 'sponsor-role', 'bill-action'}


def e(value):
    return escape(str(value or ''), quote=True)


def filename(member, page=1, undated=False):
    if member not in MEMBERS or type(page) is not int or not 1 <= page <= MAX_PAGES:
        raise ValueError('member-history-page-identity')
    return f'member-{member}{"-relationships" if undated else ""}{"-" + str(page) if page > 1 else ""}.html'


def artifact_names():
    return {filename(member, page, undated) for member in MEMBERS
            for page in range(1, MAX_PAGES + 1) for undated in (False, True)}


def accepted_rows(ledger, member, as_of):
    """Recheck the shared fact contract. Quiet baselines belong in history too."""
    rows = []; rejected = 0
    for stored_key, stored in ledger['facts'].items():
        fact = stored.get('fact', {})
        if member not in fact.get('members', []) or fact.get('kind') not in KINDS:
            continue
        scope_id, separator, key = stored_key.partition('|')
        scope = ledger['scopes'].get(scope_id)
        if (not separator or key != fact.get('key') or not scope
                or validate_fact(fact, scope)
                or stored.get('fingerprint') != digest(semantic(fact))
                or (not stored.get('active', True) and fact.get('operation') != 'removed')):
            rejected += 1
            continue
        if fact.get('occurred_at') and fact['occurred_at'][:10] > as_of:
            continue
        rows.append({'fact': fact, 'scope': scope_id, 'id': 'history-' + digest(stored_key)[:20]})
    filings = {r['fact'].get('measure') for r in rows if r['fact']['kind'] == 'filing'}
    # A current sponsor listing adds no join date beyond its already-shown filing.
    rows = [r for r in rows if not (r['fact'].get('role') == 'sponsored'
            and r['fact'].get('operation') == 'listed' and r['fact'].get('measure') in filings)]
    dated = sorted((r for r in rows if r['fact'].get('occurred_at')),
                   key=lambda r: (r['fact']['occurred_at'], r['fact']['key']), reverse=True)
    undated = sorted((r for r in rows if not r['fact'].get('occurred_at')),
                     key=lambda r: (r['fact'].get('measure', ''), r['fact']['key']))
    return dated, undated, rejected


def row_html(row):
    f = row['fact']; when = f.get('occurred_at')
    label = {'filing': 'Introduction / filing', 'sponsor-role': 'Sponsorship',
             'bill-action': 'Related bill update'}[f['kind']]
    date = f'<time datetime="{e(when)}">{e(when[:10])}</time>' if when else '<span>Date unknown</span>'
    measure = f['measure'].split('-', 2)[-1]
    quiet = '<span class="tag quiet">Ceremonial</span>' if ceremonial(f['title']) else ''
    attribution = f.get('attribution') or ('Action on an associated measure; not necessarily an action by this member.'
                    if f['kind'] == 'bill-action' else '')
    note = f'<p class="minor">{e(attribution)}</p>' if attribution else ''
    roles = {'original-filer': 'Original filer', 'chief-co-sponsor': 'Chief co-sponsor',
             'chief-sponsor': 'Chief sponsor', 'co-sponsor': 'Co-sponsor', 'sponsor': 'Sponsor',
             'sponsored': 'Sponsor', 'cosponsored': 'Co-sponsor'}
    operations = {'filed': 'Filed', 'added-or-changed': 'Role added or changed',
                  'removed': 'Removed', 'listed': 'Listed relationship'}
    role = (f'<span class="minor"> · {e(roles[f["role"]])} · {e(operations[f["operation"]])}</span>'
            if f['kind'] == 'sponsor-role' else '')
    return (f'<li class="activity-row" id="{e(row["id"])}"><div class="activity-date">{date}'
            f'<span class="tag">{label}</span>{quiet}</div><div><p class="activity-title">'
            f'<a href="{e(f["evidence"]["url"])}">{e(measure)} · {e(f["title"])} ↗</a></p>'
            f'<p class="activity-detail">{e(f["detail"])}{role}</p>{note}'
            f'<p class="minor">Source checked {e(f["evidence"]["retrieved_at"][:10])}</p></div></li>')


def pagination(member, number, count, undated):
    links = []
    noun = 'listings' if undated else 'actions'
    if number > 1:
        links.append(f'<a rel="prev" href="{filename(member, number-1, undated)}">← {"Previous listings" if undated else "Newer actions"}</a>')
    if number < count:
        links.append(f'<a rel="next" href="{filename(member, number+1, undated)}">{"Next listings" if undated else "Older actions"} →</a>')
    if count > 1:
        links.extend([f'<a href="{filename(member, 1, undated)}">First page</a>',
                      f'<a href="{filename(member, count, undated)}">{"Last listings" if undated else "Oldest available actions"}</a>'])
    return (f'<nav class="history-pagination" aria-label="History pages"><span>Page {number} of {count} · '
            f'{PAGE_SIZE} {noun} per page</span>{"".join(links)}</nav>')


def build_pages(root, snapshot):
    from .dashboard import media_section
    style_version = sha256((root/'web/styles.css').read_bytes()).hexdigest()[:12]
    ledger = read(root/'data/change-ledger.json', empty())
    quality = read(root/'data/change-quality-report.json', {})
    withheld = {s['id'] for s in quality.get('scopes', []) if s['status'] == 'withheld'}
    pages = {}; report = {}
    for member in snapshot['members']:
        ident = member['id']
        dated, undated, rejected = accepted_rows(ledger, ident, snapshot['as_of'])
        counts = Counter(r['fact']['kind'] for r in dated)
        report[ident] = {'dated': len(dated), 'undated': len(undated), 'withheld_records': rejected,
                         'earliest': dated[-1]['fact']['occurred_at'][:10] if dated else None,
                         'latest': dated[0]['fact']['occurred_at'][:10] if dated else None}
        problems = len({r['scope'] for r in dated+undated} & withheld)
        source = 'Illinois' if member['jurisdiction'] == 'IL' else 'Federal'
        session_label = 'Illinois GA104' if member['jurisdiction'] == 'IL' else 'Congress119'
        public_links = f'<a href="{e(member["url"])}">Official member page ↗</a>'
        for kind in ('facebook', 'campaign'):
            link = member.get('public_links', {}).get(kind)
            if link:
                public_links += f' · <a href="{e(link["url"])}">{e(link["label"])} ↗</a>'
        link_note = member.get('public_links', {}).get('note')
        if link_note: public_links += f'<small class="minor"> {e(link_note)}</small>'
        health = snapshot.get('daily_refresh', {}).get('sources', {}).get(source, {})
        warning = ('<p class="warning">Source coverage is incomplete; prior accepted records retain their original source dates. '
                   'Check the homepage collection-health report.</p>'
                   if problems or rejected or health.get('status', 'ok') != 'ok' else '')
        coverage = (f'{len(dated)} dated entries: {counts["filing"]} filing, {counts["sponsor-role"]} sponsorship, '
                    f'{counts["bill-action"]} related bill updates. {len(undated)} undated relationship listings.')
        date_range = (f'Available dated records: {report[ident]["earliest"]}–{report[ident]["latest"]}.'
                      if dated else 'No dated entries are available in the accepted records.')
        news_column = media_section(member, lookback_days=200, as_of=snapshot['as_of'])
        for is_undated, records in ((False, dated), (True, undated)):
            count = max(1, math.ceil(len(records)/PAGE_SIZE))
            if count > MAX_PAGES:
                raise ValueError('member-history-page-budget-exceeded')
            for number in range(1, count+1):
                name = filename(ident, number, is_undated)
                title = 'Undated sponsorship listings' if is_undated else 'Sponsorship & bill activity'
                nav = pagination(ident, number, count, is_undated)
                rows = ''.join(row_html(r) for r in records[(number-1)*PAGE_SIZE:number*PAGE_SIZE])
                if not rows: rows = '<li class="empty-source">No accepted entries in this section. This does not establish inactivity.</li>'
                pages[name] = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer">'
                    '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'self\'; base-uri \'none\'; form-action \'none\'; object-src \'none\'">'
                    f'<title>{e(member["name"])} · {e(title)} · page {number}</title><link rel="stylesheet" href="styles.css?v={style_version}"></head>'
                    '<body class="dashboard member-history"><a class="skip" href="#history">Skip to activity history</a>'
                    '<header class="masthead"><a class="brand" href="./"><span class="brand-mark" aria-hidden="true">IL</span>Illinois civic tracker</a>'
                    f'<nav aria-label="Main"><a href="./#member-{ident}">← Back to homepage</a></nav></header><main>'
                    f'<section class="intro"><div><p class="eyebrow">{e(member["office"])}</p><h1>{e(member["name"])}</h1>'
                    f'<p class="lede">{e(title)}</p><p>{public_links}</p></div></section>'
                    f'<section class="dashboard-coverage"><p><strong>{e(coverage)}</strong></p><p>{e(date_range)} '
                    f'{session_label} only; coverage is incomplete.</p>{warning}'
                    '<details class="history-method"><summary>Coverage &amp; date rules</summary>'
                    '<p>This is collected history, not complete service history. '
                    'Older imports may contain only role actions and the last bill update; missing intermediate actions do not establish inactivity.</p>'
                    '<p>Entries use their legislative dates, not the date imported. Related bill updates are not necessarily personal actions by the member. '
                    'Undated listings do not establish when a cosponsorship began or ended. Current sponsor listings already represented by a filing are not repeated. '
                    'Ceremonial measures are included and marked here.</p>'
                    f'<p>Snapshot: {e(snapshot["as_of"])} · {rejected} invalid stored records withheld.</p></details>'
                    f'<nav class="history-pagination" aria-label="History sections"><a href="{filename(ident)}">Dated bill activity ({len(dated)})</a>'
                    f'<a href="{filename(ident, undated=True)}">Undated listings ({len(undated)})</a></nav></section>'
                    f'<div class="member-history-columns"><section id="history"><h2>{e(title)}</h2>{nav}<ul class="activity-list">{rows}</ul>{nav}</section>'
                    f'<aside class="history-news" aria-label="News coverage for {e(member["name"])}">{news_column}</aside></div>'
                    '</main><footer><span>Official sources linked on each entry · No automatic outreach</span></footer></body></html>')
    size = sum(len(page.encode('utf-8')) for page in pages.values())
    if size > MAX_HISTORY_BYTES:
        raise ValueError('member-history-size-budget-exceeded')
    return pages, {'members': report, 'pages': len(pages), 'artifact_bytes': size}
