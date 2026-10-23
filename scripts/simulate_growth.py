"""Deterministic year-one storage-growth simulation; never collects or mutates data."""
import argparse
import json
from pathlib import Path


LIMITS = {
    'canonical_json': 20_000_000,
    'change_ledger': 10_000_000,
    'error_journal': 96 * 1024,
    'base_artifact': 650_000,
    'member_history': 3_000_000,
    'digest_artifact': 90_000,
    'combined_site': 3_650_000,
}

# These are measured/qualified public-artifact baselines from the current
# project. The simulator deliberately models deltas, not source records.
BASELINES = {
    'canonical_json': 7_043_154,
    'change_ledger': 1_200_000,
    'error_journal': 18_000,
    'base_artifact': 546_175,
    'member_history': 2_410_435,
    'digest_artifact': 27_258,
}

SCENARIOS = {
    'unchanged': {'canonical_per_day': 2_000, 'ledger_per_day': 400,
                  'journal_per_day': 250, 'base_per_day': 20,
                  'history_per_day': 0, 'digest_per_day': 10},
    'realistic': {'canonical_per_day': 25_000, 'ledger_per_day': 7_500,
                  'journal_per_day': 1_200, 'base_per_day': 120,
                  'history_per_day': 950, 'digest_per_day': 120},
    'noisy-worst-case': {'canonical_per_day': 65_000, 'ledger_per_day': 35_000,
                         'journal_per_day': 4_000, 'base_per_day': 450,
                         'history_per_day': 2_400, 'digest_per_day': 300},
}


def _bounded(value, limit):
    # Journal and displayed news/history stores are bounded by their existing
    # implementation caps; canonical and permanent ledgers are not silently
    # truncated. The report makes both the raw forecast and final artifact clear.
    return min(value, limit)


def simulate(days=365):
    if type(days) is not int or not 1 <= days <= 3650:
        raise ValueError('days-bound')
    scenarios = {}
    for name, rates in SCENARIOS.items():
        raw = {
            'canonical_json': BASELINES['canonical_json'] + days * rates['canonical_per_day'],
            'change_ledger': BASELINES['change_ledger'] + days * rates['ledger_per_day'],
            'error_journal': BASELINES['error_journal'] + days * rates['journal_per_day'],
            'base_artifact': BASELINES['base_artifact'] + days * rates['base_per_day'],
            'member_history': BASELINES['member_history'] + days * rates['history_per_day'],
            'digest_artifact': BASELINES['digest_artifact'] + days * rates['digest_per_day'],
        }
        # The journal and rolling member/news display are bounded stores. Keep
        # their forecasted physical size at the implementation cap, while also
        # retaining the pre-cap value for auditability.
        measured = dict(raw)
        measured['error_journal'] = _bounded(raw['error_journal'], LIMITS['error_journal'])
        measured['member_history'] = _bounded(raw['member_history'], LIMITS['member_history'])
        measured['combined_site'] = measured['base_artifact'] + measured['member_history'] + measured['digest_artifact']
        measured['git_history_forecast'] = days * sum(rates.values())
        checks = {key: {'bytes': measured[key], 'limit': limit, 'pass': measured[key] <= limit}
                  for key, limit in LIMITS.items()}
        raw_checks = {key: {'bytes': raw[key], 'limit': limit, 'would_exceed_without_bound': raw[key] > limit}
                      for key, limit in LIMITS.items() if key in raw}
        scenarios[name] = {
            'days': days,
            'assumptions': rates,
            'generated_member_history_pages': 5 * (2 + 20),
            'news_records_per_member': 100,
            'raw_forecast_bytes': raw,
            'bounded_measurement': measured,
            'checks': checks,
            'raw_bound_warnings': raw_checks,
            'pass': all(item['pass'] for item in checks.values()),
        }
    return {
        'schema_version': 1,
        'task': 'P05',
        'method': 'Synthetic offline forecast; no source, model, network, storage service, or production-data writes.',
        'days': days,
        'limits_bytes': LIMITS,
        'baselines_bytes': BASELINES,
        'assumption_notes': [
            'Unchanged runs retain bounded displays but still add small receipts.',
            'Realistic and noisy rates are synthetic byte deltas, not observed legislative volume.',
            'Journal and rolling member/history displays are measured at their existing caps; permanent canonical and change-ledger forecasts are never truncated.',
            'Git history is forecast separately because it has no live-file cap.',
        ],
        'scenarios': scenarios,
        'overall_pass': all(item['pass'] for item in scenarios.values()),
        'recommendation': 'No deletion is proposed. If a scenario fails, shard or window the affected display and preserve permanent source/financial history.'
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=365)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = simulate(args.days)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'task': 'P05', 'days': args.days, 'overall_pass': report['overall_pass'],
                      'scenarios': {key: value['pass'] for key, value in report['scenarios'].items()}}))


if __name__ == '__main__':
    main()
