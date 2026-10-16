"""Small HTTP client enforcing the project's host and rate rules."""
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.parse import urlsplit
from urllib.error import HTTPError
import hashlib,json,os,time

ALLOWED={'ftp.ilga.gov','ilga.gov','capitolfax.com','leecodemocrats.com','leecountyilgop.org'}


def validate_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.netloc not in ALLOWED:raise ValueError('Unapproved source host')
    if p.netloc=='ilga.gov' and any(p.path.casefold().startswith(prefix) for prefix in ['/account','/admin','/search','/api','/mylegislation']):
        raise ValueError('Logged-in or disallowed main-site path')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        # An automatic redirect could skip the main-site rate gate. Caller must retry explicitly.
        raise ValueError('Redirect requires an explicit rate-checked request')


class Client:
    def __init__(self,config,state_dir,interval=None):
        self.config=config;self.state_dir=Path(state_dir);self.state_dir.mkdir(parents=True,exist_ok=True)
        self.interval=config['main_site_min_interval_seconds'] if interval is None else interval
        if self.interval<10:raise ValueError('Main-site interval must be at least ten seconds')
        self.events=[]
    def get(self,url,headers=None,method="GET"):
        validate_url(url);host=urlsplit(url).netloc;lock=self.state_dir/'main-request.lock';fd=None
        try:
            if host=='ilga.gov':
                try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
                except FileExistsError:raise RuntimeError('Another main-site request owns the rate gate') from None
                clock=self.state_dir/'main-request-clock.json'
                previous=json.loads(clock.read_text()) if clock.exists() else {}
                time.sleep(max(0,self.interval-(time.time()-previous.get('started_epoch',0))))
                clock.write_text(json.dumps({'started_epoch':time.time()}))
            started=time.time();request=Request(url,method=method,headers={'User-Agent':self.config['user_agent'],**(headers or {})})
            try:
                with build_opener(NoRedirect()).open(request,timeout=45) as r:
                    data=r.read(self.config['max_source_bytes']+1)
                    if len(data)>self.config['max_source_bytes']:raise ValueError('Source exceeds configured byte bound')
                    result={'url':url,'status':r.status,'body':data,'headers':dict(r.headers)}
            except HTTPError as ex:
                if ex.code!=304:raise
                result={'url':url,'status':304,'body':b'','headers':dict(ex.headers)}
            self.events.append({'host':host,'started_epoch':started,'status':result['status']})
            return result
        finally:
            if fd is not None:os.close(fd);lock.unlink(missing_ok=True)


def fingerprint(result):
    headers={key.casefold():value for key,value in result['headers'].items()}
    return {'url':result['url'],'status':result['status'],'bytes':len(result['body']),
            'sha256':hashlib.sha256(result['body']).hexdigest(),
            'last_modified':headers.get('last-modified'),'etag':headers.get('etag')}
