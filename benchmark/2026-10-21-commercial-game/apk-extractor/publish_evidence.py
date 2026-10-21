#!/usr/bin/env python3
"""Publish small sanitized evidence; preserve private raw bytes and failed attempts."""
import argparse
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')

def publish(main, base):
    E=D/'evidence'; E.mkdir(exist_ok=True)
    aliases=sorted([(str(D),'G08'),(str(D.parents[2]),'LANE'),(str(main),'MAIN'),
                    (str(base),'COMMERCIAL_PRIVATE'),(str(Path.home()),'HOME')],key=lambda x:-len(x[0]))
    def sanitize(s):
        for old,new in aliases:s=s.replace(old,new)
        return s
    raw=[]
    for p in sorted((D/'.private').rglob('*')):
        if p.is_file():raw.append({'alias':'G08_PRIVATE/'+str(p.relative_to(D/'.private')),'sha256':sha(p),'bytes':p.stat().st_size})
    public=[]
    for folder in ['replay-02','replay-03','boundaries-03','revision-02','static-01','static-02']:
        for p in sorted((D/'.private'/folder).iterdir()):
            if p.suffix not in ['.json','.stdout','.stderr','.rc']:continue
            if p.name=='symbols.stdout':continue # Full symbol inventory stays private.
            q=E/(folder+'--'+p.name+('.txt' if p.suffix in ['.stdout','.stderr'] else ''))
            q.write_text(sanitize(p.read_text()))
            public.append({'path':q.name,'source_alias':'G08_PRIVATE/'+str(p.relative_to(D/'.private')),
                           'raw_sha256':sha(p),'public_sha256':sha(q),'transformation':'literal path aliases only'})
    dump(E/'raw-index.json',{'base':'G08/.private (persistent lane directory; not a remote archive)','files':raw})
    dump(E/'sanitization-index.json',public)
    outer=base/'apk-extractor/outer-rea'; ledger=[]
    for p in sorted(outer.glob('*.json')):
        d=json.loads(p.read_text()); s=d.get('structuredContent',{})
        row={'alias':'COMMERCIAL_PRIVATE/apk-extractor/outer-rea/'+p.name,'sha256':sha(p),'bytes':p.stat().st_size,
             'executed_by':'outer(codex)','analyzed_by':'inner(codex)','evidence_id':s.get('evidence_id')}
        if s.get('subject'):
            assert s['subject']['digest']['sha256']=='51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5'
            row['subject_sha256']=s['subject']['digest']['sha256'];row['parameters']=s.get('parameters')
        ledger.append(row)
    dump(E/'rea-ledger.json',{'files':ledger,'address_rule':'observed = ELF VA + 0x100000 for this Ghidra session',
       'check_end':{'ELF_VA':'0x115be0','observed':'0x215be0','finding':'numDisk at +4 checked first; commentLen at +20 must be zero'},
       'parse_end':{'ELF_VA':'0x115e28','observed':'0x215e28','finding':'fseek(start+length-22), fread22, CheckEndDir; no backwards scan'},
       'limits':'Pseudocode/assembly corroborate source branches, not source-build byte reproduction. Wrong-address response remains private and indexed.'})
    log=base/'first-launch/window-outer-02/shards/20261021T155849-deb027d2/5ea34a4500000000000000001123012c/genshin/install-hilog.txt'
    lines=log.read_text().splitlines(); numbers=[162,164,278,280,281,282,283,285,286]
    dump(E/'install-first-fatal.json',{'source_alias':'COMMERCIAL_PRIVATE/'+str(log.relative_to(base)),
         'sha256':sha(log),'bytes':log.stat().st_size,'lines':[{'line':n,'text':sanitize(lines[n-1])} for n in numbers]})
    snapshots=D/'source-snapshots';snapshots.mkdir(exist_ok=True)
    sources=[]
    for name in ['project.spec.md','t8-apk-extractor.spec.md']:
        p=main/'specs/commercial-game-round1'/name;q=snapshots/name;q.write_bytes(p.read_bytes())
        sources.append({'source':'MAIN/specs/commercial-game-round1/'+name,'snapshot':'source-snapshots/'+name,'sha256':sha(q)})
    dump(E/'contract-sources.json',sources)
    dump(D/'results.json',{'status':'OFFLINE_SOURCE_REPRO_AND_BOUNDARY_TESTS_PASS',
       'predicted_key':'genshin','game_runtime':'NOT_STARTED','device_install':'NOT_TESTED_WITH_PATCH',
       'input_sha256':'abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc',
       'input_bytes':513290344,'deployment_library_sha256':'51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5',
       'original_source_sha256':sha(D/'sources/zip_file.cpp'),'candidate_source_sha256':sha(D/'sources/zip_file.comment-compatible.cpp'),
       'replay':'evidence/replay-03--receipt.json','boundaries':'evidence/boundaries-03--results.json',
       'zip_layout':'evidence/static-02--zip-audit.stdout.txt','first_error':'evidence/install-first-fatal.json',
       'rea':'evidence/rea-ledger.json','historical_candidate':'3ab88482da9ecc7e98683e4901da1737134059c5719a89d4edbbb2fba112bbe4',
       'historical_candidate_status':'REJECTED_BY_PEER_BOUNDARIES; original successful exact-input replay retained',
       'limits':['Host shims replace dependencies, not ZipFile parser logic; nonparallel Open only.',
                 'No APK rewrite, signature verification change, device build/deploy, extraction payload or game validation.',
                 'BaseExtractor original full source and complete libinstalls reproducible build are not established here.',
                 'Remaining ZIP extra-field bytes are counted but not interpreted as a failure.',
                 'No claim that all malformed ZIPs are covered or this is a complete ZIP security audit.']})
    print('Published actual replay-03 and boundaries-03; private originals unchanged')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--main',type=Path,required=True)
    p.add_argument('--private-base',type=Path,default=Path.home()/'.local/share/westlake/commercial-game-20261021')
    a=p.parse_args();publish(a.main.resolve(),a.private_base.resolve())
