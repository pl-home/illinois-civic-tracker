"""Read-only OpenRouter authentication/provider diagnostics; never calls a model."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, build_opener
from .daily import save
from .http import NoRedirect


def check(root):
    report={'checked_at':datetime.now(timezone.utc).isoformat(), 'model_calls':0}
    key=os.environ.get('OPENROUTER_API_KEY','').strip()
    if not key:raise ValueError('missing-openrouter-key')
    opener=build_opener(NoRedirect())
    for name,url,headers in [
        ('authentication','https://openrouter.ai/api/v1/key',{'Authorization':'Bearer '+key}),
        ('endpoint','https://openrouter.ai/api/v1/models/qwen/qwen3-32b/endpoints',{})]:
        try:
            with opener.open(Request(url,headers=headers),timeout=30) as response:
                raw=response.read(100001)
            if len(raw)>100000:raise ValueError('response-bound')
            value=json.loads(raw)['data']
            if name=='authentication':
                # Never publish key labels, hashes, account balances or unrelated spend.
                report[name]={'status':'ok'}
            else:
                endpoints=[e for e in value['endpoints'] if e.get('tag')=='deepinfra/fp8']
                report[name]={'present':bool(endpoints),'status_codes':[e.get('status') for e in endpoints],
                    'structured_outputs':all('response_format' in e.get('supported_parameters',[]) for e in endpoints)}
        except HTTPError as error:report[name]={'error':'HTTP_'+str(error.code)}
        except Exception as error:report[name]={'error':type(error).__name__}
    save(root/'data/openrouter-health.json',report)
    print(json.dumps(report))


if __name__=='__main__':check(Path.cwd())
