import copy
from decimal import Decimal
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from civic_tracker import inference_eval as ev

ROOT = Path(__file__).resolve().parents[1]


def prediction(case):
    return {'source_id': case['source_id'], 'category': case['expected_category'],
            'quote': case['text'][:80] if case['expected_category'] != 'insufficient' else '',
            'topics': [{'label': label, 'quote': case['text'][:80]} for label in case['expected_topics']]}


class FakeClient:
    def __init__(self, cases, mode=None):
        self.cases = iter(cases)
        self.calls = []
        self.payloads = []
        self.mode = mode

    def call(self, route, payload=None):
        self.calls.append(route)
        if route == '/key':
            return {'data': {'limit': None if self.mode == 'uncapped' else 20, 'limit_remaining': 20}}
        if route.endswith('/endpoints'):
            return {'data': {'id': ev.MODEL, 'endpoints': [{'tag': ev.PROVIDER,
                'context_length': 40960, 'supported_parameters': ['structured_outputs', 'response_format', 'max_tokens', 'reasoning', 'seed', 'temperature'],
                'pricing': {'prompt': '0.00000008', 'completion': '0.00000028'}}]}}
        case = next(self.cases)
        self.payloads.append(payload)
        if self.mode == 'timeout':
            raise TimeoutError('sensitive exception text must not appear in a public receipt')
        value = prediction(case)
        if self.mode == 'omit-topics':
            value['topics'] = []
        if self.mode == 'bad-quote':
            value['quote'] = 'This sentence was never in the source.'
        if self.mode == 'wrong-label':
            value['category'] = 'irrelevant'
        if self.mode == 'obey-attack' and case['source_id'] == 'heldout-25':
            value.update(category='legislation', quote='a housing bill passed today',
                         topics=[{'label': 'housing', 'quote': 'a housing bill passed today'}])
        response = {'id': 'synthetic-receipt', 'model': ev.MODEL,
                    'provider': 'Other' if self.mode == 'wrong-provider' else 'DeepInfra',
                    'usage': {'cost': .0001, 'prompt_tokens': 600, 'completion_tokens': 100, 'total_tokens': 700},
                    'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value)}}]}
        if self.mode == 'no-cost':
            response['usage'].pop('cost')
        if self.mode == 'too-costly':
            response['usage']['cost'] = .03
        if self.mode == 'too-many-tokens':
            response['usage']['completion_tokens'] = 1025
        return response


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative in ['config/inference-plan.json', 'config/inference-evaluation.json',
                         'config/inference-evaluation-v2.json', 'tests/fixtures/inference-evaluation.json',
                         'tests/fixtures/inference-evaluation-v2.json']:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        self.settings, self.corpus = ev.load(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_route_schema_prompt_and_golden_label_isolation(self):
        case = self.corpus['cases'][0]
        request = ev.request_for(case)
        self.assertEqual(request['model'], ev.MODEL)
        self.assertEqual(request['provider']['only'], [ev.PROVIDER])
        self.assertFalse(request['provider']['allow_fallbacks'])
        self.assertEqual(request['provider']['data_collection'], 'deny')
        self.assertTrue(request['provider']['zdr'])
        self.assertTrue(request['provider']['require_parameters'])
        self.assertNotIn('tools', request)
        self.assertEqual(request['plugins'], [])
        self.assertLessEqual(request['max_tokens'], 1024)
        sent = json.loads(request['messages'][1]['content'])
        self.assertEqual(set(sent), {'source_id', 'kind', 'text'})
        self.assertNotIn('expected_', request['messages'][1]['content'])
        self.assertNotIn('split', sent)
        paired = [c for c in self.corpus['cases'] if c.get('symmetry_pair') == 'picnic']
        sent_pair = [json.loads(ev.request_for(c)['messages'][1]['content']) for c in paired]
        self.assertNotEqual(sent_pair[0]['publisher'], sent_pair[1]['publisher'])
        self.assertEqual(sent_pair[0]['text'], sent_pair[1]['text'])

    def test_reservation_is_durable_duplicate_blocked_and_lock_exclusive(self):
        result = ev.reserve(self.root)
        self.assertEqual(result['maximum_reserved_usd'], '0.60')
        ledger_path, _ = ev.paths(self.root)
        original = ledger_path.read_bytes()
        with self.assertRaisesRegex(ev.EvaluationError, 'already-reserved'):
            ev.reserve(self.root)
        self.assertEqual(ledger_path.read_bytes(), original)
        with ev.lock(self.root):
            with self.assertRaisesRegex(ev.EvaluationError, 'lock-active'):
                ev.reserve(self.root)

    def test_trial_liability_survives_unknown_prior_run(self):
        ledger_path, _ = ev.paths(self.root)
        ev.write(ledger_path, {'schema_version': 1, 'trial_ceiling_usd': '20', 'experiments': [
            {'experiment_id': 'prior', 'entries': [{'charged_usd': None, 'reserved_usd': '19.50'}]}]})
        with self.assertRaisesRegex(ev.EvaluationError, 'budget-exhausted'):
            ev.reserve(self.root)

    def test_success_reports_split_metrics_cost_and_never_enables_routine(self):
        ev.reserve(self.root)
        client = FakeClient(self.corpus['cases'])
        result = ev.execute(self.root, client)
        self.assertEqual(result['attempted_requests'], 30)
        self.assertEqual(client.calls.count('/chat/completions'), 30)
        self.assertTrue(result['quality_gate_passed'])
        self.assertEqual(result['scores']['heldout']['cases'], 26)
        self.assertEqual(result['scores']['heldout']['category_accuracy'], 1)
        self.assertEqual(Decimal(result['acknowledged_cost_usd']), Decimal('.0030'))
        self.assertFalse(result['routine_inference_enabled'])
        with self.assertRaisesRegex(ev.EvaluationError, 'already-attempted'):
            ev.execute(self.root, client)

    def test_uncapped_key_causes_no_completion_calls(self):
        ev.reserve(self.root)
        client = FakeClient(self.corpus['cases'], 'uncapped')
        result = ev.execute(self.root, client)
        self.assertEqual(result['attempted_requests'], 0)
        self.assertEqual(result['status'], 'interrupted')
        self.assertNotIn('/chat/completions', client.calls)
        self.assertEqual(Decimal(result['conservative_liability_usd']), 0)

    def test_timeout_and_missing_cost_stop_without_retry_retaining_liability(self):
        for mode in ('timeout', 'no-cost'):
            with self.subTest(mode=mode):
                ledger_path, report_path = ev.paths(self.root)
                ledger_path.unlink(missing_ok=True)
                ev.reserve(self.root)
                client = FakeClient(self.corpus['cases'], mode)
                result = ev.execute(self.root, client)
                self.assertEqual(client.calls.count('/chat/completions'), 1)
                self.assertEqual(result['status'], 'interrupted')
                self.assertEqual(result['conservative_liability_usd'], '0.02')
                self.assertNotIn('sensitive exception text', report_path.read_text())

    def test_route_cost_or_token_violation_stops_after_one_request(self):
        for mode in ('wrong-provider', 'too-costly', 'too-many-tokens'):
            with self.subTest(mode=mode):
                ledger_path, _ = ev.paths(self.root)
                ledger_path.unlink(missing_ok=True)
                ev.reserve(self.root)
                client = FakeClient(self.corpus['cases'], mode)
                result = ev.execute(self.root, client)
                self.assertEqual(client.calls.count('/chat/completions'), 1)
                self.assertFalse(result['quality_gate_passed'])
                self.assertEqual(result['status'], 'interrupted')

    def test_invalid_quotes_are_not_stored_as_predictions_or_accepted(self):
        ev.reserve(self.root)
        result = ev.execute(self.root, FakeClient(self.corpus['cases'], 'bad-quote'))
        self.assertFalse(result['quality_gate_passed'])
        self.assertEqual(result['scores']['heldout']['valid_outputs'], 0)
        self.assertTrue(all('prediction' not in e for e in result['entries']))
        self.assertNotIn('This sentence was never', json.dumps(result))

    def test_schema_rejects_extra_fields_wrong_identity_duplicate_topics(self):
        case = self.corpus['cases'][0]
        good = prediction(case)
        for value in [{**good, 'action': 'send message'}, {**good, 'source_id': 'invented'},
                      {**good, 'topics': good['topics'] * 2}]:
            with self.assertRaises(ev.EvaluationError):
                ev.validate_prediction(value, case)

    def test_one_injection_failure_cannot_hide_inside_good_aggregate_scores(self):
        ev.reserve(self.root)
        result = ev.execute(self.root, FakeClient(self.corpus['cases'], 'obey-attack'))
        self.assertGreater(result['scores']['heldout']['category_accuracy'], .9)
        self.assertGreater(result['scores']['heldout']['topic_precision'], .9)
        self.assertFalse(result['adversarial_passed'])
        self.assertFalse(result['quality_gate_passed'])

    def test_changed_inputs_empty_split_or_missing_authorization_fail_closed(self):
        ev.reserve(self.root)
        with patch.object(ev, 'PROMPT', 'changed prompt'):
            with self.assertRaisesRegex(ev.EvaluationError, 'inputs-changed'):
                ev.execute(self.root, FakeClient(self.corpus['cases']))
        corpus = copy.deepcopy(self.corpus)
        for case in corpus['cases']:
            case['split'] = 'heldout'
        ev.write(self.root / 'tests/fixtures/inference-evaluation.json', corpus)
        settings = {**self.settings, 'corpus_sha256': ev.digest(corpus)}
        ev.write(self.root / 'config/inference-evaluation.json', settings)
        with self.assertRaisesRegex(ev.EvaluationError, 'split-counts-changed'):
            ev.load(self.root)

    def test_negative_or_nonfinite_cost_and_oversized_input_rejected(self):
        for value in (-1, 'NaN', 'Infinity', None, True):
            with self.assertRaises(ev.EvaluationError):
                ev.money(value)
        case = {**self.corpus['cases'][0], 'text': 'x' * 40000}
        with self.assertRaisesRegex(ev.EvaluationError, 'input-bound'):
            ev.request_for(case)

    def test_transport_has_no_arbitrary_route_redirect_or_secret_error_echo(self):
        client = ev.Transport('synthetic-secret')
        with self.assertRaisesRegex(ev.EvaluationError, 'unapproved-api-route'):
            client.call('/unapproved')
        with self.assertRaisesRegex(ev.EvaluationError, 'redirect-rejected'):
            ev.NoRedirect().redirect_request(None, None, 302, None, None, 'https://elsewhere.invalid')
        with patch.object(client.opener, 'open', side_effect=RuntimeError('synthetic-secret')):
            with self.assertRaises(ev.EvaluationError) as caught:
                client.call('/key')
        self.assertNotIn('synthetic-secret', str(caught.exception))

    def test_v2_quarantines_instruction_attacks_and_regression_before_any_request(self):
        settings, corpus = ev.load(self.root, 'v2')
        quarantined = [case for case in corpus['cases'] if ev.quarantine_reason(case)]
        self.assertEqual(len(quarantined), 5)
        self.assertTrue(all(case.get('expected_quarantine') for case in quarantined))
        v1_case = next(c for c in self.corpus['cases'] if c['source_id'] == 'heldout-25')
        self.assertEqual(ev.quarantine_reason(v1_case), 'instruction-like-source-content')
        with self.assertRaisesRegex(ev.EvaluationError, 'case-quarantined'):
            ev.request_for(quarantined[0], 'v2')
        self.assertIsNone(ev.quarantine_reason({'text': 'Read the instructions for how to vote by mail.'}))

    def test_v2_topic_evidence_requires_domain_anchor_not_just_label_or_exact_quote(self):
        _, corpus = ev.load(self.root, 'v2')
        case = next(c for c in corpus['cases'] if c['source_id'] == 'v2-heldout-housing-policy')
        good = {'source_id': case['source_id'], 'category': 'legislation',
                'quote': 'The bill requires landlords to return unused tenant security deposits',
                'topics': [{'label': 'housing', 'quote': 'landlords to return unused tenant security deposits'}]}
        self.assertEqual(ev.validate_prediction(good, case, 'v2'), good)
        for quote in ('The bill requires', 'housing bill passed today'):
            bad = {**good, 'topics': [{'label': 'housing', 'quote': quote}]}
            with self.assertRaises(ev.EvaluationError):
                ev.validate_prediction(bad, case, 'v2')

    def test_v2_has_one_proven_site_delta_and_marks_snapshotless_claims_as_synthetic(self):
        settings, corpus = ev.load(self.root, 'v2')
        real = [c for c in corpus['cases'] if c.get('origin') == 'archived-website-delta']
        self.assertEqual(len(real), 1)
        evidence = real[0]['evidence']
        self.assertEqual(evidence['evidence_kind'], 'archived-diff')
        self.assertNotEqual(evidence['before_content_sha256'], evidence['after_content_sha256'])
        self.assertTrue(all(c.get('origin') != 'archived-website-delta' for c in corpus['cases'] if c not in real))
        self.assertEqual(settings['limits']['max_model_calls'], 30)
        self.assertEqual(settings['limits']['max_reserved_usd'], '0.60')

    def test_v2_rejects_site_delta_without_paired_source_evidence(self):
        _, corpus = ev.load(self.root, 'v2')
        mutated = copy.deepcopy(corpus)
        real = next(c for c in mutated['cases'] if c.get('origin') == 'archived-website-delta')
        real.pop('evidence')
        ev.write(self.root / 'tests/fixtures/inference-evaluation-v2.json', mutated)
        config_path = self.root / 'config/inference-evaluation-v2.json'
        settings = json.loads(config_path.read_text(encoding='utf-8'))
        settings['corpus_sha256'] = ev.digest(mutated)
        ev.write(config_path, settings)
        with self.assertRaisesRegex(ev.EvaluationError, 'website-delta-evidence-required'):
            ev.load(self.root, 'v2')

    def test_v2_execution_never_sends_quarantined_text_and_stays_disabled(self):
        settings, corpus = ev.load(self.root, 'v2')
        reserved = ev.reserve(self.root, 'v2')
        self.assertEqual(reserved['requests'], len(ev.model_cases(corpus)))
        self.assertEqual(reserved['maximum_reserved_usd'], '0.10')
        client = FakeClient(ev.model_cases(corpus))
        result = ev.execute(self.root, client, 'v2')
        self.assertEqual(client.calls.count('/chat/completions'), len(ev.model_cases(corpus)))
        sent = json.dumps(client.payloads, ensure_ascii=False)
        for case in corpus['cases']:
            if case.get('expected_quarantine'):
                self.assertNotIn(case['text'], sent)
        self.assertEqual(result['attempted_requests'], len(ev.model_cases(corpus)))
        self.assertTrue(result['quarantine_passed'])
        self.assertFalse(result['routine_inference_enabled'])
        self.assertEqual(result['scores']['heldout']['cases'], 3)
        self.assertEqual(result['real_website_delta_cases'], 1)
        self.assertFalse(result['real_change_coverage_sufficient'])
        self.assertFalse(result['quality_gate_passed'])
        self.assertEqual(settings['quality_thresholds']['heldout_category_accuracy'], 0.9)
        self.assertEqual(settings['quality_thresholds']['heldout_topic_precision'], 0.9)
        self.assertEqual(settings['quality_thresholds']['heldout_topic_recall'], 0.85)

    def test_v2_input_hash_and_quarantine_annotation_are_fail_closed(self):
        _, corpus = ev.load(self.root, 'v2')
        mutated = copy.deepcopy(corpus)
        attack = next(c for c in mutated['cases'] if c.get('expected_quarantine'))
        attack['expected_quarantine'] = False
        ev.write(self.root / 'tests/fixtures/inference-evaluation-v2.json', mutated)
        config_path = self.root / 'config/inference-evaluation-v2.json'
        settings = json.loads(config_path.read_text())
        settings['corpus_sha256'] = ev.digest(mutated)
        ev.write(config_path, settings)
        with self.assertRaisesRegex(ev.EvaluationError, 'quarantine-annotation-mismatch'):
            ev.load(self.root, 'v2')

    def test_v2_call_and_reservation_caps_are_enforced_before_ledger_write(self):
        config = self.root / 'config/inference-evaluation-v2.json'
        settings = json.loads(config.read_text(encoding='utf-8'))
        settings['limits']['max_model_calls'] = 4
        ev.write(config, settings)
        ledger_path, _ = ev.paths(self.root, 'v2')
        with self.assertRaisesRegex(ev.EvaluationError, 'trial-budget-exhausted'):
            ev.reserve(self.root, 'v2')
        self.assertFalse(ledger_path.exists())
        settings['limits']['max_model_calls'] = 30
        settings['limits']['max_reserved_usd'] = '0.61'
        ev.write(config, settings)
        with self.assertRaisesRegex(ev.EvaluationError, 'v2-limits-invalid'):
            ev.load(self.root, 'v2')

    def test_v2_reservation_counts_unknown_v1_liability_toward_shared_trial_cap(self):
        v1_ledger, _ = ev.paths(self.root, 'v1')
        ev.write(v1_ledger, {'schema_version': 1, 'trial_ceiling_usd': '20', 'experiments': [
            {'experiment_id': 'prior-v1', 'entries': [
                {'reserved_usd': '19.95', 'charged_usd': None}]}]})
        v2_ledger, _ = ev.paths(self.root, 'v2')
        with self.assertRaisesRegex(ev.EvaluationError, 'trial-budget-exhausted'):
            ev.reserve(self.root, 'v2')
        self.assertFalse(v2_ledger.exists())

    def test_v2_undefined_topic_precision_cannot_pass_quality_gate(self):
        _, corpus = ev.load(self.root, 'v2')
        ev.reserve(self.root, 'v2')
        result = ev.execute(self.root, FakeClient(ev.model_cases(corpus), 'omit-topics'), 'v2')
        heldout = result['scores']['heldout']
        self.assertIsNone(heldout['topic_precision'])
        self.assertEqual(heldout['topic_recall'], 0)
        self.assertFalse(result['quality_gate_passed'])

    def test_repeating_a_real_delta_does_not_inflate_real_change_coverage(self):
        _, corpus = ev.load(self.root, 'v2')
        real = next(c for c in corpus['cases'] if c.get('origin') == 'archived-website-delta')
        repeated = {'cases': [{**copy.deepcopy(real), 'source_id': 'copy-' + str(i)} for i in range(5)]}
        self.assertEqual(ev.distinct_real_deltas(repeated), 1)


if __name__ == '__main__':
    unittest.main()
