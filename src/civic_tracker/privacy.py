"""Fail on private addresses, user-profile paths and recognizable credential shapes."""
from pathlib import Path
import re,subprocess

EMAIL=re.compile(r'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
NOREPLY=re.compile(r'(?:\d+\+)?[A-Za-z0-9-]+(?:\[bot\])?@users\.noreply\.github\.com\Z')
PROFILE=re.compile(r'(?i)\b[A-Z]:[\\/]+Users[\\/]')
CREDENTIAL=re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AIza[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,})')
OPAQUE=re.compile(r'\b[A-Za-z0-9]{32,}\b')
# Exact reviewed public CA certificate basename, not an exemption for URL contents.
PUBLIC_IDENTIFIERS={'SectigoPublicServer'+'AuthenticationCAOVR40'}

def violations(text):
    failures=[]
    if any(not NOREPLY.fullmatch(value) for value in EMAIL.findall(text)):failures.append('email-address')
    if PROFILE.search(text):failures.append('user-profile-path')
    if CREDENTIAL.search(text):failures.append('credential-shape')
    for found in OPAQUE.finditer(text):
        value=found.group()
        if value in PUBLIC_IDENTIFIERS:continue
        # Source SHA-256 fingerprints are public evidence; other mixed opaque values need review.
        if len(value)==64 and re.fullmatch('[a-f0-9]+',value):continue
        line=text[text.rfind('\n',0,found.start())+1:text.find('\n',found.end()) if '\n' in text[found.end():] else len(text)]
        if len(value)==32 and re.fullmatch('[a-f0-9]+',value) and '"etag"' in line:continue
        if any(c.isalpha() for c in value) and any(c.isdigit() for c in value):
            failures.append('opaque-token-shape');break
    return failures

def scan(root):
    paths=subprocess.run(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=root,capture_output=True,check=True).stdout.decode().split('\0')
    failures=[]
    for relative in sorted(set(paths)-{''}):
        path=root/relative
        if not path.is_file():continue
        try:text=path.read_text(encoding='utf-8-sig')
        except UnicodeError:failures.append({'file':relative,'kinds':['unreviewed-binary']});continue
        kinds=violations(text)
        if kinds:failures.append({'file':relative,'kinds':kinds})
    return failures

if __name__=='__main__':
    import json
    findings=scan(Path.cwd());print(json.dumps({'privacy_findings':findings}));raise SystemExit(bool(findings))
