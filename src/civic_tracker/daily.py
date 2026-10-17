"""Independent daily source refresh. No AI, SMTP, vault access or message delivery."""
import argparse
from datetime import datetime, timezone
import json
import time
from pathlib import Path
from zoneinfo import ZoneInfo
from . import daily_state, daily_federal
from .dashboard_collect import collect, federal_events


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8',newline='\n')
    temporary.replace(path)


def due(plan, state, now, manual=False):
    local = now.astimezone(ZoneInfo(plan['timezone']))
    if not plan['enabled']:return False
    if manual:return True
    return (plan['start_hour'] <= local.hour < plan['catch_up_before_hour']
            and state.get('last_completed_local_date') != local.date().isoformat())


def run(root, now):
    plan=load(root/'config/daily.json'); state=load(root/'data/collection-state.json')
    day=now.astimezone(ZoneInfo(plan['timezone'])).date()
    previous=load(root/'data/dashboard.json'); archives={}; reports={}
    for name, filename in [('Illinois','illinois-index.json'),('Federal','federal-index.json')]:
        old=load(root/'data'/filename)
        started=time.monotonic()
        print(json.dumps({'phase':name,'status':'started'}),flush=True)
        try:
            if day.isoformat()>=plan['review_before']:
                raise RuntimeError('session-review-required')
            if name=='Illinois':
                data, new_state, report=daily_state.refresh(root,old,state.get('illinois',{}),now)
                state['illinois']=new_state
            else:data, report=daily_federal.refresh(root,old,now)
        except Exception as ex:
            data=old
            report={'status':'failed','checked_at':now.isoformat(),'errors':[{'source':name,'error':'session-review-required' if day.isoformat()>=plan['review_before'] else type(ex).__name__}],
                    'limitations':['Previous verified records retained; this source was not refreshed.']}
        report['duration_seconds']=round(time.monotonic()-started,2)
        print(json.dumps({'phase':name,'status':report['status'],'duration_seconds':report['duration_seconds']}),flush=True)
        archives[name]=data; reports[name]=report
        save(root/'data'/filename,data)
    print(json.dumps({'phase':'Calendars','status':'started'}),flush=True)
    calendar_started=time.monotonic()
    try:
        if day.isoformat()>=plan['review_before']:raise RuntimeError('session-review-required')
        collect(root,root/'data/illinois-index.json',root/'data/federal-index.json',day)
        snapshot=load(root/'data/dashboard.json')
        reports['Calendars']={'status':'partial' if snapshot['errors'] else 'ok','checked_at':now.isoformat(),'errors':list(snapshot['errors'])}
        old_members={m['id']:m for m in previous['members']}
        for member in snapshot['members']:
            for key in ('media_reports', 'media_health', 'media_search', 'communications', 'communication_sources', 'communications_checked_at'):
                if key in old_members[member['id']]:member[key]=old_members[member['id']][key]
            source='Illinois' if member['jurisdiction']=='IL' else 'Federal'
            member['activity_coverage']=('Daily FTP listing changes and official floor-vote CSV; committee votes retain historical PDF coverage.' if source=='Illinois'
                else 'Daily Congress.gov sponsorship lists and official floor roll calls; unknown cosponsorship join dates remain undated.')
            if reports[source]['status']!='ok':member['activity_coverage']+=' Source refresh is incomplete; prior verified records are retained.'
            if member['calendar_health'] in ('failed','partial_or_failed'):
                old=old_members[member['id']]
                if not member.get('committees'):member['committees']=old.get('committees',[])
                failed_urls={c['url'] for c in member['committees'] if c.get('health')=='failed'}
                present={m['source_url'] for m in member['meetings']}
                for meeting in old.get('meetings',[]):
                    retain=(member['calendar_health']=='failed' or member['jurisdiction']=='US' or meeting.get('committee_url') in failed_urls)
                    if retain and meeting['source_url'] not in present and day.isoformat()<=meeting['date_local'][:10]<=snapshot['calendar_end']:
                        member['meetings'].append({**meeting,'retained_after_failure':True,'items':[{**bill,'submission_verified':False} for bill in meeting.get('items',[])]})
                member['meetings'].sort(key=lambda m:m['date_local'])
    except Exception as ex:
        snapshot=previous
        reports['Calendars']={'status':'failed','checked_at':now.isoformat(),'errors':[{'source':'Dashboard compilation','error':'session-review-required' if day.isoformat()>=plan['review_before'] else type(ex).__name__}]}
    reports['Calendars']['duration_seconds']=round(time.monotonic()-calendar_started,2)
    print(json.dumps({'phase':'Calendars','status':reports['Calendars']['status'],'duration_seconds':reports['Calendars']['duration_seconds']}),flush=True)
    snapshot['automatic_refresh_enabled']=True
    snapshot['daily_refresh']={'target_time':'01:00 America/Chicago','checked_at':now.isoformat(),
        'status':'ok' if all(r['status']=='ok' for r in reports.values()) else 'partial','sources':reports}
    # Snapshot freshness and collector health are distinct. A failed compilation
    # retains its old as_of and source dates; only the attempt receipt changes.
    save(root/'data/dashboard.json',snapshot)
    state['last_completed_local_date']=day.isoformat(); state['last_attempt_at']=now.isoformat()
    state['last_status']=snapshot['daily_refresh']['status']
    save(root/'data/collection-state.json',state)
    save(root/'data/daily-report.json',snapshot['daily_refresh'])
    size=sum(p.stat().st_size for p in (root/'data').glob('*.json'))
    if size>plan['max_data_bytes']:raise RuntimeError('data-size-budget-exceeded')
    print(json.dumps({'status':state['last_status'],'data_bytes':size,'source_status':{k:v['status'] for k,v in reports.items()}}))


def run_federal(root, now):
    """Recheck only federal facts; preserve calendar, news and budget timestamps."""
    plan = load(root/'config/daily.json')
    day = now.astimezone(ZoneInfo(plan['timezone'])).date()
    if day.isoformat() >= plan['review_before']:
        raise RuntimeError('session-review-required')
    snapshot = load(root/'data/dashboard.json')
    old = load(root/'data/federal-index.json')
    started = time.monotonic()
    archive, report = daily_federal.refresh(root, old, now)
    report['duration_seconds'] = round(time.monotonic() - started, 2)
    for member in snapshot['members']:
        if member['jurisdiction'] != 'US':
            continue
        data, listings = federal_events(archive, member, snapshot['recent_start'], snapshot['as_of'])
        member.update(data)
        member['sponsorship_listings'] = listings
        member['activity_source_checked_at'] = archive['collected_at']
        member['activity_coverage'] = ('Daily Congress.gov sponsorship lists and official floor roll calls; '
            'unknown cosponsorship join dates remain undated.')
        if report['status'] != 'ok':
            member['activity_coverage'] += ' Source refresh is incomplete; prior verified records are retained.'
    health = snapshot['daily_refresh']
    health['sources']['Federal'] = report
    health['status'] = 'ok' if all(r['status'] == 'ok' for r in health['sources'].values()) else 'partial'
    health['source_recheck_at'] = now.isoformat()
    # Retain the old failure receipt as compact evidence, without duplicating the
    # historical source archive or changing the once-per-day collection ledger.
    receipt = {'previous_federal_report': load(root/'data/daily-report.json')['sources']['Federal'],
               'federal_report': report}
    save(root/'data/federal-index.json', archive)
    save(root/'data/dashboard.json', snapshot)
    save(root/'data/daily-report.json', health)
    save(root/'data/federal-recheck-report.json', receipt)
    if sum(p.stat().st_size for p in (root/'data').glob('*.json')) > plan['max_data_bytes']:
        raise RuntimeError('data-size-budget-exceeded')
    print(json.dumps({'phase': 'Federal', 'status': report['status'],
                      'api_attempts': report['api_attempts'], 'vote_requests': report['vote_requests']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['gate','run','federal']);parser.add_argument('--manual',action='store_true')
    args=parser.parse_args();root=Path.cwd();now=datetime.now(timezone.utc)
    if args.command=='gate':
        print('active='+str(due(load(root/'config/daily.json'),load(root/'data/collection-state.json'),now,args.manual)).lower())
    elif args.command=='federal':run_federal(root,now)
    else:run(root,now)


if __name__=='__main__':main()
