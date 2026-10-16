"""Small HTTP client enforcing the project's host and rate rules."""
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPSHandler
from urllib.parse import urlsplit
from urllib.error import HTTPError
import hashlib,json,os,time,ssl

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
        validate_url(url);host=urlsplit(url).netloc;lock=self.state_dir/'main-request.lock';fd=None;started=None
        handlers=[NoRedirect()]
        context=source_tls_context(self.config,self.state_dir,host)
        if context is not None:handlers.append(HTTPSHandler(context=context))
        opener=build_opener(*handlers)
        request=Request(url,method=method,headers={'User-Agent':self.config['user_agent'],**(headers or {})})
        try:
            if host=='ilga.gov':
                try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
                except FileExistsError:raise RuntimeError('Another main-site request owns the rate gate') from None
                clock=self.state_dir/'main-request-clock.json'
                previous=json.loads(clock.read_text()) if clock.exists() else {}
                deadline=previous.get('started_epoch',0)+self.interval
                while time.time()<deadline:
                    time.sleep(max(0,deadline-time.time()))
            started=time.time()
            try:
                with opener.open(request,timeout=45) as r:
                    data=r.read(self.config['max_source_bytes']+1)
                    if len(data)>self.config['max_source_bytes']:raise ValueError('Source exceeds configured byte bound')
                    result={'url':url,'status':r.status,'body':data,'headers':dict(r.headers)}
            except HTTPError as ex:
                if ex.code!=304:raise
                result={'url':url,'status':304,'body':b'','headers':dict(ex.headers)}
            self.events.append({'host':host,'started_epoch':started,'status':result['status']})
            return result
        finally:
            if fd is not None:
                try:
                    # Persist the same timestamp used in evidence, after the attempt.
                    # Writing the clock before measuring the start caused sub-millisecond
                    # shortfalls in the first M0 spacing evidence.
                    if started is not None:clock.write_text(json.dumps({'started_epoch':started}))
                finally:
                    os.close(fd);lock.unlink(missing_ok=True)


def fingerprint(result):
    headers={key.casefold():value for key,value in result['headers'].items()}
    return {'url':result['url'],'status':result['status'],'bytes':len(result['body']),
            'sha256':hashlib.sha256(result['body']).hexdigest(),
            'last_modified':headers.get('last-modified'),'etag':headers.get('etag')}


def error_metadata(error):
    """Bounded public diagnostics without exception text, URLs, headers or local paths."""
    result={'error':type(error).__name__}
    cause=getattr(error,'reason',None)
    if cause is not None:
        result['cause']=type(cause).__name__
        for attribute in ('reason','verify_code','errno'):
            value=getattr(cause,attribute,None)
            if isinstance(value,(str,int)) and len(str(value))<120:result[attribute]=value
    if isinstance(error,HTTPError):result['http_status']=error.code
    return result


def source_tls_context(config,state_dir,host):
    """Supply a missing intermediate without disabling hostname or root verification.

    The CA's published AIA URL is HTTP. Its certificate bytes must match the pinned
    fingerprint observed in an independently verified chain before loading them.
    This permits a public intermediate, never a leaf or a new trusted root.
    """
    certificates=[item for item in config.get('tls_intermediates',[]) if host in item['hosts']]
    if not certificates:return None
    context=ssl.create_default_context()
    # Require a path to a system root, even on Python versions enabling partial chains.
    context.verify_flags &= ~getattr(ssl,'VERIFY_X509_PARTIAL_CHAIN',0)
    for item in certificates:
        parsed=urlsplit(item['url'])
        if parsed.netloc!='crt.sectigo.com' or parsed.path!='/SectigoPublicServerAuthenticationCAOVR40.crt' or parsed.scheme not in ('http','https') or parsed.query or parsed.fragment:
            raise ValueError('Unapproved certificate issuer URL')
        cache=Path(state_dir)/('issuer-'+item['der_sha256']+'.der')
        if cache.exists():data=cache.read_bytes()
        else:
            request=Request(item['url'],headers={'User-Agent':config['user_agent']})
            with build_opener(NoRedirect()).open(request,timeout=20) as response:data=response.read(32769)
        if len(data)>32768 or hashlib.sha256(data).hexdigest()!=item['der_sha256']:
            raise ValueError('Certificate issuer fingerprint mismatch')
        context.load_verify_locations(cadata=ssl.DER_cert_to_PEM_cert(data))
        if not cache.exists():cache.write_bytes(data)
    return context
