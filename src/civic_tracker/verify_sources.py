"""M0 evidence capture. Raw sources stay in ignored local scratch; reports are compact."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,quote,urlencode
import argparse,collections,csv,hashlib,json,re,zipfile,xml.etree.ElementTree as ET
from .http import Client,fingerprint
from .vote_csv import read_csv,bill_id,motion,choice
from .rules import ceremonial,shell


def now():return datetime.now(timezone.utc).isoformat()
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def compare_votes(csv_data,archive):
    # Join only floor votes. The CSV has no committee rows and cannot replace committee evidence.
    index=collections.defaultdict(list)
    for row in csv_data['subjects']:
        key=(row['subject'],bill_id(row['Legislation']),row['Chamber'],row['Vote Date'],motion(row['Vote Type']))
        index[key].append(row)
    verified=collections.defaultdict(list);committee_count=0
    for record in archive['votes'].values():
        if record.get('scope')!='floor':committee_count+=1;continue
        for selected in record['choices']:
            who={'3428':'fritts','3383':'arellano'}.get(str(selected['member_id']))
            if not who:continue
            key=(who,bill_id(record['measure_id'].split('-')[-1]),record['chamber'],record['date'],motion(record.get('motion_context','')))
            verified[key].append((record,selected))
    matched=[];mismatches=[];seen_csv=set()
    for key,records in verified.items():
        candidates=index.get(key,[])
        distinct={selected['choice'] for record,selected in records}
        if len(distinct)!=1:
            mismatches.append({'key':key,'kind':'conflicting-retained-pdf-choices','pdf_choices':sorted(distinct)});continue
        expected=next(iter(distinct))
        if not candidates:
            # Report missing motion/date keys rather than silently matching on fewer fields.
            alternatives=[{'date':other[3],'motion':other[4]} for other in index if other[:3]==key[:3]]
            mismatches.append({'key':key,'kind':'no-exact-csv-key','pdf_choice':expected,'available_csv_date_motions':alternatives});continue
        csv_choices={choice(row['Vote']) for row in candidates};seen_csv.add(key)
        if csv_choices!={expected}:mismatches.append({'key':key,'kind':'choice-mismatch','pdf_choice':expected,'csv_choices':sorted(csv_choices)})
        else:matched.append(key)
    csv_only=[{'key':key,'choices':sorted({choice(row['Vote']) for row in rows})} for key,rows in index.items() if key not in verified]
    return {'verified_source_documents':len(archive['votes']),'committee_documents_outside_csv':committee_count,'unique_verified_floor_keys':len(verified),'exact_choice_matches':len(matched),'exact_match_rate':len(matched)/len(verified) if verified else None,'mismatches':mismatches,'csv_only':csv_only,
            'csv_target_counts':dict(collections.Counter(row['subject'] for row in csv_data['subjects'])),'csv_target_split_counts':dict(collections.Counter(row['subject'] for row in csv_data['subjects'] if row['nay_count']>0)),
            'hb24_checks':[{'subject':row['subject'],'date':row['Vote Date'],'chamber':row['Chamber'],'motion':row['Vote Type'],'vote':row['Vote'],'nays':row['nay_count']} for row in csv_data['subjects'] if bill_id(row['Legislation'])=='HB24']}


def run(root,archive_path,provided_csv):
    scratch=root/'.local';scratch.mkdir(exist_ok=True)
    config=json.loads((root/'config/project.json').read_text(encoding='utf-8'))
    client=Client(config,scratch,interval=config['backfill_main_site_min_interval_seconds'])
    archive=json.loads(archive_path.read_text(encoding='utf-8'))
    archive_root=archive_path.parents[2]
    manifest=json.loads((archive_path.parent/'source-manifest.json').read_text(encoding='utf-8'))
    report={'observed_at':now(),'checks':{},'errors':[]};cache={}
    def fetch(url):
        if url not in cache:
            result=client.get(url);cache[url]=result
            suffix='.pdf' if result['body'].startswith(b'%PDF') else '.raw'
            path=scratch/(hashlib.sha256(url.encode()).hexdigest()+suffix);path.write_bytes(result['body'])
        return cache[url]
    def checkpoint():write(scratch/'m0-progress.json',{'updated_at':now(),'checks_completed':list(report['checks']),'errors':report['errors']})
    # Snapshot public access policy before using the main site.
    robots=fetch('https://ilga.gov/robots.txt')
    report['robots']={'evidence':fingerprint(robots),'directives':[line for line in robots['body'].decode('utf-8','replace').splitlines() if any(word in line.lower() for word in ['crawl-delay','disallow','ftp.ilga.gov'])]}
    vote=fetch('https://ilga.gov/documents/reports/static/104MemberVotes.csv')
    vote_path=scratch/'104MemberVotes.csv';vote_path.write_bytes(vote['body'])
    parsed=read_csv(vote_path)
    report['checks']['0.4']={'evidence':fingerprint(vote),'provided_csv_sha256':hashlib.sha256(provided_csv.read_bytes()).hexdigest(),'provided_and_current_identical':provided_csv.read_bytes()==vote['body'],**compare_votes(parsed,archive)}
    report['checks']['0.5']={'status':'observing','observations':[{'at':now(),**fingerprint(vote)}],'latest_vote_date':parsed['latest_vote_date'],'rows':parsed['row_count'],'roll_calls':parsed['roll_call_count'],'note':'A single observation cannot establish regeneration cadence; recheck daily and after the veto session.'};checkpoint()
    listing_url='https://ftp.ilga.gov/Legislation/104/BillStatus/XML/'
    listing=fetch(listing_url);text=listing['body'].decode('utf-8','replace')
    entries=re.findall(r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}\s+[AP]M)\s+(\d+)\s+<A HREF="([^"]+)"',text,re.I)
    links=re.findall(r'HREF="([^"]+)"',text,re.I)
    parent=fetch('https://ftp.ilga.gov/Legislation/104/BillStatus/')
    parent_links=re.findall(r'HREF="([^"]+)"',parent['body'].decode('utf-8','replace'),re.I)
    with (root/'tests/fixtures/fritts-sponsorship-104.csv').open(encoding='utf-8-sig',newline='') as f:export=list(csv.DictReader(f))
    sample=[]
    for typ,count in [('HB',20),('SB',14),('HR',10),('HJR',4),('SJR',2)]:sample.extend([row['Legislation'] for row in export if re.match('[A-Z]+',row['Legislation'])[0]==typ][:count])
    by_filename={Path(urlsplit(url).path).name.casefold():(url,entry) for url,entry in manifest.items() if '/billstatus/xml/' in url.casefold()}
    compared=[]
    for ident in sample:
        typ,num=re.fullmatch(r'([A-Z]+)(\d+)',ident).groups();code={'HJR':'HJ','SJR':'SJ'}.get(typ,typ);filename=f'10400{code}{int(num):04d}.xml'
        url='https://ftp.ilga.gov/Legislation/104/BillStatus/XML/'+filename
        current=fetch(url);old_url,entry=by_filename[filename.casefold()]
        if 'archive' in entry:
            with zipfile.ZipFile(archive_root/entry['archive']) as archive_zip:old=archive_zip.read(entry['entry'])
        else:old=(archive_root/entry['path']).read_bytes()
        assert hashlib.sha256(old).hexdigest()==entry['sha256']
        compared.append({'bill':ident,'ftp':fingerprint(current),'old_source_url':old_url,'old_retrieved_at':entry['retrieved_at'],'old_sha256':entry['sha256'],'identical':current['body']==old})
    report['checks']['0.1']={'sample_size':len(compared),'identical':sum(item['identical'] for item in compared),'comparison_basis':'Current FTP bytes against hash-verified archived main-site mirror bytes, not 50 new main-site downloads.','listing_entries_with_date_and_size':len(entries),'zip_links_seen':[link for link in links+parent_links if link.lower().endswith('.zip')],'sample':compared}
    report['checks']['0.2']={'status':'observing','observations':[{'at':now(),'listing':fingerprint(listing),'listing_entry_count':len(entries),'recent_timestamps':dict(collections.Counter(date+' '+clock for date,clock,size,url in entries).most_common(12))}],'note':'Listing timestamps are source metadata, not proof of sync timezone or completion. Repeat over 2-3 days.'};checkpoint()
    amendments={}
    for num in [742,2137]:
        url=f'https://ftp.ilga.gov/Legislation/104/BillStatus/XML/10400HB{num:04d}.xml';result=fetch(url);tree=ET.fromstring(result['body']);sections=[];title='Original synopsis';operation='original'
        for child in tree.find('synopsis'):
            if child.tag=='synopsistitle':
                title=''.join(child.itertext()).strip() or 'Original synopsis';operation='original' if title=='Original synopsis' else 'unspecified'
            elif child.tag=='reftype':operation=''.join(child.itertext()).strip()
            elif child.tag=='reference':sections.append({'section':title,'operation':operation,'reference':''.join(child.itertext()).strip()})
        amendments['HB'+str(num)]={'evidence':fingerprint(result),'short_description':tree.findtext('shortdesc'),'last_action':tree.findtext('lastaction/action'),'references':sections,'has_adds_and_deletes':any('Adds' in row['operation'] for row in sections) and any('Deletes' in row['operation'] for row in sections)}
    report['checks']['0.3']={'bills':amendments,'implication':'XML carries amendment-specific additions/deletions alongside original references. Do not treat the flat union as current law or current text.'}
    service={}
    for chamber in ['House','Senate']:
        result=fetch(f'https://ftp.ilga.gov/Members/103{chamber}Members.xml');tree=ET.fromstring(result['body'])
        service[chamber]={'evidence':fingerprint(result),'target_members':[{'name':member.findtext('Name'),'district':member.findtext('District')} for member in tree.findall('Member') if any(name in (member.findtext('Name') or '') for name in ['Fritts','Arellano'])]}
    report['checks']['0.10']=service;checkpoint()
    pdfs=[]
    for name in ['Legislation in Committee-House.pdf','Legislation in Committee-Senate.pdf','Sponsor Bill Listing By Name-House.pdf','Sponsor Bill Listing By Name-Senate.pdf']:
        url='https://ilga.gov/documents/reports/static/'+quote(name)
        try:
            result=fetch(url)
            pdfs.append({'name':name,**fingerprint(result),'pdf_signature':result['body'].startswith(b'%PDF'),'scratch_file':hashlib.sha256(url.encode()).hexdigest()+'.pdf'})
        except Exception as ex:pdfs.append({'name':name,'url':url,'error':type(ex).__name__})
    report['checks']['0.6']={'status':'downloaded-awaiting-parse','sources':pdfs};checkpoint()
    feeds=[]
    for term in ['Bradley Fritts','Li Arellano','Darin LaHood','Dick Durbin','Tammy Duckworth','Lee County','Lee County Democrats','Lee County Republicans']:
        url='https://capitolfax.com/?'+urlencode({'s':term,'feed':'rss2'})
        try:
            result=fetch(url);tree=ET.fromstring(result['body']);items=tree.findall('./channel/item')
            public=[{'title':item.findtext('title'),'link':item.findtext('link'),'date':item.findtext('pubDate')} for item in items if not (item.findtext('title') or '').startswith('Protected:')]
            feeds.append({'term':term,'evidence':fingerprint(result),'items_total':len(items),'public_items':len(public),'samples':public[:3]})
        except Exception as ex:feeds.append({'term':term,'url':url,'error':type(ex).__name__})
    report['checks']['0.7']={'feeds':feeds};report['requests']=client.events;report['finished_at']=now()
    write(root/'docs/evidence/m0-initial.json',report);checkpoint()
    print(json.dumps({'checks':list(report['checks']),'csv_targets':report['checks']['0.4']['csv_target_counts'],'vote_matches':report['checks']['0.4']['exact_choice_matches'],'vote_mismatches':len(report['checks']['0.4']['mismatches']),'csv_only':len(report['checks']['0.4']['csv_only']),'ftp_identical':report['checks']['0.1']['identical'],'pdf_download_errors':sum('error' in item for item in pdfs),'feed_errors':sum('error' in item for item in feeds)}))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--provided-csv',type=Path,required=True);args=parser.parse_args()
    run(Path.cwd(),args.archive,args.provided_csv)

if __name__=='__main__':main()
