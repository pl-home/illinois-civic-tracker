"""Bounded public party-page observations; deterministic, no model or PDF calls.

Reviewed allowlist and extraction principles ported from the owner's earlier
watcher. A compact semantic projection replaces its raw snapshot archive. An
observation is a publisher's page edit, never proof that an event occurred.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import time
import unicodedata
from urllib.parse import urlsplit, urlencode
from urllib.request import Request, build_opener
from urllib.error import HTTPError
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from .changes import digest, packed, public_url, read, timestamp
from .http import NoRedirect, source_error
from .privacy import EMAIL, CREDENTIAL, violations

UA = 'IllinoisCivicTracker/0.0.1 (+https://github.com/pl-home/illinois-civic-tracker)'
CATEGORIES = {'leadership-contact', 'event-meeting', 'candidate-endorsement', 'position-statement', 'image-review', 'unclassified'}
PATTERNS = {
    'leadership-contact': r'\b(chair|officers?|treasurer|secretary|contact|phone|office hours|precinct committee)\b',
    'event-meeting': r'\b(meeting|events?|picnic|fundraiser|oktoberfest|postponed|cancell?ed|rescheduled)\b',
    'candidate-endorsement': r'\b(candidates?|endorse\w*|nominees?)\b',
    'position-statement': r'\b(our position|mission statement|platform|we (?:support|oppose|believe))\b',
}
PHONE = re.compile(r'(?<!\d)(?:\+1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)')


def clean(value):
    value = unicodedata.normalize('NFKC', value)
    value = EMAIL.sub('[contact redacted]', value)
    value = PHONE.sub('[contact redacted]', value)
    value = CREDENTIAL.sub('[redacted]', value)
    return ' '.join(value.split())


def parse_page(raw, page, host):
    soup = BeautifulSoup(raw, 'html.parser')
    root = soup.select_one('.elementor-widget-theme-post-content,.et-l--body,.entry-content,main')
    if root is None:
        raise ValueError('party-content-structure')
    body_text = soup.get_text(' ', strip=True)
    contacts = sorted(set([a.get('href', '') for a in soup.select('a[href^="mailto:"],a[href^="tel:"]')]
                          + EMAIL.findall(body_text) + PHONE.findall(body_text)))
    # Social widgets have relative timestamps, view/share counters and content
    # fetched elsewhere. They are outside this first-party HTML coverage.
    for node in root.select('script,style,nav,header,footer,aside,form,iframe,noscript,svg,#cff,.cff-wrapper,.sharedaddy,.share,.elementor-location-footer'):
        node.decompose()
    lines = []
    for node in root.select('h1,h2,h3,h4,p,li,tr,address'):
        if node.find_parent(['p', 'li', 'tr']): continue
        text = clean(node.get_text(' | ' if node.name == 'tr' else ' ', strip=True))
        if text and text not in lines: lines.append(text)
    if sum(map(len, lines)) < 20:
        lines = [clean(root.get_text(' ', strip=True))]
    if len(lines) > 220 or len(packed(lines).encode()) > 18000:
        raise ValueError('party-projection-bound')
    if sum(map(len, lines)) < 10: raise ValueError('party-content-structure')
    links = set()
    for a in root.select('a[href]'):
        url = a['href']
        from urllib.parse import urljoin
        url = urljoin('https://' + host + page['path'], url)
        p = urlsplit(url)
        if p.scheme == 'https' and p.netloc == host and not p.query and not p.fragment:
            try: public_url(url)
            except ValueError: continue
            if not violations(url): links.add(url)
    if len(links) > 120: raise ValueError('party-projection-bound')
    media = []
    for img in root.select('img[src]'):
        url = img.get('src', '')
        if urlsplit(url).netloc == host and not violations(url):
            try: public_url(url)
            except ValueError: continue
            media.append(url)
    if len(media) > 50: raise ValueError('party-projection-bound')
    result = {'lines': lines, 'links': sorted(links), 'media': sorted(set(media)), 'contacts_hash': digest(contacts)}
    if violations(packed(result)): raise ValueError('party-sensitive-content')
    return result


def classification(old, new, page):
    """Use the changed spans, never unchanged navigation to explain a match."""
    before = old['projection']['lines']; after = new['projection']['lines']
    changed = []
    for op, a, b, c, d in SequenceMatcher(a=before, b=after, autojunk=False).get_opcodes():
        if op != 'equal': changed.extend(before[a:b] + after[c:d])
    text = ' '.join(changed)
    categories = list(page.get('categories', [])) if changed else []
    reasons = ['reviewed page purpose: ' + cat for cat in categories]
    for cat, pattern in PATTERNS.items():
        match = re.search(pattern, text, re.I)
        if match and cat not in categories:
            categories.append(cat); reasons.append('changed-span phrase: ' + match[0].casefold())
    if old['projection'].get('contacts_hash') != new['projection'].get('contacts_hash'):
        if 'leadership-contact' not in categories: categories.append('leadership-contact')
        reasons.append('public contact target fingerprint changed; address values withheld')
    if old['projection'].get('media') != new['projection'].get('media'):
        categories.append('image-review'); reasons.append('first-party image reference changed; human visual review required')
    if not categories:
        categories = ['unclassified']; reasons = ['content/link change without a reviewed category match; review required']
    return sorted(categories), reasons, changed


def diff_excerpts(old, new):
    """Center bounded before/after excerpts on an edit, not the page prefix.

    Multiple edits may exceed this preview. Fingerprints and current projections
    are retained, but this deliberately is not a full historical text archive.
    """
    before = clean(' '.join(old['projection']['lines']))
    after = clean(' '.join(new['projection']['lines']))
    prefix = 0
    for a, b in zip(before, after):
        if a != b: break
        prefix += 1
    start = max(0, prefix - 70)
    def excerpt(value):
        end = min(len(value), start + 350)
        return ('…' if start else '') + value[start:end] + ('…' if end < len(value) else '')
    return excerpt(before), excerpt(after)


def approved(url, host):
    public_url(url)
    p = urlsplit(url)
    if p.netloc != host or p.fragment or p.path.startswith(('/wp-admin', '/wp-login')):
        raise ValueError('party-unapproved-url')


def source_bound(fact):
    """Bind entity, exact configured page/asset URL and publisher label."""
    config = read(Path(__file__).resolve().parents[2]/'config/parties.json')
    for org in config['organizations']:
        urls = {'https://' + org['host'] + p['path'] for p in org['pages']} | set(org.get('assets', []))
        if fact.get('entities') == [org['id']]:
            return fact['evidence']['url'] in urls and fact.get('publisher') == org['label']
    return False


def fetch(url, limit):
    with build_opener(NoRedirect()).open(Request(url, headers={'User-Agent': UA}), timeout=25) as response:
        raw = response.read(limit + 1)
        if len(raw) > limit: raise ValueError('party-response-bound')
        return raw, response.headers.get_content_type()


def write(root, name, value, limit):
    path = root / 'data' / name; raw = (packed(value) + '\n').encode()
    if len(raw) > limit: raise ValueError('party-state-bound')
    other = sum(p.stat().st_size for p in (root / 'data').glob('*.json') if p != path)
    if other + len(raw) > read(root / 'config/daily.json')['max_data_bytes']:
        raise ValueError('public-data-size-budget-exceeded')
    temporary = path.with_suffix('.json.tmp'); temporary.write_bytes(raw); temporary.replace(path)


def collect(root, now, get=fetch):
    config = read(root / 'config/parties.json')
    previous = read(root / 'data/party-state.json', {'pages': {}})
    accepted = read(root/'data/change-ledger.json', {'facts': {}})['facts']
    state = {'schema_version': 1, 'checked_at': now, 'pages': {}, 'model_calls': 0}
    if len(config['organizations']) != 2 or sum(len(o['pages']) + len(o.get('assets', [])) for o in config['organizations']) > 12:
        raise ValueError('party-source-count-bound')
    if {org['id']: org['host'] for org in config['organizations']} != {'lee-democrats': 'leecodemocrats.com', 'lee-gop': 'leecountyilgop.org'}:
        raise ValueError('party-unapproved-url')
    for org in config['organizations']:
        robot = None; robot_error = None
        try:
            raw, _ = get('https://' + org['host'] + '/robots.txt', 64000)
            robot = RobotFileParser(); robot.parse(raw.decode('utf-8').splitlines())
        except Exception as ex: robot_error = source_error(ex)
        sources = [dict(p, url='https://' + org['host'] + p['path']) for p in org['pages']]
        sources += [{'url': url, 'label': 'Watched poster', 'asset': True} for url in org.get('assets', [])]
        for page in sources:
            url = page['url']; old = previous.get('pages', {}).get(url, {})
            receipt = {**deepcopy(old), 'url': url, 'entity': org['id'], 'publisher': org['label'],
                       'label': page['label'], 'checked_at': now, 'status': 'failed'}
            prefix = 'party:' + digest(url)[:24] + '|change:'
            pending = [c for c in old.get('pending_changes', []) if prefix + c['observed_at'] not in accepted]
            try:
                approved(url, org['host'])
                if robot_error: raise ValueError('party-robots-unavailable')
                if not robot.can_fetch(UA, url): raise ValueError('party-robots-disallow')
                delay = robot.crawl_delay(UA) or robot.crawl_delay('*') or 0
                if delay > 10: raise ValueError('party-crawl-delay-review')
                if get is fetch: time.sleep(max(1, delay))
                raw, content_type = get(url, 3000000 if page.get('asset') else config['max_source_bytes'])
                raw_hash = sha256(raw).hexdigest()
                if page.get('asset'):
                    if content_type != 'image/png' or not raw.startswith(b'\x89PNG\r\n\x1a\n'):
                        raise ValueError('party-asset-format')
                    projection = {'lines': ['Image bytes; content not extracted.'], 'sha256': raw_hash}
                else:
                    if content_type not in {'text/html', 'application/xhtml+xml'}: raise ValueError('party-content-type')
                    projection = parse_page(raw, page, org['host'])
                receipt.update(status='ok', raw_sha256=raw_hash, projection=projection,
                               parser=config['parser_version'], last_good_at=now, bytes=len(raw))
                receipt.pop('error', None)
                baseline = not old.get('projection') or old.get('parser') != config['parser_version']
                if pending and old.get('parser') != config['parser_version']:
                    raise ValueError('party-parser-pending-review')
                receipt['observation'] = 'baseline' if baseline else 'unchanged'
                if not baseline and digest(old['projection']) != digest(projection):
                    old_len = sum(map(len, old['projection']['lines'])); new_len = sum(map(len, projection['lines']))
                    if not page.get('asset') and new_len < old_len * .4:
                        raise ValueError('party-content-shrink-review')
                    receipt['observation'] = 'changed'
                    if page.get('asset'):
                        cats, reasons, changed = ['image-review'], ['watched poster byte fingerprint changed; human visual review required'], []
                    else: cats, reasons, changed = classification(old, receipt, page)
                    # A bounded evidence diff is retained in the immutable common
                    # ledger. No full page/article/image archive is committed.
                    before_excerpt, after_excerpt = diff_excerpts(old, receipt)
                    receipt['change'] = {'categories': cats, 'reasons': reasons,
                        'before_sha256': old['raw_sha256'], 'after_sha256': raw_hash,
                        'before_excerpt': before_excerpt, 'after_excerpt': after_excerpt,
                        'observed_at': now, 'source_date': None,
                        'previous_good_at': old['last_good_at'], 'after_gap': old.get('status') != 'ok'}
                    pending.append(receipt['change'])
                    if len(pending) > 8: raise ValueError('party-pending-change-bound')
                if baseline: receipt.pop('change', None)
                receipt['pending_changes'] = pending
            except Exception as ex:
                receipt = {**deepcopy(old), 'url': url, 'entity': org['id'], 'publisher': org['label'],
                           'label': page['label'], 'checked_at': now, 'status': 'failed',
                           'error': str(ex) if isinstance(ex, ValueError) and str(ex).startswith('party-') else source_error(ex)}
            state['pages'][url] = receipt
    state['status'] = 'partial' if any(p['status'] != 'ok' for p in state['pages'].values()) else 'ok'
    write(root, 'party-state.json', state, config['max_state_bytes'])
    return state


def observations(root):
    state = read(root / 'data/party-state.json', {'pages': {}})
    for url, page in state['pages'].items():
        changes = list(page.get('pending_changes', [])); facts = []
        if page.get('change') and not any(c['observed_at'] == page['change']['observed_at'] for c in changes):
            changes.append(page['change'])
        for change in changes:
            facts.append({'key': 'change:' + change['observed_at'], 'kind': 'party-change',
                'jurisdiction': 'LOCAL', 'session': None, 'members': [], 'entities': [page['entity']],
                'occurred_at': None, 'date_precision': 'unknown', 'title': page['publisher'] + ' · ' + page['label'],
                'detail': 'Publisher page edited; action/event date unknown. ' + '; '.join(change['reasons']),
                'evidence': {'url': url, 'retrieved_at': change['observed_at'], 'binding': 'party-page', 'sha256': change['after_sha256']},
                'publisher': page['publisher'], **change})
        # If the bounded outbox is full, its already captured good changes can
        # still be reconciled at their last-good cursor before collection retries.
        checked = page.get('last_good_at') if page.get('error') == 'party-pending-change-bound' else page['checked_at']
        age = (datetime.now(timezone.utc) - timestamp(checked)).total_seconds()
        yield {'id': 'party:' + digest(url)[:24], 'family': 'party-pages', 'adapter': page.get('parser', 1),
            'jurisdiction': 'LOCAL', 'session': None, 'checked_at': checked,
            'complete': (page['status'] == 'ok' or page.get('error') == 'party-pending-change-bound') and 0 <= age <= 48 * 3600, 'facts': facts}


def panel(root):
    state = read(root / 'data/party-state.json', {'pages': {}})
    config = read(root / 'config/parties.json'); rows = []
    e = lambda value: escape(str(value), quote=True)
    now = datetime.now(timezone.utc)
    for org in config['organizations']:
        pages = [p for p in state['pages'].values() if p['entity'] == org['id']]
        links = []
        for page in pages:
            stale = (now - timestamp(page['checked_at'])).total_seconds() > config['stale_hours'] * 3600
            status = 'stale' if stale else page['status']
            links.append(f'<li><a href="{e(page["url"])}">{e(page["label"])} ↗</a> · {e(status)} · {e(page.get("observation", "not baselined"))}'
                         f' · checked {e(page["checked_at"])}' + (f' · {e(page["error"])}' if page.get('error') else '') + '</li>')
        rows.append(f'<article><h3>{e(org["label"])}</h3><details><summary>Pages &amp; coverage ({len(pages)})</summary><ul>{"".join(links)}</ul></details></article>')
    from .changes import empty, validated_events
    events = [ev for ev in validated_events(read(root/'data/change-ledger.json', empty())) if ev['fact']['kind'] == 'party-change']
    latest = {ev['id']: ev for ev in events}
    visible = []; hidden = []; hidden_total = sum(not ev['eligible'] for ev in latest.values())
    for ev in sorted(latest.values(), key=lambda v: v['observed_at'], reverse=True):
        f = ev['fact']
        target = visible if ev['eligible'] else hidden
        if len(target) >= 6: continue
        line = f'<li><a href="{e(f["evidence"]["url"])}">{e(f["title"])} ↗</a> · observed {e(ev["observed_at"])}<p>{e(f["detail"])}</p><details><summary>Evidence &amp; exact inclusion reasons</summary><p>Before: {e(f["before_excerpt"])}<br>Changed spans: {e(f["after_excerpt"])}</p><p>Source date unknown · baseline/gap start {e(f["previous_good_at"])} · after collection gap: {e(f["after_gap"])}</p><p>Before SHA-256: {e(f["before_sha256"])}<br>After SHA-256: {e(f["after_sha256"])}</p></details></li>'
        target.append(line)
    mentions = read(root/'data/mentions-state.json', {})
    mention_rows = []
    for subject, row in mentions.get('sources', {}).items():
        stale = (now - timestamp(row['checked_at'])).total_seconds() > config['stale_hours'] * 3600
        status = 'stale' if stale else row['status']
        mention_rows.append(f'<li><a href="{e(row["url"])}">{e(subject)} search feed ↗</a>: {e(status)} · {row.get("matched", 0)} explicit title matches of {row.get("checked", 0)} candidates · checked {e(row.get("checked_at"))}'
                            + (f' · {e(row["error"])}' if row.get('error') else '') + '</li>')
    mention_rows = ''.join(mention_rows)
    return '<section id="county-parties" class="dashboard-coverage"><h2>Lee County party websites</h2><p>Hosted checks run with the daily 01:00 Central refresh. Organization-published material is attributed; page edits do not verify claims or establish event dates. No model calls.</p>' + ''.join(rows) + '<h3>Attributed website changes</h3><ul>' + (''.join(visible) or '<li>No relevant page changes accepted since each page’s quiet baseline. Check source health; this does not establish inactivity.</li>') + '</ul><details><summary>Show changes held for review (' + str(hidden_total) + ')</summary><p>Up to six latest review entries shown. Full retained entries: <a href="https://github.com/pl-home/illinois-civic-tracker/blob/main/data/change-ledger.json">shared change ledger ↗</a>. Review is unresolved; no automatic clearance is inferred.</p><ul>' + ''.join(hidden) + '</ul></details><details><summary>Method &amp; limits · Capitol Fax mention coverage</summary><p>Eleven reviewed HTML pages and one first-party poster; no recursive crawl, Facebook, OCR, full articles or raw image archives. New pages and parser upgrades establish quiet baselines; cosmetic whitespace and social widgets are ignored. Large content shrink is withheld. Poster changes require human visual review; no content is inferred. Public contact values are redacted, with a fingerprint for change detection. First-party member-name-filtered feeds above remain separate.</p><p>Capitol Fax search feeds: up to twelve public headline candidates per subject, explicit name/title match only. No matching title does not rule out a body-text mention. Protected posts are excluded; these candidates are not automatically independent newsroom reports.</p><ul>' + mention_rows + '</ul></details></section>'


def collect_mentions(root, now, get=fetch):
    config = read(root/'config/parties.json'); previous = read(root/'data/mentions-state.json', {'sources': {}})
    state = {'schema_version': 1, 'checked_at': now, 'sources': {}, 'model_calls': 0}
    if len(config['mention_terms']) > 6: raise ValueError('party-source-count-bound')
    robot = None
    try:
        raw, _ = get('https://capitolfax.com/robots.txt', 64000)
        robot = RobotFileParser(); robot.parse(raw.decode('utf-8').splitlines())
    except HTTPError as ex:
        # A missing robots file is not a collection outage or a robots denial.
        # Do not apply this exception to 403/429/5xx or a network/TLS failure.
        if ex.code == 404: robot = RobotFileParser(); robot.parse([])
    except Exception: pass
    for subject, terms in config['mention_terms'].items():
        # WordPress ANDs search terms rather than interpreting an OR expression.
        # A reviewed surname query covers aliases within one candidate budget;
        # acceptance below still requires a configured full headline name.
        query = config.get('mention_queries', {}).get(subject, terms[0])
        url = 'https://capitolfax.com/?' + urlencode({'s': query, 'feed': 'rss2'})
        row = {'url': url, 'checked_at': now, 'status': 'failed'}
        try:
            if robot is None: raise ValueError('party-robots-unavailable')
            if not robot.can_fetch(UA, url): raise ValueError('party-robots-disallow')
            delay = robot.crawl_delay(UA) or robot.crawl_delay('*') or 0
            if delay > 10: raise ValueError('party-crawl-delay-review')
            if get is fetch: time.sleep(max(1, delay))
            raw, _ = get(url, 250000); tree = ET.fromstring(raw)
            if tree.find('channel') is None: raise ValueError('party-content-structure')
            items = tree.findall('./channel/item')[:12]; matched = []
            for item in items:
                title = clean(item.findtext('title') or '')
                link = item.findtext('link') or ''
                if title.casefold().startswith('protected:'): continue
                if urlsplit(link).netloc != 'capitolfax.com': continue
                public_url(link)
                if not any(re.search(r'\b' + re.escape(term) + r'\b', title, re.I) for term in terms): continue
                date = parsedate_to_datetime(item.findtext('pubDate') or '')
                if date.tzinfo is None or date > timestamp(now): continue
                matched.append({'title': title[:240], 'url': link, 'published_at': date.isoformat(), 'reason': 'explicit headline name match'})
            row.update(status='ok', checked=len(items), matched=len(matched), items=matched, last_good_at=now)
        except Exception as ex:
            row.update(error=str(ex) if isinstance(ex, ValueError) and str(ex).startswith('party-') else source_error(ex), items=previous['sources'].get(subject, {}).get('items', []),
                       last_good_at=previous['sources'].get(subject, {}).get('last_good_at'))
        state['sources'][subject] = row
    write(root, 'mentions-state.json', state, 50000)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('command', choices=['collect'])
    parser.parse_args(); root = Path.cwd(); now = datetime.now(timezone.utc).isoformat()
    state = collect(root, now); mentions = collect_mentions(root, now)
    print(json.dumps({'party_status': state['status'], 'pages': len(state['pages']),
                      'mentions': {k: v['status'] for k, v in mentions['sources'].items()}, 'model_calls': 0}))


if __name__ == '__main__': main()
