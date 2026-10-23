import json
from pathlib import Path
import tempfile
import unittest

from scripts.simulate_growth import simulate


class GrowthSimulationTests(unittest.TestCase):
    def test_report_is_deterministic_and_covers_required_scenarios(self):
        first = simulate()
        second = simulate()
        self.assertEqual(first, second)
        self.assertEqual(set(first['scenarios']), {'unchanged', 'realistic', 'noisy-worst-case'})
        self.assertEqual(first['days'], 365)
        for scenario in first['scenarios'].values():
            self.assertEqual(scenario['news_records_per_member'], 100)
            self.assertGreater(scenario['generated_member_history_pages'], 0)
            self.assertIn('git_history_forecast', scenario['bounded_measurement'])

    def test_realistic_passes_and_noisy_case_identifies_sharding_pressure(self):
        report = simulate()
        self.assertTrue(report['scenarios']['realistic']['pass'])
        noisy = report['scenarios']['noisy-worst-case']
        self.assertFalse(noisy['pass'])
        failed = {key for key, value in noisy['checks'].items() if not value['pass']}
        self.assertTrue({'canonical_json', 'change_ledger', 'base_artifact', 'combined_site'} & failed)
        self.assertIn('No deletion', report['recommendation'])

    def test_output_is_optional_and_does_not_need_repository_data(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'growth.json'
            report = simulate(30)
            path.write_text(json.dumps(report), encoding='utf-8')
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['days'], 30)


if __name__ == '__main__':
    unittest.main()
