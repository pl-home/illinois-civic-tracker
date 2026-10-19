"""Allowlisted response metadata only. Never returns model text or error messages."""
import hashlib
import json
import re

FIELDS={'status','committee','measure','motion','member_vote','tally','document_title','decisions'}
STATUSES={'extracted','unverified','verified','ok','success','complete','failed','error','unknown'}
FINISH={'stop','length','content_filter','tool_calls','error','eos','unknown'}
ERROR_TYPES={'rate_limit_exceeded','context_length_exceeded','invalid_request','authentication',
             'permission_denied','server','provider_unavailable','content_filter'}


def integer(value):return value if type(value) is int and 0<=value<=10_000_000 else None
def kind(value):return ('object' if isinstance(value,dict) else 'array' if isinstance(value,list) else
                       'null' if value is None else 'boolean' if type(value) is bool else 'number' if isinstance(value,(int,float)) else 'string')


def completion(result,expected):
    if not isinstance(result,dict):return {'envelope_shape':kind(result)}
    d={'envelope_shape':'object','provider_match':result.get('provider')=='DeepInfra',
       'model_match':result.get('model') in ('qwen/qwen3-32b','qwen/qwen3-32b-04-28')}
    ident=result.get('id')
    if isinstance(ident,str) and re.fullmatch(r'gen-\d{8,16}-[A-Za-z0-9]{1,50}',ident):d['response_id']=ident
    usage=result.get('usage')
    if isinstance(usage,dict):
        for key in ('prompt_tokens','completion_tokens','total_tokens'):
            if integer(usage.get(key)) is not None:d[key]=usage[key]
    choices=result.get('choices')
    choice=choices[0] if isinstance(choices,list) and choices and isinstance(choices[0],dict) else {}
    finish=choice.get('finish_reason');d['finish_reason']=finish if isinstance(finish,str) and finish in FINISH else 'not-captured' if finish is None else 'other'
    message=choice.get('message');message=message if isinstance(message,dict) else {}
    d['refusal_present']=bool(message.get('refusal'));d['reasoning_present']=bool(message.get('reasoning'))
    content=message.get('content');d['content_shape']=kind(content)
    if not isinstance(content,str):d['json_parse']='not-string';return d
    d['content_bytes']=len(content.encode());d['code_fence']=content.lstrip().startswith('```')
    if d['content_bytes']>100_000:d['json_parse']='over-bound';return d
    try:value=json.loads(content)
    except json.JSONDecodeError as error:
        d.update(json_parse='invalid',json_error_line=error.lineno,json_error_column=error.colno);return d
    d.update(json_parse='ok',json_shape=kind(value))
    if not isinstance(value,dict):return d
    expected=set(expected)&FIELDS
    d['missing_fields']=sorted(expected-set(value));d['unexpected_field_count']=len(set(value)-expected)
    status=value.get('status');d['status_shape']=kind(status)
    if status is None:d['model_status']='not-captured'
    elif isinstance(status,str):
        normalized=status.strip().lower();d['model_status']=normalized if normalized in STATUSES else 'other'
        d['status_exact']=status=='extracted';d['status_chars']=len(status)
        if normalized not in STATUSES:d['status_sha256']=hashlib.sha256(status.encode()).hexdigest()
    else:d['model_status']='other'
    return d


def http_error(error):
    d={'http_status':error.code if type(error.code) is int and 100<=error.code<=599 else 0}
    try:
        raw=error.read(16_385)
        if len(raw)>16_384:d['http_json']='over-bound';return d
        value=json.loads(raw);payload=value.get('error',{}) if isinstance(value,dict) else {}
        metadata=payload.get('metadata',{}) if isinstance(payload,dict) else {}
        if not isinstance(metadata,dict):metadata={}
        error_type=metadata.get('error_type')
        d['provider_error_type']=error_type if isinstance(error_type,str) and error_type in ERROR_TYPES else 'other'
        d['parser_annotations_present']=bool(metadata.get('file_annotations'));d['http_json']='ok'
    except Exception:d['http_json']='unavailable'
    return d
