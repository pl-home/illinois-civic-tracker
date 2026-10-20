"""Stateful acceptance for Stage A. Offline; no PDF/model/source requests."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from civic_tracker.changes import (empty, reconcile, public_events, validate_fact, packed, read, collect)
from civic_tracker.change_sources import evidence, fact, scope, federal, illinois, publications
from civic_tracker.change_feed import atom, payload, render, write_if_changed

ROOT = Path(__file__).resolve().parents[1]
DAY1 = '2026-10-19T13:00:00+00:00'
DAY2 = '2026-10-20T13:00:00+00:00'
DAY3 = '2026-10-21T13:00:00+00:00'
URL = 'https://ilga.gov/Legislation/BillStatus?DocNum=24&GAID=18&DocTypeID=HB&SessionID=114'


def row(**extra):
    value = fact('HB24:role:3428', 'sponsor-role', 'IL', ['fritts'], 'Home repair',
        'Added Co-Sponsor Rep. Bradley Fritts', evidence(URL, DAY1, 'official-bill', 'a'*64),
        '2026-10-19', measure='IL-104-HB24', role='co-sponsor', operation='added-or-changed')
    value.update(extra)
    return value


def observation(rows=None, checked=DAY1, **extra):
    return scope('ilga:test:HB24', 'IL', checked, True, rows if rows is not None else [row()], **extra)


class ChangeTests(unittest.TestCase):
    def baseline(self):
        return reconcile(empty(), [observation()], DAY1)[0]

    def test_initial_baseline_and_unchanged_replay_emit_nothing(self):
        baseline = self.baseline()
        self.assertEqual(public_events(baseline), [])
        replay, report = reconcile(baseline, [observation(checked=DAY2)], DAY2)
        self.assertEqual(replay['events'], [])
        self.assertEqual(report['added_revisions'], 0)
        self.assertEqual(report['unchanged_facts'], 1)

    def test_correction_revert_and_multiple_same_day_actions(self):
        initial = self.baseline()
        corrected = row(detail='Removed Co-Sponsor Rep. Bradley Fritts', operation='removed')
        second = row(key='second-action', occurred_at='2026-10-20')
        changed, report = reconcile(initial, [observation([corrected, second], DAY2)], DAY2)
        self.assertEqual(report['added_revisions'], 2)
        revised = next(e for e in changed['events'] if e['change'] == 'corrected')
        self.assertTrue(revised['supersedes'].endswith('-r0'))
        self.assertEqual(revised['previous_fact']['detail'], row()['detail'])
        again, _ = reconcile(changed, [observation([row(), second], DAY3)], DAY3)
        last = again['events'][-1]
        self.assertEqual(last['id'], revised['id'])
        self.assertEqual(last['revision'], 2)
        self.assertEqual(last['supersedes'], revised['revision_id'])
        self.assertEqual(len(public_events(again)), 2)

    def test_complete_role_removal_and_readdition_preserve_lineage(self):
        first = observation(removals=True)
        initial, _ = reconcile(empty(), [first], DAY1)
        removed, _ = reconcile(initial, [observation([], DAY2, removals=True)], DAY2)
        event = removed['events'][-1]
        self.assertEqual(event['change'], 'removed')
        self.assertIsNone(event['fact']['occurred_at'])
        self.assertEqual(event['fact']['date_precision'], 'unknown')
        replay, _ = reconcile(removed, [observation([], DAY3, removals=True)], DAY3)
        self.assertEqual(replay['events'], removed['events'])
        added, _ = reconcile(replay, [observation(checked='2026-10-22T13:00:00+00:00', removals=True)], '2026-10-22T13:00:00+00:00')
        self.assertEqual(added['events'][-1]['id'], event['id'])
        self.assertEqual(added['events'][-1]['previous_fact']['operation'], 'removed')

    def test_incomplete_and_regressed_sources_keep_facts_and_cursor(self):
        initial = self.baseline()
        for bad in [{**observation([], DAY2, removals=True), 'complete': False}, observation([], '2026-10-18T13:00:00+00:00')]:
            result, report = reconcile(initial, [bad], DAY2)
            self.assertEqual(result['facts'], initial['facts'])
            self.assertEqual(result['scopes'], initial['scopes'])
            self.assertEqual(result['events'], [])
            self.assertEqual(report['status'], 'partial')

    def test_failed_scope_does_not_prevent_healthy_source_progress(self):
        initial = self.baseline()
        failed = {**observation([], DAY2), 'complete': False}
        healthy = scope('different', 'IL', DAY2, True, [row()], family='new-source')
        result, report = reconcile(initial, [failed, healthy], DAY2)
        self.assertIn('different', result['scopes'])
        self.assertEqual(result['scopes']['ilga:test:HB24'], initial['scopes']['ilga:test:HB24'])
        self.assertEqual(report['withheld_scopes'], 1)

    def test_baseline_new_source_and_adapter_migration_are_quiet(self):
        initial = self.baseline()
        migration = {**observation([row(detail='Parser representation changed')]), 'adapter': 2}
        result, _ = reconcile(initial, [migration], DAY2)
        self.assertEqual(result['events'], [])
        self.assertEqual(public_events(result), [])

    def test_new_bill_in_established_family_can_emit_and_history_stays_quiet(self):
        initial, _ = reconcile(empty(), [observation(family='ilga-xml', baseline_on_add=False)], DAY1)
        new = {**observation([row(key='new', occurred_at='2026-10-20')], DAY2, family='ilga-xml', baseline_on_add=False), 'id': 'ilga:new'}
        old = {**observation([row(key='old', occurred_at='2025-01-01')], DAY2, family='ilga-xml', baseline_on_add=False), 'id': 'ilga:old'}
        result, _ = reconcile(initial, [new, old], DAY2)
        self.assertEqual(len(result['events']), 2)
        self.assertEqual([e['fact']['key'] for e in public_events(result)], ['new'])

    def test_transport_freshness_and_hash_change_are_not_activity(self):
        initial = self.baseline()
        updated = row(evidence=evidence(URL, DAY2, 'official-bill', 'b'*64))
        result, _ = reconcile(initial, [observation([updated], DAY2)], DAY2)
        self.assertEqual(result['events'], [])
        self.assertEqual(next(iter(result['facts'].values()))['fact']['evidence']['sha256'], 'b'*64)

    def test_duplicate_identity_unknown_role_member_and_wrong_session_quarantine(self):
        bad_rows = [[row(), row()], [row(role=None)], [row(members=['duckworth'])],
                    [row(session=105)], [row(kind='unknown')], [row(measure='IL-104-HB25')],
                    [row(evidence=evidence('https://ilga.gov/Legislation/BillStatus?DocNum=24&GAID=18&DocTypeID=HB&SessionID=114&api_key=synthetic', DAY1, 'official-bill'))]]
        for rows in bad_rows:
            result, report = reconcile(self.baseline(), [observation(rows, DAY2)], DAY2)
            self.assertEqual(report['withheld_scopes'], 1)
            self.assertEqual(public_events(result), [])
            self.assertNotIn('synthetic', packed(report))

    def test_conflicting_replay_cannot_rewrite_source_receipt(self):
        initial = self.baseline()
        result, report = reconcile(initial, [observation([row(detail='changed')])], DAY2)
        self.assertIn('conflicting-replay', report['errors'][0]['codes'])
        self.assertEqual(result['facts'], initial['facts'])

    def test_disappearing_scope_is_reported_without_aging_its_cursor_forward(self):
        initial = self.baseline()
        result, report = reconcile(initial, [], DAY2)
        self.assertEqual(result['facts'], initial['facts'])
        self.assertEqual(result['scopes'], initial['scopes'])
        self.assertEqual(report['errors'][0]['codes'], ['scope-not-observed'])

    def test_agreeing_but_unreviewed_service_session_still_fails(self):
        future = row(session=105)
        group = {**observation([future]), 'session': 105}
        self.assertIn('source-session-mismatch', validate_fact(future, group))

    def test_history_and_calendar_absence_are_not_deletions(self):
        initial = self.baseline()
        after, _ = reconcile(initial, [observation([], DAY2)], DAY2)
        self.assertEqual(after['facts'], initial['facts'])
        self.assertEqual(after['events'], [])

    def test_exception_queue_is_bounded_without_source_text(self):
        bad = [{**observation([row(detail='do not log source body')], DAY2), 'id': 'scope-' + str(i), 'complete': False} for i in range(80)]
        result, report = reconcile(self.baseline(), [observation(checked=DAY2)] + bad, DAY2)
        self.assertEqual(len(result['exceptions']), 64)
        self.assertEqual(report['withheld_scopes'], 80)
        self.assertNotIn('do not log', packed(result['exceptions']))

    def test_size_ceiling_fails_before_mutating_input(self):
        initial = self.baseline(); before = deepcopy(initial)
        with patch('civic_tracker.changes.MAX_LEDGER', 10):
            with self.assertRaisesRegex(ValueError, 'size-budget'): reconcile(initial, [observation(checked=DAY2)], DAY2)
        self.assertEqual(initial, before)

    def test_every_public_channel_uses_same_gate_and_deterministic_atom(self):
        initial = self.baseline()
        changed, _ = reconcile(initial, [observation([row(title='<script>bad & "quoted"</script>', detail='Corrected detail')], DAY2)], DAY2)
        rows = public_events(changed)
        data = {'events': rows, 'updated_at': DAY2, 'baseline_at': DAY1}
        xml = atom(data)
        parsed = ET.fromstring(xml)
        self.assertEqual(len(parsed.findall('{http://www.w3.org/2005/Atom}entry')), 1)
        self.assertNotIn('<script>', render(data, {}))
        self.assertEqual(xml, atom(data))
        changed['events'][0]['fact']['role'] = 'invented'
        self.assertEqual(public_events(changed), [])
        data['events'] = public_events(changed)
        self.assertNotIn('<entry>', atom(data))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'changes.atom'
            self.assertTrue(write_if_changed(path, xml))
            self.assertFalse(write_if_changed(path, xml))

    def test_vote_identity_choice_tally_and_proof_binding(self):
        vote = fact('US-119-HOUSE-2-00313:lahood', 'vote', 'US', ['lahood'], 'Water Resources', 'On passage',
            evidence('https://clerk.house.gov/Votes/2026313', DAY1, 'official-roll', 'a'*64),
            '2026-09-16', roll_id='US-119-HOUSE-2-00313', choice='yes', totals={'yes': 415, 'no': 9}, vote_scope='floor')
        group = scope('house-vote', 'US', DAY1, True, [vote])
        self.assertEqual(validate_fact(vote, group), [])
        for changed, code in [(dict(choice='unknown'), 'unknown-choice'), (dict(totals={'yes': 0}), 'choice-tally-conflict'),
                              (dict(roll_id='US-119-HOUSE-2-00314'), 'roll-evidence-mismatch')]:
            self.assertIn(code, validate_fact({**vote, **changed}, group))

    def test_title_or_current_association_edit_does_not_revise_past_actions(self):
        original = row(kind='bill-action')
        title = row(key='title', kind='bill-title')
        initial, _ = reconcile(empty(), [observation([original, title])], DAY1)
        after, _ = reconcile(initial, [observation([
            {**original, 'title': 'New short title', 'members': ['fritts', 'arellano']},
            {**title, 'title': 'New short title'}], DAY2)], DAY2)
        self.assertEqual([e['fact']['kind'] for e in after['events']], ['bill-title'])

    def test_same_day_timestamped_post_after_baseline_is_new(self):
        initial = self.baseline()
        article = row(key='post', kind='publication', occurred_at='2026-10-19T16:00:00+00:00', date_precision='timestamp',
            publication_kind='office', publisher='Office', evidence=evidence('https://repfritts.com/news/post', DAY2, 'publisher-listing'))
        after, _ = reconcile(initial, [observation([row(), article], DAY2)], DAY2)
        self.assertEqual(len(public_events(after)), 1)
        self.assertEqual(public_events(after)[0]['fact']['key'], 'post')

    def test_recent_backfill_before_baseline_stays_history(self):
        initial = self.baseline()
        after, _ = reconcile(initial, [observation([row(), row(key='recent-old', occurred_at='2026-10-18')], DAY2)], DAY2)
        self.assertEqual(len(after['events']), 1)
        self.assertEqual(public_events(after), [])

    def test_mixed_jurisdiction_party_publication_is_not_lost_or_duplicated(self):
        item = {'url': 'https://leecountyilgop.org/post/', 'title': 'Party statement', 'published_at': '2026-10-19',
                'publisher': 'County party', 'kind': 'party'}
        state = {'sources': {'party': {'status': 'ok', 'checked_at': DAY2, 'members': ['fritts', 'arellano', 'lahood'],
            'source_url': 'https://leecountyilgop.org/', 'items': [{**item, 'member_id': m} for m in ['fritts', 'arellano', 'lahood']]}}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'data').mkdir()
            (root/'data/communications-state.json').write_text(packed(state))
            scopes = list(publications(root, {'members': []}))
        self.assertEqual(len(scopes), 2)
        self.assertEqual(sorted(len(s['facts'][0]['members']) for s in scopes), [1, 2])
        self.assertTrue(all(not validate_fact(f,s) for s in scopes for f in s['facts']))

    def test_total_data_budget_failure_preserves_prior_ledger(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root/'data').mkdir(); (root/'config').mkdir()
            path = root/'data/change-ledger.json'; path.write_text(packed(self.baseline()))
            prior = path.read_bytes()
            (root/'config/daily.json').write_text('{"max_data_bytes":10}')
            with patch('civic_tracker.change_sources.observations', return_value=[observation(checked=DAY2)]):
                with self.assertRaisesRegex(ValueError, 'public-data-size'): collect(root, DAY2)
            self.assertEqual(path.read_bytes(), prior)
            self.assertFalse((root/'data/change-quality-report.json').exists())

    def test_publication_rejects_tampered_event_despite_status_and_official_url(self):
        after, _ = reconcile(self.baseline(), [observation([row(detail='Correction')], DAY2)], DAY2)
        after['events'][0]['fact']['detail'] = 'Unverified replacement'
        self.assertEqual(public_events(after), [])

    def test_live_baseline_feed_build_and_replay_do_not_touch_paid_ledgers(self):
        from civic_tracker.change_sources import observations
        before = {p.name: p.read_bytes() for p in (ROOT/'data').glob('*ledger*.json')}
        initial, report = reconcile(empty(), observations(ROOT), '2026-10-20T04:00:00+00:00')
        self.assertEqual(initial['events'], [])
        replay, _ = reconcile(initial, observations(ROOT), '2026-10-20T04:01:00+00:00')
        self.assertEqual(replay['events'], [])
        self.assertEqual(before, {p.name: p.read_bytes() for p in (ROOT/'data').glob('*ledger*.json')})

    def test_extreme_escaped_text_keeps_the_public_artifact_small(self):
        from civic_tracker.browse import build
        # Exercise expansion by HTML/XML escaping, not merely raw JSON length.
        initial = self.baseline()
        rows = [row(key='huge-' + str(i), kind='bill-title', title='&'*2000, detail='&'*2000,
                    occurred_at='2026-10-20') for i in range(20)]
        baseline, _ = reconcile(initial, [observation(rows, DAY2)], DAY2)
        rows = [{**f, 'title': '<'*2000} for f in rows]
        after, _ = reconcile(baseline, [observation(rows, DAY3)], DAY3)
        with tempfile.TemporaryDirectory() as temp:
            with patch('civic_tracker.change_feed.read', return_value=after):
                data = payload(ROOT)
                self.assertGreater(data['omitted_for_size'], 0)
                report = build(ROOT, Path(temp))
        self.assertLess(report['artifact_bytes'], 650_000)

    def test_quality_failure_and_recovery_reuse_the_existing_journal(self):
        from datetime import datetime
        from civic_tracker import error_journal as journal
        with tempfile.TemporaryDirectory() as temp:
            log = journal.Journal(temp, datetime.fromisoformat(DAY2))
            journal.ingest(log, {'change-quality': {'checked_at': DAY1, 'status': 'partial'}})
            self.assertEqual(log.data['incidents'][0]['code'], 'change-quality-withheld')
            journal.ingest(log, {'change-quality': {'checked_at': DAY2, 'status': 'ok'}})
            self.assertEqual(log.data['incidents'][0]['status'], 'resolved')

    def test_reviewed_state_and_federal_examples_baseline_and_replay(self):
        examples = read(ROOT / 'tests/fixtures/change-feed-reviewed.json')
        self.assertEqual({m for s in examples for f in s['facts'] for m in f['members']}, {'fritts', 'arellano', 'lahood', 'durbin', 'duckworth'})
        ledger, report = reconcile(empty(), examples, DAY1)
        self.assertEqual(report['status'], 'ok')
        self.assertEqual(ledger['events'], [])
        replay, report = reconcile(ledger, examples, DAY2)
        self.assertEqual(replay['events'], [])
        self.assertEqual(report['added_revisions'], 0)


if __name__ == '__main__': unittest.main()
