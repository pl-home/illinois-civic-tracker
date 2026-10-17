"""M0 hearing fallback verification using cached public pages and FTP bill XML."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin
import hashlib,json,re,xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from .hearings import parse_hearing_details
from .http import Client,fingerprint


def normalized(text):
    return re.sub(r'[^a-z0-9]', '', text.casefold())


def history_agrees(body, page):
    soup=BeautifulSoup(body,'html.parser');dates=set()
    for anchor in soup.find_all('a',href=True):
        if urljoin(page['source_url'],anchor['href']) != page['source_url']:
            continue
        row=anchor.find_parent('tr')
        if row:
            found=re.search(r'\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s+[AP]M',row.get_text(' ',strip=True))
            if found:dates.add(found[0])
    return dates == {page['raw_date']}


def main():
    root=Path.cwd();scratch=root/'.local'
    config=json.loads((root/'config/project.json').read_text())
    client=Client(config,scratch)
    catalog=[]
    for filename in ['hearing-details-inspection.json','hearing-expanded-inspection.json']:
        catalog.extend(json.loads((scratch/filename).read_text()))
    detail_sources=[item for item in catalog if item['name'].startswith(('house-detail-','senate-detail-'))]
    # Include the Senate sample before the larger House docket; then use source order.
    detail_sources.sort(key=lambda item:0 if item['name'].startswith('senate') else 1)
    hearings=[];source_evidence=[]
    for source in detail_sources:
        page=parse_hearing_details((scratch/('hearing-'+source['name']+'.html')).read_bytes(),source['url'])
        history_file='hearing-senate-history-3130.html' if page['chamber']=='Senate' else 'hearing-house-history.html'
        page['history_time_matches']=history_agrees((scratch/history_file).read_bytes(),page)
        hearings.append(page)
        source_evidence.append({key:source[key] for key in ['url','status','bytes','sha256','observed_at']})
    sample=[];seen=set()
    for page in hearings:
        for item in page['items']:
            if item['bill'] in seen:continue
            seen.add(item['bill']);sample.append((page,item))
            if len(sample)==20:break
        if len(sample)==20:break
    comparisons=[]
    for page,item in sample:
        typ,num=re.fullmatch(r'([A-Z]+)(\d+)',item['bill']).groups()
        code={'HJR':'HJ','SJR':'SJ','HJRCA':'HC','SJRCA':'SC'}.get(typ,typ)
        url=f'https://ftp.ilga.gov/Legislation/{config["ga"]}/BillStatus/XML/{config["ga"]}00{code}{int(num):04d}.xml'
        cache=scratch/(hashlib.sha256(url.encode()).hexdigest()+'.raw')
        if cache.exists():
            body=cache.read_bytes();evidence={'url':url,'sha256':hashlib.sha256(body).hexdigest(),'cached':True}
        else:
            fetched=client.get(url);body=fetched['body'];cache.write_bytes(body);evidence=fingerprint(fetched)
        tree=ET.fromstring(body);title=tree.findtext('title') or ''
        ident=re.search(r'for\s+([A-Z]+)\s*(\d+)',title)
        committee=page['title'].split(' Hearing Details -')[0]
        committee=re.sub(r'^(House|Senate)\s+','',committee).removesuffix(' Committee')
        actions=[];date='';chamber=''
        for child in tree.find('actions'):
            if child.tag=='statusdate':date=child.text or ''
            elif child.tag=='chamber':chamber=child.text or ''
            elif child.tag=='action' and chamber==page['chamber'] and normalized(committee) in normalized(child.text or ''):
                actions.append({'date':date,'action':child.text})
        comparisons.append({'bill':item['bill'],'hearing_url':page['source_url'],'hearing_date_local':page['date_local'],
                            'posted_item':item,'xml':evidence,'xml_title':title,'short_description':tree.findtext('shortdesc'),
                            'identity_matches':bool(ident and ident[1]+str(int(ident[2]))==item['bill']),
                            'same_committee_action_history_found':bool(actions),'committee_action_samples':actions[:4]})
    report={'observed_at':datetime.now(timezone.utc).isoformat(),
            'method':'Public hearing details parsed without the disallowed range API. Five nonempty page samples, twenty distinct bill identities cross-checked with FTP XML; hearing times cross-checked against public committee history rows. XML does not establish hearing time.',
            'static_committee_pdf_nonempty_validation':'pending',
            'history_sources':[{'url':url,'sha256':hashlib.sha256((scratch/file).read_bytes()).hexdigest()} for url,file in [('https://ilga.gov/House/Committees/Hearings/3062','hearing-house-history.html'),('https://ilga.gov/Senate/Committees/Hearings/3130','hearing-senate-history-3130.html')]],
            'range_api_used':False,'historical_only':True,'active_witness_form_verified':False,
            'sources':source_evidence,'hearings':[dict((key,value) for key,value in page.items() if key!='items')|{'posted_item_count':len(page['items'])} for page in hearings],
            'parsed_posted_items':sum(len(page['items']) for page in hearings),
            'distinct_bills_compared':len(comparisons),'identity_matches':sum(item['identity_matches'] for item in comparisons),
            'history_time_matches':sum(page['history_time_matches'] for page in hearings),
            'comparisons':comparisons}
    (root/'docs/evidence/m0-hearing-fallback.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({key:report[key] for key in ['parsed_posted_items','distinct_bills_compared','identity_matches','history_time_matches']}))

if __name__=='__main__':main()
