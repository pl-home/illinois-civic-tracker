"""Small public-runner reachability probe: no secrets or message sending."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys
from .http import Client,fingerprint,error_metadata


def main():
    root=Path.cwd();config=json.loads((root/'config/project.json').read_text())
    client=Client(config,root/'.local',interval=config['backfill_main_site_min_interval_seconds'])
    urls=['https://ftp.ilga.gov/Members/104HouseMembers.xml','https://ilga.gov/robots.txt',
          'https://ilga.gov/documents/reports/static/104MemberVotes.csv','https://capitolfax.com/?s=Bradley+Fritts&feed=rss2','https://leecodemocrats.com/','https://leecountyilgop.org/']
    results=[]
    for url in urls:
        try:results.append({**fingerprint(client.get(url,method='HEAD' if url.endswith('.csv') else 'GET')),'reachable':True})
        except Exception as ex:results.append({'url':url,'reachable':False,**error_metadata(ex)})
    report={'observed_at':datetime.now(timezone.utc).isoformat(),'environment':'GitHub-hosted runner','sources':results,'all_reachable':all(row['reachable'] for row in results),'requests':client.events}
    destination=root/'docs/evidence/m0-runner-access.json';destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'source_reachability':[{'url':row['url'],'reachable':row['reachable']} for row in results]}))
    return int(not report['all_reachable'])

if __name__=='__main__':raise SystemExit(main())
