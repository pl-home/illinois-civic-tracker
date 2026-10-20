"""Static shared-change views; pure publication, never a collector.

Atom envelope / source-log timestamps / write-if-changed adapted from
Hawaii-Appleseed/Tracker, tracker/legislative/feeds.py (_feed_xml and
_write_if_changed), reviewed revision b244e82. See THIRD_PARTY_NOTICES.md and
docs/provenance/stage-a.json. IDs and validation are our own stricter contract.
"""
from html import escape
from xml.sax.saxutils import escape as xml_escape, quoteattr
from .changes import empty, packed, public_events, read

BASE = 'https://pl-home.github.io/illinois-civic-tracker/'
LIMIT = 20
MAX_JSON_BYTES = 32_000
MAX_VIEW_BYTES = 90_000


def payload(root):
    ledger = read(root / 'data/change-ledger.json', empty())
    candidates = public_events(ledger, LIMIT)
    baseline = min((s['baseline_at'] for s in ledger['scopes'].values()), default=None)
    rows = []; omitted = 0
    for event in candidates:
        # Prior values remain permanent in the repository; the browser slice
        # carries revision links, not another copy of every prior fact body.
        event = {k: v for k, v in event.items() if k != 'previous_fact'}
        proposed = rows + [event]
        preview = {'events': proposed, 'baseline_at': baseline, 'updated_at': event['observed_at']}
        view_bytes = len((packed(preview) + atom(preview) + render(preview, {})).encode())
        if len(packed(proposed).encode()) > MAX_JSON_BYTES or view_bytes > MAX_VIEW_BYTES:
            omitted += 1
        else:
            rows.append(event)
    return {'schema_version': 1, 'policy': ledger['policy'], 'baseline_at': baseline,
            'updated_at': max((r['observed_at'] for r in rows), default=baseline),
            'selection': 'latest accepted revision per event; at most 20 and 32 KB of entries; historical discoveries excluded',
            'omitted_for_size': omitted,
            'events': rows}


def atom(data):
    # Feed timestamps come from the durable log, not build time (Hawaii pattern).
    updated = data['updated_at'] or '1970-01-01T00:00:00+00:00'
    entries = []
    for row in data['events']:
        fact = row['fact']
        title = f'{fact["kind"]}: {fact["title"]}'
        content = (fact['detail'] + '\nSource date: ' + (fact['occurred_at'] or 'unknown')
                   + '\n' + row['inclusion_reason'])
        entries.append(f'''  <entry>
    <id>urn:illinois-civic-tracker:{row['id']}</id>
    <title>{xml_escape(title)}</title>
    <updated>{xml_escape(row['observed_at'])}</updated>
    <link rel="alternate" href={quoteattr(fact['evidence']['url'])}/>
    <summary>{xml_escape(content)}</summary>
  </entry>''')
    return f'''<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>{BASE}changes.atom</id>
  <title>Illinois civic tracker · accepted changes</title>
  <author><name>Illinois civic tracker</name></author>
  <updated>{xml_escape(updated)}</updated>
  <link rel="self" href="{BASE}changes.atom"/>
  <link rel="alternate" href="{BASE}#changes"/>
{chr(10).join(entries)}
</feed>
'''


def write_if_changed(path, content):
    # Adapted from Hawaii's byte comparison; avoids newline normalization churn.
    data = content.encode('utf-8')
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def render(data, quality):
    e = lambda value: escape(str(value), quote=True)
    rows = []
    for event in data['events'][:10]:
        f = event['fact']
        label = ' · '.join(f['members'])
        rows.append(f'<li id="{e(event["id"])}"><p class="minor">{e(label)} · {e(f["kind"])} · Source date: {e(f["occurred_at"] or "unknown")}</p>'
            f'<strong><a href="{e(f["evidence"]["url"])}">{e(f["title"])} ↗</a></strong><p>{e(f["detail"])}</p>'
            f'<p class="minor">{e(event["inclusion_reason"])} · first observed {e(event["first_observed_at"][:10])}'
            f' · revision {event["revision"]}</p></li>')
    baseline = data['baseline_at'][:10] if data['baseline_at'] else 'not established'
    body = ''.join(rows) or f'<li>No accepted new changes since the baseline ({e(baseline)}). The member sections below retain historical context. Check source coverage; this does not establish inactivity.</li>'
    withheld = quality.get('withheld_scopes', 0)
    status = quality.get('status', 'not checked')
    return f'''<section id="changes" class="dashboard-coverage" aria-label="Shared change feed"><h2>Recent changes</h2>
<p>Source-dated activity and traceable corrections after a quiet baseline. Existing history is not a new alert. Up to ten latest accepted changes are shown here. {data.get('omitted_for_size', 0)} oversized entries omitted from the browser slice; full revisions remain in the repository.</p>
<p><a href="changes.atom">Subscribe with Atom ↗</a> · <a href="changes.json">Compact change feed (JSON) ↗</a> · <a href="https://github.com/pl-home/illinois-civic-tracker/blob/main/docs/CHANGE_FEED.md">Coverage &amp; validation ↗</a></p>
<details><summary>Change-feed quality · {e(status)} · {withheld} withheld source scopes</summary><p>{quality.get('accepted_facts', 0)} accepted compact facts · {quality.get('event_revisions', 0)} preserved event revisions. Failed or invalid observations retain last-good facts and completion cursors. Source-adapter checks do not independently verify publisher claims. This gate covers the new feed; older member snapshot sections retain their existing validation.</p><p>PDF collection remains deferred. Bounded vote rechecks do not establish complete historical correction coverage. Calendar absence never establishes cancellation. Feed build and collection make no model calls.</p></details>
<ul class="activity-list">{body}</ul></section>'''


def build(root, output):
    data = payload(root)
    write_if_changed(output / 'changes.json', packed(data) + '\n')
    write_if_changed(output / 'changes.atom', atom(data))
