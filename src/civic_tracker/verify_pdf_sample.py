"""Bounded M0 PDF sample check; raw reports and XML remain ignored scratch."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,re,xml.etree.ElementTree as ET
from .http import Client,fingerprint


def parse_sponsor_rows(text,limit=10):
    owner=re.search(r'Sponsor Legislation Listing For (.+)',text)[1].strip()
    pattern=r'^(HB|SB|HR|SR|HJR|SJR)\s+(\d+)\s+(.+?)\s+((?:Alt\. )?(?:Chief Co-Sponsor|Chief Sponsor|Co-Sponsor))\s+([HS])\s+(.+?)\s+(\d{2}/\d{2}/\d{4})$'
    rows=[]
    for line in text.splitlines():
        match=re.match(pattern,line)
        if match:
            typ,num,title,role,chamber,action,date=match.groups()
            rows.append({'bill':typ+str(int(num)),'owner':owner,'role':role,'chamber':{'H':'House','S':'Senate'}[chamber],'action':action,'date':datetime.strptime(date,'%m/%d/%Y').date().isoformat()})
    if len(rows)<limit:raise ValueError('Insufficient parseable rows in bounded PDF sample')
    return rows[:limit]


def normalized_action(text):
    return ' '.join(re.sub(r'\s*\.\s*',' ',text).split()).casefold()


def current_role(block,name,alternate):
    # Only the named sample is checked. Alternate blocks are parenthesized, including
    # their chief. The first name is chief; dash-separated names before the first comma
    # are chief co-sponsors. Preserve the raw block for independent review.
    text=re.sub(r'^(?:Rep\.|Sen\.)\s*','',block.strip().lstrip('(')).strip()
    if name not in text:return None
    if text.startswith(name):base='Chief Sponsor'
    elif name in re.split(r',| and ',text,maxsplit=1)[0]:base='Chief Co-Sponsor'
    else:base='Co-Sponsor'
    return ('Alt. ' if alternate else '')+base


def main():
    import pdfplumber
    root=Path.cwd();scratch=root/'.local'
    config=json.loads((root/'config/project.json').read_text())
    initial=json.loads((root/'docs/evidence/m0-initial.json').read_text())
    client=Client(config,scratch,interval=config['backfill_main_site_min_interval_seconds'])
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'method':'First ten parseable bill rows on the first page of each sponsor report; XML retrieved from FTP. This is a layout sample, not subject-specific acceptance or exhaustive PDF validation.','reports':[],'comparisons':[]}
    for source in initial['checks']['0.6']['sources']:
        with pdfplumber.open(scratch/source['scratch_file']) as pdf:
            text=pdf.pages[0].extract_text() or ''
            summary={'url':source['url'],'pages':len(pdf.pages),'bytes':source['bytes'],'source_sha256':source['sha256']}
            if source['name'].startswith('Legislation in Committee'):
                summary.update({'status':'blocked-nonempty-sample','no_data_found':'NO DATA FOUND' in text})
                result['reports'].append(summary);continue
            rows=parse_sponsor_rows(text);summary.update({'status':'parsed-bounded-sample','sample_size':len(rows)})
            result['reports'].append(summary)
        for row in rows:
            typ,num=re.fullmatch(r'([A-Z]+)(\d+)',row['bill']).groups()
            code={'HJR':'HJ','SJR':'SJ'}.get(typ,typ)
            url=f'https://ftp.ilga.gov/Legislation/104/BillStatus/XML/10400{code}{int(num):04d}.xml'
            cache=scratch/(hashlib.sha256(url.encode()).hexdigest()+'.raw')
            if cache.exists():
                body=cache.read_bytes();evidence={'url':url,'sha256':hashlib.sha256(body).hexdigest(),'cached_from_initial_probe':True}
            else:
                fetched=client.get(url);body=fetched['body'];cache.write_bytes(body);evidence=fingerprint(fetched)
            tree=ET.fromstring(body);last=tree.find('lastaction');alternate=row['role'].startswith('Alt.')
            block=tree.findtext('./sponsor/'+('altsponsors' if alternate else 'sponsors')) or ''
            xml={'date':datetime.strptime(last.findtext('statusdate'),'%m/%d/%Y').date().isoformat(),'chamber':last.findtext('chamber'),'action':last.findtext('action'),'role':current_role(block,row['owner'],alternate),'sponsor_block':block}
            checks={'date':row['date']==xml['date'],'chamber':row['chamber']==xml['chamber'],'action':normalized_action(row['action'])==normalized_action(xml['action']),'role':row['role']==xml['role']}
            result['comparisons'].append({'pdf':row,'xml':xml,'checks':checks,'evidence':evidence})
    result['sample_size']=len(result['comparisons']);result['all_fields_match']=sum(all(c['checks'].values()) for c in result['comparisons'])
    path=root/'docs/evidence/m0-pdf-sample.json';path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'sample_size':result['sample_size'],'all_fields_match':result['all_fields_match'],'mismatch_bills':[r['pdf']['bill'] for r in result['comparisons'] if not all(r['checks'].values())]}))

if __name__=='__main__':main()
