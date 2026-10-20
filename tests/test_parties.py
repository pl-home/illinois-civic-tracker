"""Stage C stateful fixtures; synthetic source edits, no live requests/models."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from civic_tracker import parties
from civic_tracker.changes import empty, reconcile, public_events, validate_fact, read
from civic_tracker.relevance import explain
from civic_tracker.privacy import violations
from civic_tracker import error_journal

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime.now(timezone.utc)


def html(text, extra=''):
    return ('<html><nav>Ignore menu</nav><main><h1>County organization</h1><p>' + text + '</p>' + extra + '</main></html>').encode()


class PartyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); (self.root/'data').mkdir(); (self.root/'config').mkdir()
        self.config = read(ROOT/'config/parties.json')
        for org in self.config['organizations']:
            org['pages'] = [org['pages'][0]]; org.pop('assets', None)
        self.config['mention_terms'] = {'lee-county': ['Lee County']}
        self.save_config()
        (self.root/'config/daily.json').write_text('{"max_data_bytes":20000000}')
        self.body = html('Our regular meeting will take place November 2 in the town hall.')
        self.unavailable = False

    def save_config(self):
        (self.root/'config/parties.json').write_text(json.dumps(self.config))

    def get(self, url, limit):
        if self.unavailable: raise TimeoutError()
        if url.endswith('/robots.txt'): return b'User-agent: *\nDisallow: /private/', 'text/plain'
        return self.body, 'text/html'

    def run_collect(self, delta=0):
        return parties.collect(self.root, (NOW+timedelta(minutes=delta)).isoformat(), self.get)

    def scopes(self):
        return list(parties.observations(self.root))

    def test_baseline_cosmetic_replay_and_parser_migration_are_quiet(self):
        first = self.run_collect(-5); ledger, _ = reconcile(empty(), self.scopes(), NOW.isoformat())
        self.assertEqual(first['status'], 'ok'); self.assertEqual(ledger['events'], [])
        self.body = self.body.replace(b'<p>', b'<script>dynamic()</script><p class="new-style">  ').replace(b'November 2', b'November\n 2')
        second = self.run_collect(-4)
        self.assertEqual({p['observation'] for p in second['pages'].values()}, {'unchanged'})
        ledger, report = reconcile(ledger, self.scopes(), NOW.isoformat())
        self.assertEqual(report['added_revisions'], 0)
        self.config['parser_version'] += 1; self.save_config()
        self.body = html('An officer has changed during a parser upgrade; review baseline.')
        migrated = self.run_collect(-3)
        self.assertEqual({p['observation'] for p in migrated['pages'].values()}, {'baseline'})
        ledger, _ = reconcile(ledger, self.scopes(), NOW.isoformat())
        self.assertEqual(ledger['events'], [])

    def test_equal_party_rules_meaningful_categories_and_no_duplicate_replay(self):
        self.run_collect(-5); ledger, _ = reconcile(empty(), self.scopes(), NOW.isoformat())
        for index, (category, text) in enumerate([
                ('leadership-contact', 'The chair and secretary have been appointed for our organization.'),
                ('event-meeting', 'Our next meeting has been postponed to November 12 at town hall.'),
                ('candidate-endorsement', 'Our candidates have received an endorsement from the county party.'),
                ('position-statement', 'Our position: we support changes described in this public statement.')]):
            self.body = html(text); state = self.run_collect(-4+index)
            changes = [p['change'] for p in state['pages'].values()]
            self.assertEqual(changes[0]['categories'], changes[1]['categories'])
            self.assertIn(category, changes[0]['categories'])
            ledger, report = reconcile(ledger, self.scopes(), NOW.isoformat())
            self.assertEqual(report['added_revisions'], 2)
        self.assertEqual(len(public_events(ledger)), 8)
        for event in ledger['events']:
            self.assertEqual(event['fact']['members'], [])
            self.assertIsNone(event['fact']['occurred_at'])
            self.assertIn('edit date unknown', event['inclusion_reason'])
        replay, _ = reconcile(ledger, self.scopes(), NOW.isoformat())
        self.assertEqual(replay['events'], ledger['events'])

    def test_failure_retains_last_good_and_recovery_labels_collection_gap(self):
        initial = self.run_collect(-5); self.unavailable = True; failed = self.run_collect(-4)
        for url, page in failed['pages'].items():
            self.assertEqual(page['status'], 'failed')
            self.assertEqual(page['projection'], initial['pages'][url]['projection'])
            self.assertEqual(page['last_good_at'], initial['pages'][url]['last_good_at'])
        self.unavailable = False; self.body = html('The next meeting is canceled. A new notice will follow later.')
        recovered = self.run_collect(-3)
        self.assertTrue(all(p['change']['after_gap'] for p in recovered['pages'].values()))

    def test_two_unreconciled_edits_survive_and_acknowledged_queue_is_bounded(self):
        self.run_collect(-5); ledger, _ = reconcile(empty(), self.scopes(), NOW.isoformat())
        (self.root/'data/change-ledger.json').write_text(json.dumps(ledger))
        self.body = html('Our meeting has moved to November 12 at the town hall.')
        self.run_collect(-4)
        self.body = html('Our meeting has moved again to November 13 at the town hall.')
        state = self.run_collect(-3)
        self.assertTrue(all(len(p['pending_changes']) == 2 for p in state['pages'].values()))
        ledger, report = reconcile(ledger, self.scopes(), NOW.isoformat())
        self.assertEqual(report['added_revisions'], 4)
        (self.root/'data/change-ledger.json').write_text(json.dumps(ledger))
        state = self.run_collect(-2)
        self.assertTrue(all(p['pending_changes'] == [] for p in state['pages'].values()))
        again, report = reconcile(ledger, self.scopes(), NOW.isoformat())
        self.assertEqual(report['added_revisions'], 0)

    def test_long_paragraph_evidence_is_centered_on_changed_date(self):
        old = {'projection': {'lines': ['Background information. ' * 40 + 'Meeting November 12 at the hall.']}}
        new = {'projection': {'lines': ['Background information. ' * 40 + 'Meeting November 14 at the hall.']}}
        before, after = parties.diff_excerpts(old, new)
        self.assertIn('November 12', before); self.assertIn('November 14', after)
        self.assertLessEqual(len(before), 360); self.assertLessEqual(len(after), 360)

    def test_full_pending_outbox_can_reconcile_before_collection_retries(self):
        self.run_collect(-20); ledger, _ = reconcile(empty(), self.scopes(), NOW.isoformat())
        (self.root/'data/change-ledger.json').write_text(json.dumps(ledger))
        for i in range(9):
            self.body = html('Our next meeting is now on November ' + str(i+2) + ' at the town hall.')
            state = self.run_collect(-18+i)
        self.assertEqual({p['error'] for p in state['pages'].values()}, {'party-pending-change-bound'})
        self.assertTrue(all(len(p['pending_changes']) == 8 for p in state['pages'].values()))
        ledger, report = reconcile(ledger, self.scopes(), NOW.isoformat())
        self.assertEqual(report['added_revisions'], 16)
        (self.root/'data/change-ledger.json').write_text(json.dumps(ledger))
        self.assertEqual(self.run_collect(-2)['status'], 'ok')

    def test_missing_robots_404_is_distinct_from_forbidden_or_unavailable(self):
        from urllib.error import HTTPError
        rss = b'<rss><channel/></rss>'
        for code, status in [(404, 'ok'), (403, 'failed'), (429, 'failed'), (503, 'failed')]:
            def get(url, limit):
                if url.endswith('robots.txt'): raise HTTPError(url, code, 'test', {}, None)
                return rss, 'application/rss+xml'
            result = parties.collect_mentions(self.root, NOW.isoformat(), get)
            self.assertEqual(result['sources']['lee-county']['status'], status)

    def test_old_held_changes_remain_visible_after_more_recent_activity(self):
        self.body = html('County public information for all visitors.', '<a href="/old/">Information</a>')
        self.run_collect(-30); ledger, _ = reconcile(empty(), self.scopes(), NOW.isoformat())
        self.body = self.body.replace(b'/old/', b'/new/'); self.run_collect(-29)
        ledger, _ = reconcile(ledger, self.scopes(), NOW.isoformat())
        for i in range(7):
            (self.root/'data/change-ledger.json').write_text(json.dumps(ledger))
            self.body = html('Our regular meeting will take place November ' + str(2+i) + ' in the town hall.')
            self.run_collect(-20+i); ledger, _ = reconcile(ledger, self.scopes(), NOW.isoformat())
        (self.root/'data/change-ledger.json').write_text(json.dumps(ledger))
        result = parties.panel(self.root)
        self.assertIn('Show changes held for review (2)', result)
        self.assertIn('without a reviewed category', result)

    def test_empty_shrink_bounds_and_source_binding_fail_closed(self):
        self.body = html('Our meeting details are published here. ' * 100)
        first = self.run_collect(-5)
        self.body = html('Our meeting is now at the town hall.')
        shrunk = self.run_collect(-4)
        self.assertEqual({p['error'] for p in shrunk['pages'].values()}, {'party-content-shrink-review'})
        self.assertEqual(next(iter(first['pages'].values()))['projection'], next(iter(shrunk['pages'].values()))['projection'])
        self.body = b'<html><main></main></html>'
        self.assertEqual({p['error'] for p in self.run_collect(-3)['pages'].values()}, {'party-content-structure'})
        with self.assertRaises(ValueError): parties.approved('https://example.org/page', 'leecodemocrats.com')

    def test_contact_changes_are_detected_without_storing_addresses(self):
        mail = 'office' + chr(64) + 'example.org'
        self.body = html('Contact our county organization for information.', '<a href="mailto:' + mail + '">Email</a>')
        self.run_collect(-5)
        self.body = self.body.replace(b'office', b'new-office')
        state = self.run_collect(-4)
        self.assertTrue(all('leadership-contact' in p['change']['categories'] for p in state['pages'].values()))
        self.assertNotIn(mail, json.dumps(state)); self.assertEqual(violations(json.dumps(state)), [])

    def test_rotating_social_contact_values_do_not_change_party_projection(self):
        first = html('Contact our county organization for information.', '<div id="cff">Social hotline 555-123-4567</div>')
        second = first.replace(b'555-123-4567', b'555-987-6543')
        page = {'path': '/'}
        self.assertEqual(parties.parse_page(first,page,'leecodemocrats.com'), parties.parse_page(second,page,'leecodemocrats.com'))

    def test_unclassified_link_change_is_visible_for_review_not_feed(self):
        self.body = html('County public information for all visitors.', '<a href="/old/">Information</a>')
        self.run_collect(-5); ledger, _ = reconcile(empty(), self.scopes(), NOW.isoformat())
        self.body = self.body.replace(b'/old/', b'/new/')
        self.run_collect(-4); ledger, _ = reconcile(ledger, self.scopes(), NOW.isoformat())
        self.assertEqual(public_events(ledger), [])
        self.assertEqual(len(ledger['events']), 2)
        self.assertEqual(ledger['events'][0]['fact']['categories'], ['unclassified'])
        scope = self.scopes()[0]; fact = deepcopy(scope['facts'][0]); fact['entities'] = ['lee-gop']
        self.assertIn('party-entity-source', validate_fact(fact, scope))

    def test_robots_disallow_and_stale_scope_never_claim_success(self):
        def deny(url, limit): return b'User-agent: *\nDisallow: /', 'text/plain'
        result = parties.collect(self.root, NOW.isoformat(), deny)
        self.assertEqual({p['error'] for p in result['pages'].values()}, {'party-robots-disallow'})
        self.run_collect(-60*49)
        self.assertFalse(any(s['complete'] for s in self.scopes()))

    def test_new_detail_and_image_baseline_and_poster_change_require_review(self):
        self.config = read(ROOT/'config/parties.json'); self.save_config()
        image = [b'\x89PNG\r\n\x1a\nimage-one']
        def get(url, limit):
            if url.endswith('.png'): return image[0], 'image/png'
            return self.get(url, limit)
        parties.collect(self.root, (NOW-timedelta(minutes=5)).isoformat(), get)
        ledger, _ = reconcile(empty(), self.scopes(), NOW.isoformat())
        self.assertEqual(len(ledger['events']), 0)
        image[0] += b'-changed'
        parties.collect(self.root, (NOW-timedelta(minutes=4)).isoformat(), get)
        ledger, report = reconcile(ledger, self.scopes(), NOW.isoformat())
        self.assertEqual(report['added_revisions'], 1)
        self.assertEqual(public_events(ledger), [])
        self.assertEqual(ledger['events'][0]['fact']['categories'], ['image-review'])

    def test_mentions_are_exact_public_title_matches_not_body_claims(self):
        rss = b'<rss><channel><item><title>Lee County meeting coverage</title><link>https://capitolfax.com/public/</link><pubDate>Mon, 19 Oct 2026 10:00:00 GMT</pubDate></item><item><title>Protected: Lee County</title><link>https://capitolfax.com/private/</link></item><item><title>State update</title><description>Lee County</description></item></channel></rss>'
        def get(url, limit):
            if url.endswith('robots.txt'): return b'User-agent: *\nAllow: /', 'text/plain'
            return rss, 'application/rss+xml'
        result = parties.collect_mentions(self.root, NOW.isoformat(), get)
        self.assertEqual(result['sources']['lee-county']['matched'], 1)
        self.assertEqual(result['model_calls'], 0)

    def test_mentions_surname_query_covers_aliases_with_one_twelve_candidate_budget(self):
        self.config['mention_terms'] = {'fritts': ['Bradley Fritts', 'Brad Fritts']}; self.save_config()
        seen = []
        def get(url, limit):
            seen.append(url)
            if url.endswith('robots.txt'): return b'User-agent: *\nAllow: /', 'text/plain'
            return b'<rss><channel/></rss>', 'application/rss+xml'
        parties.collect_mentions(self.root, NOW.isoformat(), get)
        from urllib.parse import parse_qs, urlsplit
        self.assertEqual(parse_qs(urlsplit(seen[1]).query)['s'], ['Fritts'])
        self.assertEqual(len(seen), 2)

    def test_party_failures_and_recoveries_enter_bounded_journal(self):
        self.unavailable = True; self.run_collect(-5)
        j = error_journal.Journal(self.root, NOW)
        error_journal.ingest(j, {'parties': read(self.root/'data/party-state.json')})
        self.assertEqual(len(j.data['incidents']), 2)
        self.unavailable = False; self.run_collect(-4)
        error_journal.ingest(j, {'parties': read(self.root/'data/party-state.json')})
        self.assertTrue(all(i['status'] == 'resolved' for i in j.data['incidents']))


class RelevanceTests(unittest.TestCase):
    def test_structure_before_keyword_exact_reasons_and_no_stance(self):
        fact = {'title': 'Energy changes', 'detail': 'Assigned to Housing', 'committee_names': ['Public Utilities'], 'statutes': ['40 ILCS 5/1']}
        result = explain(fact); topics = {r['topic']: r for r in result['topics']}
        self.assertEqual(topics['energy']['basis'], 'structural')
        self.assertEqual(topics['pensions']['reasons'], ['statute reference: 40 ILCS 5/1'])
        self.assertEqual(topics['housing']['reasons'], ['committee association: Housing'])
        self.assertEqual(fact['committee_names'], ['Public Utilities'])
        self.assertEqual(result['stance'], 'not inferred')
        self.assertEqual(explain({'title': 'Energy update'})['topics'][0]['basis'], 'keyword-provisional')

    def test_unknown_tally_never_becomes_unanimity_and_resolutions_not_blanket_hidden(self):
        self.assertFalse(explain({'kind': 'vote', 'title': 'Housing', 'totals': {}})['hidden'])
        self.assertTrue(explain({'kind': 'vote', 'title': 'Housing', 'totals': {'nays': 0}})['hidden'])
        self.assertFalse(explain({'kind': 'bill-action', 'title': 'RESOLUTION-HOUSING POLICY'})['hidden'])
        self.assertTrue(explain({'kind': 'bill-action', 'title': 'CONGRATS-COMMUNITY SERVICE'})['hidden'])

    def test_hosted_workflow_is_secret_free_and_preserves_inference_history(self):
        workflow = (ROOT/'.github/workflows/parties.yml').read_text()
        self.assertNotIn('secrets.', workflow); self.assertNotIn('civic_tracker.media ', workflow)
        self.assertIn('group: m0-source-evidence', workflow)
        self.assertIn('sha256sum --check', workflow)
        self.assertIn('source_sha: ${{ steps.journal.outputs.sha }}', workflow)
        self.assertNotIn('schedule:', workflow)


if __name__ == '__main__': unittest.main()
