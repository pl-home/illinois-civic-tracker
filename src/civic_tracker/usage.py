"""One deterministic source for project inference spend, reservations and calendar budgets."""
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import json

from . import inference_eval as ev

CHICAGO=ZoneInfo('America/Chicago')


def load(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def local_day(value):
    try:
        stamp=datetime.fromisoformat(value)
        return stamp.astimezone(CHICAGO).date() if stamp.tzinfo else None
    except (TypeError,ValueError):
        return None


def entries(root, media=None):
    for version in ('v1','v2'):
        ledger=load(ev.paths(root,version)[0],{'experiments':[]})
        for run in ledger.get('experiments',[]):
            for entry in run.get('entries',[]):
                charge=ev.money(entry['charged_usd']) if entry.get('charged_usd') is not None else None
                if entry.get('status')=='quarantined-deterministically' and not charge:
                    continue
                day=local_day(entry.get('attempted_at') or run.get('reserved_at') or run.get('started_at'))
                reserve=ev.money(entry['reserved_usd']) if charge is None else Decimal(0)
                yield {'day':day,'charge':charge,'reserve':reserve,'media':False}
    if media is None:media=load(root/'data/media-inference-ledger.json',{'batches':[]})
    for batch in media.get('batches',[]):
        day=local_day(batch.get('attempted_at'))
        if day is None:
            try:day=date.fromisoformat(batch.get('day'))
            except (TypeError,ValueError):pass
        charge=ev.money(batch['charged_usd']) if batch.get('charged_usd') is not None else None
        yield {'day':day,'charge':charge,'reserve':ev.money(batch['reserved_usd']),'media':True}
    for filename in ('pdf-extraction-ledger.json','rollcall-evaluation-ledger.json','rollcall-diagnostics-v2-ledger.json'):
        for entry in load(root/'data'/filename,{'entries':[]}).get('entries',[]):
            yield {'day':local_day(entry.get('attempted_at')),
                'charge':ev.money(entry['charged_usd']) if entry.get('charged_usd') is not None else None,
                'reserve':ev.money(entry['reserved_usd']),'media':False}


def total(rows):
    charged=sum((row['charge'] for row in rows if row['charge'] is not None),Decimal(0))
    held=sum((row['reserve'] for row in rows if row['charge'] is None),Decimal(0))
    return {'charged_usd':str(charged),'reserved_usd':str(held),'liability_usd':str(charged+held),
        'unsettled_requests':sum(row['charge'] is None for row in rows),
        'media_reservations':sum(row['media'] for row in rows),
        'undated_entries':sum(row['day'] is None for row in rows)}


def periods(root, today, media=None):
    """Unknown dates count conservatively in each current window; ledgers never reset."""
    if isinstance(today,str):today=date.fromisoformat(today)
    start=today-timedelta(days=today.weekday())
    end=start+timedelta(days=7)
    rows=list(entries(root,media))
    return {'day':total([r for r in rows if r['day'] is None or r['day']==today]),
        'week':total([r for r in rows if r['day'] is None or start<=r['day']<end]),
        'lifetime':total(rows),'week_start':start.isoformat(),'week_end':(end-timedelta(days=1)).isoformat()}


def summary(root, now):
    if now.tzinfo is None:raise ValueError('timezone-required')
    today=now.astimezone(CHICAGO).date()
    result=periods(root,today)
    config=load(root/'config/media.json',{})['inference']
    for key,field in (('day','daily_cap_usd'),('week','weekly_cap_usd'),('lifetime','lifetime_cap_usd')):
        cap=ev.money(config[field]);used=ev.money(result[key]['liability_usd'])
        result[key].update(limit_usd=str(cap),remaining_usd=str(max(Decimal(0),cap-used)),
            used_percent=str(used*100/cap if cap else Decimal(0)))
    result.update(schema_version=1,as_of=now.isoformat(),local_date=today.isoformat(),
        timezone='America/Chicago',week_definition='Monday through Sunday',
        scope='Tracker inference only, including earlier evaluations; excludes unrelated OpenRouter account use.')
    return result


def apply(root, now):
    from .media import save
    report=summary(root,now)
    snapshot=load(root/'data/dashboard.json',{})
    snapshot['inference_usage']=report
    save(root/'data/dashboard.json',snapshot)
    save(root/'data/inference-usage.json',report)
    return report
