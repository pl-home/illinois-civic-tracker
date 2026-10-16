"""Normalize the public floor CSV without collapsing distinct non-voting choices."""
import csv,re,collections

def bill_id(value):
    match=re.match(r'^([A-Z]+)\s*0*(\d+)',value.strip().upper())
    if not match:raise ValueError('Unrecognized measure identifier')
    return match[1]+str(int(match[2]))

def motion(value):
    text=' '.join(value.upper().split()).replace('.','')
    parts=[part.strip() for part in text.split('/')]
    if parts[0] in ('HOUSE BILL','HOUSE BILLS','SENATE BILL','SENATE BILLS','RESOLUTIONS','JOINT RESOLUTIONS') and len(parts)>1:text=parts[1]
    else:text=parts[0]
    text=re.sub(r'#\s*(?=\d)', 'NO ', text)
    text=re.sub(r'\bNO\s*(\d+)',r'NO \1',text)
    return text

def choice(value):
    # "Absent", "Excused" and "Not Voting" have different meanings and remain distinct.
    return {'yea':'yes','nay':'no','present':'present','excused':'excused','absent':'absent','not voting':'not-voting'}.get(value.strip().casefold(),'unknown:'+value.strip())

def subject_id(name):
    if name.startswith('Fritts,'):return 'fritts'
    if name.startswith('Arellano,'):return 'arellano'
    return None

def read_csv(path):
    nays=collections.Counter();subjects=[];rolls=set();rows=0;latest='';raw_choices=collections.Counter()
    with path.open(encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle)
        expected={'GA','Member','Chamber','Session','Legislation','Vote Type','Vote Date','Vote'}
        if set(reader.fieldnames or [])!=expected:raise ValueError('Vote CSV columns changed')
        for row in reader:
            rows+=1;roll=(row['GA'],row['Chamber'],row['Session'],row['Legislation'],row['Vote Type'],row['Vote Date'])
            rolls.add(roll);latest=max(latest,row['Vote Date']);raw_choices[row['Vote']]+=1
            if choice(row['Vote'])=='no':nays[roll]+=1
            who=subject_id(row['Member'])
            if who:subjects.append({**row,'subject':who,'roll':roll})
    for row in subjects:row['nay_count']=nays[row['roll']]
    return {'row_count':rows,'roll_call_count':len(rolls),'latest_vote_date':latest,'raw_choices':dict(raw_choices),'subjects':subjects}
