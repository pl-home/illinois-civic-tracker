"""Collect compact M0 timing observations for a bounded three-day window."""
from pathlib import Path
from datetime import datetime,timezone
import json,re
from urllib.request import Request
from .http import Client,fingerprint,validate_url


def main():
    root=Path.cwd();config=json.loads((root/'config/project.json').read_text())
    plan=json.loads((root/'config/m0-observation.json').read_text())
    now=datetime.now(timezone.utc)
    if now>=datetime.fromisoformat(plan['end_exclusive']):
        print('M0 observation window ended; no requests made.');return
    destination=root/'docs/evidence/m0-observations.json'
    observations=json.loads(destination.read_text()) if destination.exists() else []
    slot=now.strftime('%Y-%m-%dT')+str((now.hour//6)*6).zfill(2)
    if any(item['slot']==slot for item in observations):
        print('M0 observation window already recorded.');return
    client=Client(config,root/'.local')
    listing=client.get('https://ftp.ilga.gov/Legislation/104/BillStatus/XML/')
    rows=re.findall(r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}\s+[AP]M)\s+(\d+)\s+<A HREF="([^"]+)"',listing['body'].decode('utf-8'),re.I)
    entry={'slot':slot,'observed_at':now.isoformat(),'listing':fingerprint(listing),'listing_rows':len(rows),'listing_date_samples':sorted(set(date for date,clock,size,url in rows))[-10:]}
    if not any(item.get('csv_headers') and item['observed_at'][:10]==now.date().isoformat() for item in observations):
        # Header-only observations avoid re-downloading the full CSV during M0.
        url='https://ilga.gov/documents/reports/static/104MemberVotes.csv'
        result=client.get(url,method='HEAD')
        headers={key.casefold():value for key,value in result['headers'].items()}
        entry['csv_headers']={'url':url,'method':'HEAD','status':result['status'],'last_modified':headers.get('last-modified'),'etag':headers.get('etag'),'content_length':headers.get('content-length')}
    observations.append(entry);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(json.dumps(observations,indent=2)+'\n')
    print('Recorded compact M0 listing/header observation.')

if __name__=='__main__':main()
