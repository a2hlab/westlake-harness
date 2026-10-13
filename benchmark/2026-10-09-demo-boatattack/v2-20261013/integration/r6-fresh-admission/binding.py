#!/usr/bin/env python3
"""Offline admission: reuse the pinned main identity, never deploy or enable."""
import argparse, ast, hashlib, importlib.util, json, os, re, shlex, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
SERIAL='5ea34a4500000000000000001123012c'
ORIGIN_READER_SHA='12cbb7343cca361b08b2f6f69c3f1e857e9a1f32aad7cceaf9b3f4d4a8a049be'
PROOF='a4da342b3ed2fda8205e63758bb18ceacca82a2197d5b9851521dd885a5bb5fc'
MAIN_OUTPUTS={'full128':'1e2388e0db84bd53df17ba9b7b39cf0dadd817f623cd6f08f82aaafbcbd0d912','smoke10':'ba4ba12d970146babc2510d67314354e0058f13e1dd208d6aeaf79f0f4e05e77','smoke10_first':'d02bd112b150d752c3398eb56b828cb3e151502009a3e47f71aaf22dcf16ba10'}
UUID=re.compile(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}')
def need(v,s):
    if not v: raise ValueError(s)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def path(p): return Path(os.path.expandvars(str(p))).resolve()
def pin(p):
    p=Path(p).resolve();ws=path(os.environ['WORKSPACES'])
    return dict(path='$WORKSPACES/'+str(p.relative_to(ws)),sha256=sha(p))
def pinned(r):
    need(isinstance(r,dict) and set(r)=={'path','sha256'},'missing exact file reference')
    p=path(r['path']);need(sha(p)==r['sha256'],'file pin differs: '+str(p));return p
def load(r,name):
    p=pinned(r);sys.path.insert(0,str(p.parent))
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def artifact(q):
    need(q['schema']=='r6-fresh-admission/v1' and q['execution_enabled'] is False and q['serial']==SERIAL,'disabled5ea request')
    need(q['artifact']['proof']['sha256']==PROOF,'main a4da proof required')
    need(all(q['artifact'][k]['sha256']==v for k,v in MAIN_OUTPUTS.items()),'exact main disabled outputs required')
    p=read(pinned(q['artifact']['proof']));c=load(p['programs']['identity'],'original_r6_identity');c.validate(p)
    for name in ('full128','smoke10'):
        rd=read(pinned(q['artifact'][name]));need(rd['serial']==SERIAL and rd['execution_enabled'] is False,'main disabled round')
        need(rd['bindings']['candidate_proof']==q['artifact']['proof'],'main proof binding')
        for r in list(rd['bindings'].values())+rd['window_bindings']:pinned(r)
        need(len(rd['windows'])==(8 if name=='full128' else 13) and rd['apps']==128,'original window membership')
    first=read(pinned(q['artifact']['smoke10_first']));need(first['execution_enabled'] is False,'first plan disabled')
    rd=read(pinned(q['artifact']['smoke10']));need(q['artifact']['smoke10_first']==rd['window_bindings'][0],'only ten-control first plan')
    keys=[k for s in first['shards'] for k in path(s['keys_file']).read_text().split()]
    tiers=read(path(first['demo_shot_tiers']));need(len(keys)==10 and len(set(keys))==10,'ten distinct controls')
    need(all({r['key']:r for r in tiers['apps']}[k]['screenshot_seconds']==20 for k in keys),'all ten controls t20')
    return c,p

def command(r,allowed=(0,)):
    j=read(pinned(r['receipt']));out=pinned(r['stdout']).read_text();err=pinned(r['stderr']).read_text()
    need(j['rc'] in allowed and 0<j['started']<=j['finished'],'original command rc/chronology')
    return j,out,err

def origin(q,c,p):
    """Derive origin from pinned actual read bookends and four real recv records."""
    e=q['origin_evidence'];need(e['program']['sha256']==ORIGIN_READER_SHA,'original capture program pin')
    m=load(e['program'],'original_origin_capture');cap=read(pinned(e['capture']));probe=read(pinned(e['probe']))
    boot=cap['boot_id'];need(isinstance(boot,str) and UUID.fullmatch(boot),'origin boot malformed')
    need(cap['serial']==probe['serial']==SERIAL and cap['metadata_rc']==probe['rc']==0,'origin capture scope/status')
    need([r['remote'] for r in cap['files']]==m.FILES and len(e['recv_commands'])==4,'four real recv members')
    old=read(c.pinned(p['original_r4_proof']));placement=read(c.pinned(p['placement_plan']));members={r['target']:r for r in placement['members']}
    hdc=read(c.pinned(p['successor_plan']))['hdc']
    def shell(ref,script):
        j,out,err=command(ref)
        need(j['stdout_sha256']==sha(pinned(ref['stdout'])) and j['stderr_sha256']==sha(pinned(ref['stderr'])) and not err.strip(),'origin raw transport hashes/stderr')
        wrapped='/system/bin/sh -c '+shlex.quote('set -eu; '+script)+'; rc=$?; printf "\\nCAPTURE_RC=%s\\n" "$rc"'
        need(j['argv']==[hdc,'-t',SERIAL,'shell',wrapped],'original read-only capture argv')
        out=out.replace('\r','');hit=re.search(r'\nCAPTURE_RC=(\d+)\n?\Z',out);need(hit and hit[1]=='0','origin remote marker')
        body=out[:hit.start()].rstrip('\n')+'\n';lines=body.splitlines()
        need(lines[0]==lines[-1]==boot,'origin boot bookends differ')
        return j,body
    pj,raw=shell(e['probe_command'],m.PROBE);bj,before=shell(e['metadata_before_command'],m.METADATA);aj,after=shell(e['metadata_after_command'],m.METADATA)
    need(before==after and pj['finished']<=probe['epoch']<=bj['started'] and cap['epoch']>=aj['finished'],'origin capture chronology/bookends')
    need(probe['command']==m.PROBE and probe['stdout_sha256']==hashlib.sha256(raw.encode()).hexdigest(),'origin probe derived receipt')
    lines=before.splitlines();need(len(lines)==10,'complete metadata rows')
    last=bj['finished']
    for i,row in enumerate(cap['files']):
        remote=row['remote'];local=path(row['local']);need(row['rc']==0 and sha(local)==row['sha256']==old['expected'][remote],'actual recv/source identity')
        need(lines[1+2*i]==row['sha256']+'  '+remote,'metadata SHA/target')
        md=re.fullmatch(r'([0-7]{3,4}):(\d+):(\d+):(u:object_r:[^:]+:s0):(\d+):(\d+)',lines[2+2*i]);need(md,'metadata malformed')
        mode,uid,gid,label,_,_=md.groups();need(dict(mode=mode,uid=int(uid),gid=int(gid),label=label)==members[remote]['after'],'control metadata differs')
        j,out,err=command(e['recv_commands'][i]);need(j['stdout_sha256']==sha(pinned(e['recv_commands'][i]['stdout'])) and j['stderr_sha256']==sha(pinned(e['recv_commands'][i]['stderr'])) and not err.strip(),'recv raw hashes/status')
        argv=j['argv'];need(len(argv)==7 and argv[:6]==[hdc,'-t',SERIAL,'file','recv',remote],'real recv CLI')
        dest=Path(argv[-1]);dest=dest if dest.is_absolute() else path(os.environ['WORKSPACES'])/'westlake-harness'/dest
        need(dest.resolve()==local and last<=j['started']<=j['finished']<=aj['started'],'recv destination/chronology');last=j['finished']
    # Probe independently identifies the running947 source and ADC; not a full337 claim.
    for target in (m.ROOT+'/sources/liboh_android_runtime.so',m.ROOT+'/worker.sh','/system/android/lib64/liboh_android_runtime.so','/system/android/lib64/libandroid.so'):
        need(raw.splitlines().count(old['expected'][target]+'  '+target)==1,'origin probe SHA missing/drift')
    table=path(cap['files'][0]['local']).read_text()
    need(all(raw.splitlines().count(line)==1 for line in table.splitlines()),'actual seven-row table missing from probe')
    return boot,aj['finished']

def deployment(q,c,p):
    origin_boot,origin_finished=origin(q,c,p)
    boot=q['candidate_boot'];need(isinstance(boot,str) and UUID.fullmatch(boot) and boot!=origin_boot,'candidate boot pending/old')
    d=q['deployment'];need(isinstance(d,dict),'fresh deployment pending')
    planpath=pinned(d['plan']);plan=read(planpath);old=read(c.pinned(p['successor_plan']))
    need(plan['execution_enabled'] is True and plan['serial']==SERIAL and plan['boot_id']==origin_boot,'new actual plan/origin')
    # Runtime guards must be unchanged: only BOOT and offline prepare may differ.
    def guard_ast(source):
        tree=ast.parse(Path(source).read_text());tree.body=[n for n in tree.body if not (isinstance(n,ast.FunctionDef) and n.name=='prepare')]
        for n in tree.body:
            if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BOOT' for t in n.targets):n.value=ast.Constant('ORIGIN')
        return ast.dump(tree,include_attributes=False)
    exe=pinned(plan['executor']);need(guard_ast(exe)==guard_ast(c.pinned(p['successor_program'])),'new successor runtime guard changed')
    mod=load(plan['executor'],'fresh_successor');mod.validate(plan)
    for k in ('hdc','boat_uid','boat_package','core','w3_installer','bms','preserved','prerequisites','directories','tools','binds','expected319','candidate_runtime_sha256'):
        need(plan[k]==old[k],'stage guard/object differs: '+k)
    need(len(plan['members'])==len(old['members'])==3,'three staged controls')
    for r,o in zip(plan['members'],old['members']):
        for k in ('target','sha256','after'):need(r[k]==o[k],'stage artifact differs')
        need({k:v for k,v in r['before'].items() if k!='source'}=={k:v for k,v in o['before'].items() if k!='source'},'stage preimage differs')
    authpath=pinned(d['authorization']);a=read(authpath)
    need(a['approved_by']=='outer(codex)' and a['action']=='apply' and a['plan_sha256']==sha(planpath),'apply authorization')
    need(a['serial']==SERIAL and a['origin_boot_id']==a['boot_id']==origin_boot and a['live_runtime_sha256']==mod.OLD,'apply actual origin')
    txpath=pinned(d['transaction']);tx=read(txpath)
    need(tx['serial']==SERIAL and tx['boot_id']==origin_boot and tx['plan_sha256']==sha(planpath),'original transaction binding')
    need(len(tx['backups'])==3 and len(d['intents'])==len(d['placed_members'])==len(d['backups'])==3,'complete transaction records')
    for i,(r,b) in enumerate(zip(plan['members'],tx['backups'])):
        need(b==dict(target=r['target'],before=r['before'],backup='backup-%03d'%i,candidate_sha256=r['sha256']),'original backup record')
        need(sha(pinned(d['backups'][i]))==r['before']['sha256'],'real original backup bytes')
        need(read(pinned(d['intents'][i]))==dict(plan_sha256=sha(planpath),serial=SERIAL,boot_id=origin_boot,target=r['target'],candidate_sha256=r['sha256'],before=r['before']),'original intent')
        need(read(pinned(d['placed_members'][i]))==dict(target=r['target'],sha256=r['sha256']),'original member placement')
    need(read(pinned(d['placed']))==dict(state='PLACED_ONLY',ui_accepted=False,seal_signed=False,reboots=0),'original placed state')
    need(read(pinned(d['source_result']))==dict(state='SOURCE_STAGED_COLD_BOOT_REQUIRED',success=True,live_runtime_sha256=mod.OLD,reboots=0,binds=0,app_signals=0,complete_runtime_rollback=False),'original source-only result')
    apply,_,_=command(d['apply_command'])
    argv=apply['argv'];need(len(argv)==14 and path(argv[1])==exe and argv[2:]==['run','--plan',str(planpath),'--action','apply','--execute','--authorization',str(authpath),'--authorization-sha256',sha(authpath),'--out',str(txpath.parent)],'actual original apply CLI')
    need(origin_finished<=apply['started'] and apply['finished']<a['expires_epoch'],'apply authorization expired')
    intent=read(pinned(d['boot_intent']));result=read(pinned(d['boot_result']))
    need(intent['serial']==SERIAL and intent['origin_boot']==origin_boot and intent['epoch']>=apply['finished'],'actual cold boot intent')
    ia=intent['authorization'];need(ia['approved_by']=='outer(codex)' and ia['serial']==SERIAL and ia['origin_boot_id']==origin_boot and ia['allow_candidate_boot'] is True,'boot authorization')
    need(result['boot_id']==boot and result['ready'] is True,'actual new boot result')
    bootcmd,_,_=command(d['boot_command'],(0,1));need(bootcmd['argv']==[plan['hdc'],'-t',SERIAL,'target','boot'] and intent['epoch']<=bootcmd['started']<=bootcmd['finished']<=ia['experiment_expires_epoch'],'actual boot command')
    def raw(name,cmd):
        j,out,_=command(d[name]);script='/system/bin/sh -c '+shlex.quote(cmd)+'; rc=$?; printf "\\nR6_RC=%s\\n" "$rc"'
        need(j['argv']==[plan['hdc'],'-t',SERIAL,'shell',script] and bootcmd['finished']<=j['started']<=ia['experiment_expires_epoch'],'boot read protocol')
        out=out.replace('\r','');m=re.search(r'\nR6_RC=(\d+)\n?\Z',out);need(m and m[1]=='0','boot remote marker')
        return j,out[:m.start()].strip()
    ready,rt=raw('ready_command','cat /data/westlake-demo/u13/receipt.env; param get sys.westlake.demo.u13.ready; getenforce')
    bound,bt=raw('bound_command','cat '+mod.ROOT+'/boat-'+boot+'.receipt')
    need(rt==result['raw'] and bt==result['bound'],'raw boot receipt differs')
    need(all(x in [s.strip() for s in rt.splitlines()] for x in ('state=READY','layers=56','boot_id='+boot,'true','Permissive')),'READY56')
    need(all(x in [s.strip() for s in bt.splitlines()] for x in ('state=BOUND','layers=7','boot_id='+boot)),'BOUND7')
    return max(ready['finished'],bound['finished'])

def replay(q,c,p,out,after):
    origin_boot,_=origin(q,c,p)
    cap=read(pinned(q['fresh_capture']));need(cap['schema']=='r6-original-reader-capture/v1' and cap['serial']==SERIAL and cap['origin_boot']==origin_boot and cap['candidate_boot']==q['candidate_boot'] and cap['proof']==q['artifact']['proof'],'independent capture scope')
    need(cap['collector']==pin(HERE/'fresh_read.py') and cap['binding']==pin(HERE/'binding.py'),'fresh recorder implementation pin')
    rows=cap['commands'];need(rows and cap['started']>=after,'fresh read predates deployment')
    upstream=load(p['programs']['reader'],'frozen_reader');absence=load(p['programs']['absence_reader'],'frozen_absence');index=0;last=cap['started']
    def run(argv,**kwargs):
        nonlocal index,last
        need(index<len(rows),'missing raw read');r=rows[index];index+=1
        need(r['started']>=last and r['finished']>=r['started'],'read chronology');last=r['finished']
        recorded=r['argv'];need(recorded[:5]==argv[:5] and recorded[3]==SERIAL,'raw reader serial/transport')
        oldmark=re.findall(r'__(?:DEMO|BOAT_ABSENCE)_RC_[a-f0-9]{32}__',recorded[-1]);newmark=re.findall(r'__(?:DEMO|BOAT_ABSENCE)_RC_[a-f0-9]{32}__',argv[-1])
        need(len(oldmark)==len(newmark)==1 and recorded[-1].replace(oldmark[0],newmark[0])==argv[-1],'raw read argv differs')
        stdout=pinned(r['stdout']).read_text();stderr=pinned(r['stderr']).read_text()
        return SimpleNamespace(returncode=r['rc'],stdout=stdout.replace(oldmark[0],newmark[0]),stderr=stderr)
    # The original implementations still enforce whitelist, host rc and markers.
    with patch('subprocess.run',run):
        result=c.check(absence.with_absence(upstream.Reader)(out,SERIAL),p,out,origin_boot)
    need(index==len(rows) and last<=cap['finished'],'unexpected/trailing raw commands')
    need(result==read(pinned(cap['identity'])) and result['passed'] is True,'independent original check differs/fails')
    need(result['boot_before']==result['boot_after']==q['candidate_boot'],'candidate boot bookends')
    return result,len(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--request',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--replay',action='store_true');a=ap.parse_args()
    q=read(a.request);c,p=artifact(q);origin_boot,_=origin(q,c,p);a.out.mkdir(parents=True,exist_ok=False)
    result=dict(state='DISABLED_PENDING_FRESH_DEPLOYMENT',execution_enabled=False,device_calls=0,candidate_boot=q['candidate_boot'],origin_boot=origin_boot,origin_evidence=q['origin_evidence'],artifact=q['artifact'],pending=['actual new deployment receipt','actual cold boot','independent original fresh Reader'])
    if a.replay:
        after=deployment(q,c,p);identity,calls=replay(q,c,p,a.out,after)
        result.update(state='FRESH_BOUND_DISABLED',candidate_boot=q['candidate_boot'],origin_boot=origin_boot,identity=identity,recorded_read_calls=calls,pending=['root runtime/UI acceptance and explicit execution authorization'])
        result['request']=pin(a.request)
        result['observed_marker']={'boot_id':q['candidate_boot']}
    (a.out/'binding.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())
