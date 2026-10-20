"""Manual official calendar-only acceptance/recovery. No PDFs, APIs or models."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .daily import load, save
from .dashboard_collect import collect
from .hearing_changes import retain_failed, clear_slips
from .http import source_error


def run(root, now):
    plan = load(root/'config/daily.json')
    day = now.astimezone(ZoneInfo(plan['timezone'])).date()
    if day.isoformat() >= plan['review_before']: raise RuntimeError('session-review-required')
    old = load(root/'data/dashboard.json')
    try:
        collect(root, root/'data/illinois-index.json', root/'data/federal-index.json', day)
        snapshot = load(root/'data/dashboard.json')
        report = {'status': 'partial' if snapshot['errors'] else 'ok', 'checked_at': now.isoformat(), 'errors': snapshot['errors']}
        prior = {m['id']: m for m in old['members']}
        for member in snapshot['members']:
            for key in ('events','sponsorship_listings','activity_source_checked_at','activity_coverage','latest_vote_date',
                        'media_reports','media_health','media_search','communications','communication_sources','communications_checked_at'):
                if key in prior[member['id']]: member[key] = prior[member['id']][key]
        retain_failed(snapshot, old, day.isoformat())
    except Exception as error:
        snapshot = old; clear_slips(snapshot)
        report = {'status': 'failed', 'checked_at': now.isoformat(), 'errors': [{'source': 'Calendar compilation', 'error': source_error(error)}]}
    sources = {**old.get('daily_refresh', {}).get('sources', {}), 'Calendars': report}
    snapshot['daily_refresh'] = {**old.get('daily_refresh', {}), 'sources': sources,
        'source_recheck_at': now.isoformat(), 'status': 'ok' if all(s['status'] == 'ok' for s in sources.values()) else 'partial'}
    snapshot['automatic_refresh_enabled'] = old.get('automatic_refresh_enabled', False)
    if 'inference_usage' in old: snapshot['inference_usage'] = old['inference_usage']
    save(root/'data/dashboard.json', snapshot)
    save(root/'data/daily-report.json', snapshot['daily_refresh'])
    save(root/'data/calendar-refresh-report.json', report)
    if sum(p.stat().st_size for p in (root/'data').glob('*.json')) > plan['max_data_bytes']: raise RuntimeError('data-size-budget-exceeded')
    print({'calendar_status': report['status'], 'source_errors': len(report['errors']), 'model_calls': 0}, flush=True)


if __name__ == '__main__': run(Path.cwd(), datetime.now(timezone.utc))
