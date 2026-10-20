"""Manual Illinois/calendar recovery; no model, email or federal API requests."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
from .daily import load, save
from .daily_state import refresh
from .dashboard_collect import collect
from .http import source_error
from .usage import apply as update_usage


def run(root, now):
    plan=load(root/'config/daily.json')
    day=now.astimezone(ZoneInfo(plan['timezone'])).date()
    if day.isoformat()>=plan['review_before']:raise RuntimeError('session-review-required')
    old=load(root/'data/dashboard.json'); ledger=load(root/'data/collection-state.json')
    archive, state, report=refresh(root,load(root/'data/illinois-index.json'),ledger.get('illinois',{}),now)
    ledger['illinois']=state
    save(root/'data/illinois-index.json',archive)
    save(root/'data/collection-state.json',ledger)
    prior_health=old['daily_refresh']
    try:
        collect(root,root/'data/illinois-index.json',root/'data/federal-index.json',day)
        snapshot=load(root/'data/dashboard.json')
        calendar={'status':'partial' if snapshot['errors'] else 'ok','checked_at':now.isoformat(),'errors':snapshot['errors']}
        old_members={m['id']:m for m in old['members']}
        for member in snapshot['members']:
            previous=old_members[member['id']]
            for key in ('media_reports','media_health','media_search','communications','communication_sources','communications_checked_at'):
                if key in previous:member[key]=previous[key]
            member['activity_coverage']=previous['activity_coverage']
        from .hearing_changes import retain_failed
        retain_failed(snapshot, old, day.isoformat())
    except Exception as ex:
        snapshot=old
        from .hearing_changes import clear_slips
        clear_slips(snapshot)
        calendar={'status':'failed','checked_at':now.isoformat(),'errors':[{'source':'Calendar compilation','error':source_error(ex)}]}
    sources={**prior_health['sources'],'Illinois':report,'Calendars':calendar}
    snapshot['daily_refresh']={**prior_health,'source_recheck_at':now.isoformat(),
        'status':'ok' if all(r['status']=='ok' for r in sources.values()) else 'partial','sources':sources}
    snapshot['automatic_refresh_enabled']=True
    if 'inference_usage' in old:snapshot['inference_usage']=old['inference_usage']
    save(root/'data/dashboard.json',snapshot)
    save(root/'data/daily-report.json',snapshot['daily_refresh'])
    save(root/'data/illinois-recovery-report.json',{'previous_health':prior_health,'recovered_sources':{'Illinois':report,'Calendars':calendar}})
    update_usage(root,now)
    if sum(p.stat().st_size for p in (root/'data').glob('*.json'))>plan['max_data_bytes']:raise RuntimeError('data-size-budget-exceeded')
    print(json.dumps({'status':snapshot['daily_refresh']['status'],'rechecked':{k:sources[k]['status'] for k in ('Illinois','Calendars')}}))


if __name__=='__main__':run(Path.cwd(),datetime.now(timezone.utc))
