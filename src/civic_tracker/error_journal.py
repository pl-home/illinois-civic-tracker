"""Bounded public error history. Stdlib only; no network, secrets or model calls."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

MAX_BYTES=96*1024
MAX_INCIDENTS=64
MAX_EVENTS=128
MAX_SEEN=128
DAYS=90
WORKFLOWS={'daily','federal','illinois','media','parties','pdf','rollcall','openrouter-health','journal'}
STAGES={'source-health','model-http','model-json','model-status','model-validation','workflow',
        'dependencies','tests','collector','changes','reserve','model','privacy','build','persist','journal-input'}
CODES=set('''RuntimeError ValueError HTTPError URLError TimeoutError OSError KeyError JSONDecodeError
SSLCertVerificationError ConnectionError workflow-failed model-abstained output-schema evidence-schema
evidence-page evidence-size evidence-quote committee-mismatch measure-mismatch motion-mismatch member-schema
unknown-vote-code wrong-member member-cell-ambiguous member-cell-binding vote-mismatch tally-schema tally-value
tally-quote-binding tally-gold-mismatch named-roster-tally-mismatch routing-mismatch cost-over-reservation
invalid-response response-bound field-schema page-evidence field-size quote-evidence measure-missing
feed-unavailable-or-invalid session-review-required daily-file-bound-pending source-hash-mismatch
native-hash-mismatch native-text-hash-mismatch batch-hash-mismatch shared-budget-exhausted missing-openrouter-key
request-outcome-unknown invalid-output prepared-work-expired response-cost-exceeds-reservation
no-compliant-endpoint request-failed unresolved-budget-reservation'''.split())
CODES.update('''source-unavailable preflight-failed approved-endpoint-unavailable case-count-bound duplicate-case-id
duplicate-output-id endpoint-extra-fee-rejected input-bound-exceeded invalid-batch-size-or-ids invalid-billing-metadata
invalid-case-identity invalid-case-schema invalid-case-text invalid-model-response invalid-output-id invalid-output-json
invalid-output-schema invalid-output-value media-config-invalid media-config-mismatch media-config-missing
missing-output-id reservation-too-small timezone-required model-call-stopped UnicodeDecodeError'''.split())
CODES.add('change-quality-withheld')
CODES.update({'party-content-structure','party-projection-bound','party-sensitive-content','party-unapproved-url',
              'party-robots-unavailable','party-robots-disallow','party-crawl-delay-review','party-response-bound',
              'party-asset-format','party-content-type','party-content-shrink-review',
              'party-pending-change-bound','party-parser-pending-review'})
CODES.update({'hearing-recheck-bound','hearing-detail-bound','hearing-agenda-bound',
              'hearing-date-conflict','hearing-status-conflict','hearing-committee-mismatch','ambiguous-hearing-identity'})
HOSTS={'ilga.gov','ftp.ilga.gov','my.ilga.gov','api.congress.gov','clerk.house.gov','www.senate.gov','news.google.com','openrouter.ai'}
HOSTS.update({'repfritts.com','senatorli.com','lahood.house.gov','durbin.senate.gov','duckworth.senate.gov','leecodemocrats.com','leecountyilgop.org','capitolfax.com'})
FILES={'daily':'data/daily-report.json','media-source':'data/media-state.json','media-model':'data/media-inference-report.json',
       'pdf':'data/pdf-extraction-report.json','rollcall':'data/rollcall-evaluation-report.json','health':'data/openrouter-health.json',
       'communications':'data/communications-state.json','media-ledger':'data/media-inference-ledger.json',
       'rollcall-v2':'data/rollcall-diagnostics-v2-report.json', 'change-quality':'data/change-quality-report.json',
       'parties':'data/party-state.json', 'mentions':'data/mentions-state.json'}
LEDGERS={p:p for p in ('data/pdf-extraction-ledger.json','data/rollcall-evaluation-ledger.json',
                      'data/rollcall-diagnostics-v2-ledger.json')}
PATHS=(r'/documents/reports/static/104MemberVotes\.csv',r'/(?:House|Senate)/Members/Details/\d{1,7}',
       r'/(?:House|Senate)/hearings/details/\d{1,7}/\d{1,7}',r'/(?:House|Senate)/Committees/(?:Hearings|Members)/\d{1,7}',
       r'/Documents/legislation/votehistory/104/(?:house|senate)/committeevotes/10400[A-Z0-9_]{5,45}\.pdf',
       r'/Legislation/104/BillStatus/XML/',r'/Votes/MemberVotes',r'/api/v1/(?:key|chat/completions)')
ENUMS={
 'envelope_shape':{'object','array','null','boolean','number','string'},
 'content_shape':{'object','array','null','boolean','number','string'},
 'json_shape':{'object','array','null','boolean','number','string','not-captured'},
 'status_shape':{'object','array','null','boolean','number','string'},
 'json_parse':{'ok','invalid','not-string','over-bound','not-captured'},
 'model_status':{'extracted','unverified','verified','ok','success','complete','failed','error','unknown','other','not-captured'},
 'finish_reason':{'stop','length','content_filter','tool_calls','error','eos','unknown','other','not-captured'},
 'validation_stage':STAGES,
 'evidence_assessment':{'matched-reference','rejected','not-run'},
 'http_json':{'ok','unavailable','over-bound'},
 'provider_error_type':{'rate_limit_exceeded','context_length_exceeded','invalid_request','authentication','permission_denied','server','provider_unavailable','content_filter','other'},
 'time_basis':{'source','commit'},
}
BOOLS={'provider_match','model_match','refusal_present','reasoning_present','code_fence','status_exact',
       'diagnostics_available','parser_annotations_present'}
NUMBERS={'prompt_tokens','completion_tokens','total_tokens','content_bytes','status_chars','json_error_line',
         'json_error_column','unexpected_field_count','http_status'}
HASHES={'source_sha256','native_sha256','prompt_sha256','config_sha256','status_sha256'}


def hashed(value):return hashlib.sha256(str(value).encode()).hexdigest()[:20]
def stamp(value):
    try:
        dt=datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt.astimezone(timezone.utc) if dt.tzinfo else None
    except (AttributeError,ValueError,TypeError):return None
def packed(value):return json.dumps(value,ensure_ascii=True,separators=(',',':'),sort_keys=True).encode()
def read(path):return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
def read_report(path):
    try:
        value=read(path)
        if value is None:return None
        if not isinstance(value,dict):return {'_input_error':'invalid-output-schema'}
        for key in ('sources','members'):
            if key in value and not isinstance(value[key],dict):return {'_input_error':'invalid-output-schema'}
        for key in ('cases','entries','batches','errors'):
            if key in value and not isinstance(value[key],list):return {'_input_error':'invalid-output-schema'}
        return value
    except (json.JSONDecodeError,UnicodeDecodeError,OSError) as error:return {'_input_error':type(error).__name__}
def safe_code(value):return value if isinstance(value,str) and (value in CODES or re.fullmatch(r'HTTP_[1-5]\d\d',value)) else 'unclassified-error'
def safe_run(value):
    return value if isinstance(value,str) and re.fullmatch(r'(?:\d{1,20}-\d{1,3}|history-[0-9a-f]{12}|local-\d{8}T\d{6}Z)',value) else 'redacted'
def safe_reference(value):
    if not isinstance(value,dict):return {}
    out={}
    if value.get('file') in FILES.values():out['file']=value['file']
    if value.get('workflow') in WORKFLOWS:out['workflow']=value['workflow']
    if isinstance(value.get('commit'),str) and re.fullmatch(r'[0-9a-f]{40}',value['commit']):out['commit']=value['commit']
    return out


def source_ref(value):
    value=value if isinstance(value,str) else ''
    try:
        p=urlsplit(value)
        if p.scheme=='https' and p.hostname in HOSTS:
            # User info, query and fragment are never retained or fingerprinted.
            identity=p.hostname+p.path
            path=p.path if any(re.fullmatch(pattern,p.path,re.I) for pattern in PATHS) else ''
            return {'id':hashed(identity),'label':'https://'+p.hostname+path}
    except ValueError:pass
    fixed=WORKFLOWS|{'Illinois','Federal','Calendars','Illinois FTP','Dashboard compilation','fritts','arellano','lahood','durbin','duckworth'}
    label=value if value in fixed or re.fullmatch(r'[A-Z]\d{6}:(?:sponsored|cosponsored)',value) else 'source-'+hashed(value)
    return {'id':hashed(value),'label':label}


def diagnostics(value):
    if not isinstance(value,dict):return {}
    out={}
    for key,v in value.items():
        if key in {'committee_check','measure_check','motion_check','member_check','tally_check'}:
            out[key]='matched-reference' if v=='matched-reference' else safe_code(v)
            continue
        if key in ENUMS and isinstance(v,str) and v in ENUMS[key]:out[key]=v
        elif key in BOOLS and type(v) is bool:out[key]=v
        elif key in NUMBERS and type(v) is int and 0<=v<=10_000_000:out[key]=v
        elif key in HASHES and isinstance(v,str) and re.fullmatch(r'[0-9a-f]{64}',v):out[key]=v
        elif key=='response_id' and isinstance(v,str) and re.fullmatch(r'gen-\d{8,16}-[A-Za-z0-9]{1,50}',v):out[key]=v
        elif key=='missing_fields' and isinstance(v,list):out[key]=sorted({s for s in v if isinstance(s,str)}&{'status','committee','measure','motion','member_vote','tally','document_title','decisions'})
        elif key=='evidence_failure_code':out[key]=safe_code(v)
    return out


def empty():return {'schema_version':1,'incidents':[],'events':[],'seen':[],'scopes':{},'runs':[],
    'evicted_incidents':0,'evicted_open_incidents':0,'evicted_events':0,'late_observations':0}


def validate_public(data):
    """Reject unexpected persisted fields as well as unsafe newly supplied metadata."""
    top=set(empty())|{'updated_at','limits','bootstrap_complete'}
    if not isinstance(data,dict) or set(data)-top or data.get('schema_version')!=1:raise ValueError('journal-schema')
    for key in ('evicted_incidents','evicted_open_incidents','evicted_events','late_observations'):
        if type(data.get(key)) is not int or data[key]<0:raise ValueError('journal-counter')
    if 'updated_at' in data and stamp(data['updated_at']) is None:raise ValueError('journal-time')
    if 'bootstrap_complete' in data and type(data['bootstrap_complete']) is not bool:raise ValueError('journal-schema')
    if 'limits' in data and data['limits']!={'bytes':MAX_BYTES,'incidents':MAX_INCIDENTS,'events':MAX_EVENTS,'days':DAYS}:raise ValueError('journal-limits')
    incident_keys={'id','scope','collector','source','code','stage','first_seen','last_seen','occurrences','status',
                   'run_id','evidence','diagnostics','resolved_at','recovery_run_id'}
    def identity(value):return isinstance(value,str) and bool(re.fullmatch(r'[0-9a-f]{20}',value))
    def scope(value):return isinstance(value,str) and ':' in value and value.split(':',1)[0] in set(FILES)|{'workflow'} and identity(value.split(':',1)[1])
    def source(value):return isinstance(value,str) and (bool(re.fullmatch(r'source-[0-9a-f]{20}',value)) or source_ref(value)['label']==value)
    for incident in data.get('incidents',[]):
        if not isinstance(incident,dict) or set(incident)-incident_keys:raise ValueError('journal-incident-schema')
        if not identity(incident.get('id')) or not scope(incident.get('scope')) or not source(incident.get('source')):raise ValueError('journal-identity')
        if incident.get('collector') not in set(FILES)|{'workflow'} or incident.get('stage') not in STAGES or safe_code(incident.get('code'))!=incident.get('code'):raise ValueError('journal-code')
        if incident.get('status') not in ('open','resolved') or type(incident.get('occurrences')) is not int or incident['occurrences']<0:raise ValueError('journal-state')
        if safe_reference(incident.get('evidence'))!=incident.get('evidence') or diagnostics(incident.get('diagnostics'))!=incident.get('diagnostics'):raise ValueError('journal-diagnostics')
        for field in ('run_id','recovery_run_id'):
            if field in incident and safe_run(incident[field])!=incident[field]:raise ValueError('journal-run')
        for field in ('first_seen','last_seen','resolved_at'):
            if field in incident and stamp(incident[field]) is None:raise ValueError('journal-time')
    for event in data.get('events',[]):
        if set(event)!={'at','kind','incident_id','run_id'} or event['kind'] not in ('opened','repeated','reopened','recovered') or not identity(event['incident_id']) or safe_run(event['run_id'])!=event['run_id'] or stamp(event['at']) is None:raise ValueError('journal-event')
    for key,value in data.get('scopes',{}).items():
        if not scope(key) or stamp(value) is None:raise ValueError('journal-scope')
    if any(not identity(value) for value in data.get('seen',[])):raise ValueError('journal-seen')
    for run in data.get('runs',[]):
        if set(run)!={'run_id','workflow','at','status'} or run['workflow'] not in WORKFLOWS or safe_run(run['run_id'])!=run['run_id'] or stamp(run['at']) is None or run['status'] not in ('success','failure','cancelled','unknown'):raise ValueError('journal-run')


class Journal:
    def __init__(self,root,now):
        self.root=Path(root);self.now=now.astimezone(timezone.utc);self.path=self.root/'data/error-journal.json'
        self.data=read(self.path) if self.path.exists() else empty()
        validate_public(self.data)

    def observe(self,collector,source,when,errors,healthy,run_id,reference,detail=None,stage='source-health',group=None):
        if collector not in set(FILES)|{'workflow'}:raise ValueError('journal-collector')
        run_id=safe_run(run_id);reference=safe_reference(reference)
        when=stamp(when)
        if when is None or when>self.now+timedelta(minutes=5):return
        ref=source_ref(source);scope=collector+':'+source_ref(group or source)['id'];stage=stage if stage in STAGES else 'source-health'
        failures=[(safe_code('HTTP_'+str(e) if type(e) is int and 100<=e<=599 else e),hashed(e)) for e in errors]
        obs=hashed(packed([scope,ref['id'],when.isoformat(),failures,bool(healthy)]))
        if obs in self.data['seen']:return
        self.data['seen'].append(obs)
        previous=stamp(self.data['scopes'].get(scope,''))
        if previous and when<previous:self.data['late_observations']+=1;return
        self.data['scopes'][scope]=when.isoformat()
        info=diagnostics(detail);ids=set()
        for code,raw_hash in failures:
            ident=hashed(scope+'|'+ref['id']+'|'+stage+'|'+code+'|'+raw_hash);ids.add(ident)
            incident=next((i for i in self.data['incidents'] if i['id']==ident),None)
            # The small receipt cache can roll over while an incident remains.
            # A replay of the same dated failure is never a fresh occurrence.
            if incident is not None and when<=stamp(incident['last_seen']):continue
            if incident is None:
                incident={'id':ident,'scope':scope,'collector':collector,'source':ref['label'],'code':code,'stage':stage,
                    'first_seen':when.isoformat(),'last_seen':when.isoformat(),'occurrences':0,'status':'open'}
                self.data['incidents'].append(incident);kind='opened'
            else:kind='reopened' if incident['status']=='resolved' else 'repeated'
            incident.update(last_seen=when.isoformat(),occurrences=incident['occurrences']+1,status='open',
                            run_id=run_id,evidence=reference,diagnostics=info)
            self.data['events'].append({'at':when.isoformat(),'kind':kind,'incident_id':ident,'run_id':run_id})
        # Only a complete successful observation resolves previous failures.
        if healthy:
            for incident in self.data['incidents']:
                if incident['scope']==scope and incident['status']=='open' and incident['id'] not in ids:
                    incident.update(status='resolved',resolved_at=when.isoformat(),recovery_run_id=run_id)
                    self.data['events'].append({'at':when.isoformat(),'kind':'recovered','incident_id':incident['id'],'run_id':run_id})

    def finish(self):
        data=self.data;cutoff=self.now-timedelta(days=DAYS)
        kept=[i for i in data['incidents'] if i['status']=='open' or max(stamp(i['last_seen']),stamp(i.get('resolved_at',i['last_seen'])))>=cutoff]
        data['evicted_incidents']+=len(data['incidents'])-len(kept);data['incidents']=kept
        events=sorted([e for e in data['events'] if stamp(e['at'])>=cutoff],key=lambda e:e['at'])
        data['evicted_events']+=len(data['events'])-min(len(events),MAX_EVENTS);data['events']=events[-MAX_EVENTS:]
        data['seen']=data['seen'][-MAX_SEEN:];data['runs']=data['runs'][-32:]
        # Keep scope watermarks bounded too; old receipts cannot silently become fresh checks.
        scopes=sorted(data['scopes'].items(),key=lambda item:item[1])[-MAX_SEEN:];data['scopes']=dict(scopes)
        def evict():
            oldest=min(data['incidents'],key=lambda i:(i['status']=='open',i['last_seen']))
            data['incidents'].remove(oldest);data['evicted_incidents']+=1
            data['evicted_open_incidents']+=oldest['status']=='open'
        while len(data['incidents'])>MAX_INCIDENTS:evict()
        data.update(updated_at=self.now.isoformat(),limits={'bytes':MAX_BYTES,'incidents':MAX_INCIDENTS,'events':MAX_EVENTS,'days':DAYS})
        while len(packed(data))+1>MAX_BYTES:
            if data['events']:data['events'].pop(0);data['evicted_events']+=1
            elif data['incidents']:evict()
            elif data['seen']:data['seen'].pop(0)
            else:raise ValueError('journal-bound')
        raw=packed(data)+b'\n'
        validate_public(data)
        for name in ('OPENROUTER_API_KEY','CONGRESS_API_KEY','CONGRESSGOV_API','GMAIL_APP_PASSWORD','GMAIL_USER','DIGEST_TO','GH_TOKEN','GITHUB_TOKEN'):
            secret=os.environ.get(name,'')
            if len(secret)>=8 and secret.encode() in raw:raise ValueError('journal-sensitive-content')
        self.path.parent.mkdir(parents=True,exist_ok=True);temp=self.path.with_suffix('.tmp');temp.write_bytes(raw);temp.replace(self.path)
        return len(raw)


def ingest(journal,files,commit=None,commit_time=None):
    ref=lambda file:{'file':FILES[file],**({'commit':commit} if commit else {})}
    run='history-'+commit[:12] if commit else run_id(journal.now)
    for kind, entries in [('parties', (files.get('parties') or {}).get('pages', {})),
                          ('mentions', (files.get('mentions') or {}).get('sources', {}))]:
        for source, report in entries.items():
            journal.observe(kind, report.get('url', source), report.get('checked_at') or commit_time,
                [report.get('error', 'source-unavailable')] if report.get('status') != 'ok' else [],
                report.get('status') == 'ok', run, ref(kind), stage='source-health')
    quality=files.get('change-quality') or {}
    if quality:
        # Bounded codes only, never source bodies, model answers or fact text.
        journal.observe('change-quality','Stage A quality',quality.get('checked_at') or commit_time,
            ['change-quality-withheld'] if quality.get('status')!='ok' else [],quality.get('status')=='ok',run,ref('change-quality'),
            stage='source-health')
    daily=files.get('daily') or {}
    for name,report in daily.get('sources',{}).items():
        if name not in ('Illinois','Federal','Calendars') or not isinstance(report,dict):continue
        when=report.get('checked_at') or daily.get('checked_at') or commit_time
        # Scope-wide report errors retain source-specific detail in separate incidents.
        errors=report.get('errors',[])
        for error in errors:
            if isinstance(error,dict):journal.observe('daily',error.get('source',name),when,[error.get('error','unclassified-error')],False,run,
                ref('daily'),detail={'diagnostics_available':True},stage='source-health',group=name)
        if not errors:journal.observe('daily',name,when,[],report.get('status')=='ok',run,ref('daily'),group=name)
    media=files.get('media-source') or {}
    for member,report in media.get('members',{}).items():
        if member not in ('fritts','arellano','lahood','durbin','duckworth') or not isinstance(report,dict):continue
        journal.observe('media-source',member,report.get('checked_at') or media.get('checked_at') or commit_time,
            [report.get('error','feed-unavailable-or-invalid')] if report.get('status')=='failed' else [],report.get('status')=='ok',run,ref('media-source'))
    communications=files.get('communications') or {}
    for source,report in communications.get('sources',{}).items():
        if not isinstance(report,dict):continue
        journal.observe('communications',report.get('source_url') or source,report.get('checked_at') or communications.get('checked_at') or commit_time,
            [report.get('error','source-unavailable')] if report.get('status')=='failed' else [],report.get('status')=='ok',run,ref('communications'))
    for batch in (files.get('media-ledger') or {}).get('batches',[])[-64:]:
        if not batch.get('attempted_at'):continue
        good=batch.get('status')=='valid';detail={**(batch.get('diagnostics') or {}),**(batch.get('usage') or {})}
        journal.observe('media-model',batch.get('batch_hash','media-model'),batch['attempted_at'],
            [] if good else [batch.get('error','request-outcome-unknown')],good,run,ref('media-ledger'),detail,stage='model-validation')
    model=files.get('media-model') or {}
    for error in model.get('errors',[]):
        code=error.get('code','unclassified-error') if isinstance(error,dict) else error
        journal.observe('media-model','media',model.get('checked_at') or media.get('checked_at') or commit_time,
            [code],False,run,ref('media-model'),stage='model-validation')
    if not model.get('errors'):journal.observe('media-model','media',model.get('checked_at') or media.get('checked_at') or commit_time,
        [],model.get('status')=='complete',run,ref('media-model'),stage='model-validation')
    health=files.get('health') or {}
    for component in ('authentication','endpoint'):
        result=health.get(component) or {};code=result.get('error')
        if component=='endpoint' and result.get('present') is False:code='approved-endpoint-unavailable'
        journal.observe('health',component,health.get('checked_at') or commit_time,[code] if code else [],
            result.get('status')=='ok' if component=='authentication' else result.get('present') is True,run,ref('health'))
    for collector,ledger_file in [('pdf','data/pdf-extraction-ledger.json'),('rollcall','data/rollcall-evaluation-ledger.json'),
                                  ('rollcall-v2','data/rollcall-diagnostics-v2-ledger.json')]:
        report=files.get(collector) or {};ledger=files.get(ledger_file) or {}
        entries=ledger.get('entries',[])
        is_rollcall=collector in ('rollcall','rollcall-v2')
        rows=report.get('cases',[]) if is_rollcall else ([report] if report.get('trial_id') else [])
        for row in rows:
            if not isinstance(row,dict) or row.get('status') in ('reserved','not-attempted'):continue
            key=row.get('case_id') if is_rollcall else row.get('trial_id')
            entry=next((e for e in entries if e.get('case_id',e.get('trial_id'))==key),{})
            when=row.get('attempted_at') or entry.get('attempted_at') or commit_time
            detail={**(row.get('diagnostics') or {}),'diagnostics_available':bool(row.get('diagnostics'))}
            for field in ('response_id','prompt_tokens','completion_tokens'): 
                if field in row:detail[field]=row[field]
            for field in ('native_sha256','prompt_sha256','config_sha256'):
                if field in entry or field in ledger:detail[field]=entry.get(field,ledger.get(field))
            detail['source_sha256']=row.get('source_sha256',row.get('sha256'))
            code=row.get('error');good=row.get('status') in ('validated','valid-extraction')
            stage='model-status' if code=='model-abstained' else 'model-http' if str(code).startswith('HTTP') else 'model-validation'
            if not detail['diagnostics_available']:detail.update(model_status='not-captured',finish_reason='not-captured',json_parse='not-captured')
            journal.observe(collector,row.get('source_url') or key,when,[code or 'request-outcome-unknown'] if not good else [],good,run,ref(collector),detail,stage,group=key)


def run_id(now):
    value=os.environ.get('GITHUB_RUN_ID','');attempt=os.environ.get('GITHUB_RUN_ATTEMPT','1')
    return value+'-'+attempt if value.isdigit() and len(value)<=20 and attempt.isdigit() and len(attempt)<=3 else 'local-'+now.strftime('%Y%m%dT%H%M%SZ')


def collect(root,now,workflow,job_status,bootstrap=False):
    journal=Journal(root,now)
    if bootstrap and not journal.data.get('bootstrap_complete'):
        result=subprocess.run(['git','log','-40','--format=%H %cI','--',*FILES.values()],cwd=root,capture_output=True,text=True,check=True)
        for line in reversed(result.stdout.splitlines()):
            commit,when=line.split(' ',1)
            if not re.fullmatch(r'[0-9a-f]{40}',commit) or not stamp(when) or stamp(when)<now-timedelta(days=DAYS):continue
            snapshots={}
            for key,path in {**FILES,**LEDGERS}.items():
                result=subprocess.run(['git','show',commit+':'+path],cwd=root,capture_output=True)
                if result.returncode==0:
                    try:snapshots[key]=json.loads(result.stdout)
                    except (ValueError,UnicodeError):pass
            ingest(journal,snapshots,commit,when)
        journal.data['bootstrap_complete']=True
    files={}
    for key,path in {**FILES,**LEDGERS}.items():
        value=read_report(Path(root)/path)
        if isinstance(value,dict) and '_input_error' in value:
            journal.observe('workflow',key,now.isoformat(),[value['_input_error']],False,run_id(now),{'file':path},stage='journal-input',group='journal-input:'+key)
            files[key]=None
        else:
            files[key]=value
            scope='workflow:'+source_ref('journal-input:'+key)['id']
            if value is not None and any(i['scope']==scope and i['status']=='open' for i in journal.data['incidents']):
                journal.observe('workflow',key,now.isoformat(),[],True,run_id(now),{'file':path},stage='journal-input',group='journal-input:'+key)
    ingest(journal,files)
    stage='workflow'
    for name in ('dependencies','tests','collector','changes','reserve','model','privacy','build','persist'):
        if os.environ.get('JOURNAL_'+name.upper())=='failure':stage=name;break
    status=job_status if job_status in ('success','failure','cancelled') else 'unknown'
    ident=run_id(now)
    journal.observe('workflow',workflow,now.isoformat(),['workflow-failed'] if status=='failure' else [],status=='success',ident,
                    {'workflow':workflow},stage=stage)
    if not any(r['run_id']==ident and r['workflow']==workflow for r in journal.data['runs']):
        journal.data['runs'].append({'run_id':ident,'workflow':workflow,'at':now.isoformat(),'status':status})
    size=journal.finish()
    print(json.dumps({'journal_bytes':size,'incidents':len(journal.data['incidents']),'model_calls':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workflow',choices=sorted(WORKFLOWS),required=True)
    parser.add_argument('--job-status',default='success');parser.add_argument('--bootstrap',action='store_true');args=parser.parse_args()
    collect(Path.cwd(),datetime.now(timezone.utc),args.workflow,args.job_status,args.bootstrap)
