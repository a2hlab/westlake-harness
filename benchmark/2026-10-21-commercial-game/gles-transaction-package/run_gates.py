#!/usr/bin/env python3
"""Persist original offline gate argv/stdout/stderr/rc as each process executes."""
import argparse, datetime, json, os, re, subprocess, sys
from pathlib import Path
from inspect_inputs import sha, save
HERE=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--main',required=True,type=Path);ap.add_argument('--assembly',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--oatdump',type=Path);ap.add_argument('--lab-home');ap.add_argument('--lab-home-from-provenance',action='store_true');ap.add_argument('--only',choices=['u7','native']);a=ap.parse_args()
    main=a.main.resolve(); root=a.assembly.resolve(); out=a.out.resolve();out.mkdir(parents=True,exist_ok=False); scripts=main/'scripts/lab';p=root/'candidate';b=root/'baseline';env=os.environ.copy();env.update(WORKSPACES=str(main.parent),WESTLAKE_HARNESS=str(main),WESTLAKE_DEPLOY_REPO=str(main),PYTHONDONTWRITEBYTECODE='1')
    commands=[('u7-dry-run',[sys.executable,str(scripts/'u7_executor.py'),'--dry-run','--package',str(p),'--baseline-native',str(b/'native'),'--out',str(out/'u7-plan.json')]),('static',[sys.executable,str(scripts/'generation_static_checks.py'),'--package',str(p),'--baseline',str(b),'--policy',str(p/'g20-static-policy.unsigned.json'),'--out',str(out/'static.json')])]
    for kind,package in [('candidate',p),('baseline',b)]:
        commands += [('native-'+kind,[sys.executable,str(scripts/'native_predeploy.py'),'--package',str(package/'native'),'--inputs',str(package/'native/native-checks/native-gates.json')]),('frozen-'+kind,[sys.executable,str(scripts/'check_frozen.py'),'--package',str(package/'native')])]
    if a.lab_home and a.lab_home_from_provenance: raise ValueError('Choose explicit LAB_HOME or pinned provenance')
    if a.lab_home: env['LAB_HOME']=a.lab_home
    if a.lab_home_from_provenance:
        source=main.parent/'westlake-inputs/aosp-14.0.0_r1-src/SOURCE.txt'
        match=re.search(r'hw248:([^\s,]+?)/aosp-14\.0\.0_r1-art',source.read_text())
        if not match: raise ValueError('LAB_HOME absent from actual hw248 provenance')
        env['LAB_HOME']=match.group(1)
        save(out/'lab-home-provenance.json',{'source':str(source),'sha256':sha(source),'LAB_HOME':env['LAB_HOME']})
    if a.oatdump: commands[0][1].extend(['--oatdump',str(a.oatdump.resolve())])
    if a.only=='u7': commands=commands[:1]
    if a.only=='native': commands=[r for r in commands if r[0].startswith('native-')]
    records=[]
    for name,argv in commands:
        record={'argv':argv,'started_at':datetime.datetime.now().astimezone().isoformat(),'device_io':False};save(out/(name+'.argv.json'),record)
        with (out/(name+'.stdout')).open('wb') as stdout,(out/(name+'.stderr')).open('wb') as stderr:
            try: rc=subprocess.run(argv,env=env,stdout=stdout,stderr=stderr,timeout=240).returncode
            except subprocess.TimeoutExpired:rc=124
        record.update(rc=rc,ended_at=datetime.datetime.now().astimezone().isoformat());save(out/(name+'.receipt.json'),record);(out/(name+'.rc')).write_text(str(rc)+'\n');records.append(record);print(name+' rc='+str(rc),flush=True)
    save(out/'records.json',records)
if __name__=='__main__':main()
