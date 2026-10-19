#!/usr/bin/env python3
"""Package already-reviewed controls; no device access and no inferred identities."""
import argparse
import json
import re
import shutil
from pathlib import Path
from deploy import CFG, SERIAL, OLD_ROOT, require, sha, validate, uuid

def prepare(payload,before,boot,out):
    uuid(boot)
    require(not out.exists(),'new output required')
    roots=re.findall(r'^ROOT=[\"\']?([^\"\'\s]+)[\"\']?$',(payload/'config-common.sh').read_text(),re.M)
    require(len(roots)==1,'unique ROOT')
    root=roots[0]
    require(bool(re.fullmatch(re.escape('/data/westlake-demo/toutiao/recovery-attempts/icon-manual-')+r'[a-z0-9-]+',root)),'root scope')
    members={}
    for line in (payload/'members.tsv').read_text().splitlines():
        digest,name,mode=line.split()
        require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',name) is not None,'member path')
        require(name not in members,'duplicate member')
        require(sha(payload/name)==digest,'member SHA '+name)
        members[name]=mode
    for name in ('boot-entry.sh','config-common.sh'):
        members.setdefault(name,'550')
    for name in ('members.tsv','startup.env','startup.expected.sha256'):
        members.setdefault(name,'440')
    out.mkdir(parents=True);(out/'payload').mkdir()
    rows=[]
    for name,mode in sorted(members.items()):
        src=payload/name
        require(src.is_file() and not src.is_symlink() and not payload.is_symlink(),'source type')
        shutil.copyfile(src,out/'payload'/name)
        rows.append({'name':name,'mode':mode,'sha256':sha(src)})
    shutil.copyfile(before,out/'before.cfg')
    cfg=json.loads(before.read_text())
    require(cfg['services'][0]['path']==['/system/bin/sh',OLD_ROOT+'/boot-entry.sh'],'wrong base cfg')
    cfg['services'][0]['path'][1]=root+'/boot-entry.sh'
    (out/'after.cfg').write_text(json.dumps(cfg,indent=2)+'\n')
    plan={'serial':SERIAL,'cfg':CFG,'root':root,'boot':boot,'files':rows,'before_sha256':sha(out/'before.cfg'),'after_sha256':sha(out/'after.cfg')}
    validate(plan,out)
    (out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    return plan

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--payload',type=Path,required=True);p.add_argument('--before',type=Path,required=True)
    p.add_argument('--boot',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.payload,a.before,a.boot,a.out),indent=2))
if __name__=='__main__':main()
