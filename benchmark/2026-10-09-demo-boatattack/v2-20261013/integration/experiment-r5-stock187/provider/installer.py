"""Narrow Boat placement adapter: reuse reviewed restore-v6 backup/place executor.
No launch, reboot, runtime bind or installation. Boot worker owns exactly six binds.
"""
import argparse, hashlib, importlib.util, json, os, re, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
if 'WORKSPACES' not in os.environ:
    for repository in HERE.parents:
        if (repository/'scripts/lab/lab_paths.py').is_file():
            os.environ['WORKSPACES']=str(repository.parent);break
    else:raise ValueError('WORKSPACES is required outside a repository')
ROOT='/data/westlake-demo/u13/boat-v2-20261013-r4'
CFG='/system/etc/init/00_westlake_u13_recover-v3.cfg'

def need(ok,msg):
    if not ok: raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def resolve(p):return Path(os.path.expandvars(str(p).replace('$PACKAGE',str(HERE))))
def core_for(plan):
    ref=plan['core'];path=resolve(ref['path']);need(sha(path)==ref['sha256'],'frozen executor drift')
    spec=importlib.util.spec_from_file_location('boat_existing_placement_core',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.ROOT=ROOT;m.CFG=CFG;m.HERE=HERE;m.SERIAL=plan['serial'];return m

def validate(plan,core):
    ref=plan['candidate_contract'];path=resolve(ref['path'])
    need(sha(path)==ref['sha256'],'candidate contract drift')
    spec=importlib.util.spec_from_file_location('boat_61b_contract',path);contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
    contract.validate(plan,core)
    allowed={ROOT+'/'+n for n in ['recover-v3-boat.sh','worker.sh','binds.tsv']}|{ROOT+'/sources/'+n for n in ['liboh_adapter_bridge.so','oh-adapter-runtime.jar','libunity.so','libil2cpp.so','libwestlake_bionic_signal_box.so','libandroid.so']}|{CFG}
    need(len(plan['members'])==10 and {r['target'] for r in plan['members']}==allowed,'exact ten placement objects')
    need(plan['members'][-1]['target']==CFG,'activate cfg last')
    need(len(plan['binds'])==6 and len({r['target'] for r in plan['binds']})==6,'exact six bind objects')
    for row in plan['members']:
        need(sha(resolve(row['source']))==row['sha256'],'member source SHA');core.metadata(row['after'],'after')
        b=row['before'];need(type(b['exists']) is bool,'unknown before')
        if b['exists']:
            core.metadata(b,'before');need(sha(resolve(b['source']))==b['sha256'],'CAS preimage mismatch')
        else:need(b.get('proof'),'absence evidence required')
    need({r['target'] for r in plan['directories']}=={ROOT,ROOT+'/sources'},'only two fresh package directories')
    for row in plan['directories']:need(row['before']['exists'] is False and row['before'].get('proof'),'fresh directory evidence');core.metadata(row['after'],'directory')
    for tool in plan['tools'].values():need(sha(resolve(tool['path']))==tool['sha256'],'transport pin drift')
    need(plan['installer_sha256']==sha(Path(__file__)),'installer self-pin')

def no_consumers(plan,dev):
    text=dev.shell('boat-consumer-readonly','ps -A -o PID,PPID,UID,NAME')
    lines=[line.split() for line in text.splitlines()]
    need(lines and lines[0][:3]==['PID','PPID','UID'],'process table header missing')
    for row in lines[1:]:
        need(len(row)>=4 and all(v.isdecimal() for v in row[:3]),'ambiguous process row')
        need(int(row[2])!=plan['boat_uid'],'Boat UID still consuming candidate; outer cold_stop required')

def audit_rows(plan,auth):
    rows=auth['retained_audit'];need(isinstance(rows,list),'retained audit required')
    allowed={ROOT+'/cfg-stage-'+row['sha256'] for row in plan['members'] if row['target']==CFG}
    allowed.add(ROOT+'/cfg-stage-'+plan['members'][-1]['before']['sha256'])
    for boot in {auth['boot_id'],plan['boot_id']}:
        allowed.update(ROOT+'/boat-'+boot+suffix for suffix in ['.log','.receipt','.intents'])
    need(len({r['target'] for r in rows})==len(rows),'duplicate audit object')
    for row in rows:
        need(row['target'] in allowed and row['exists'] is True,'unknown retained file')
        need(re.fullmatch('[a-f0-9]{64}',row['sha256']),'audit SHA missing')
        need({k:row[k] for k in ['mode','uid','gid','label']}=={'mode':'644','uid':0,'gid':0,'label':'u:object_r:data_file:s0'},'audit metadata differs')
    return {r['target']:r for r in rows}

def audit_verify(plan,dev,out,core,expected,with_payload):
    paths=set(dev.shell('audit-enumerate','set -eu; test -d '+core.q(ROOT)+'; test ! -L '+core.q(ROOT)+'; find '+core.q(ROOT)+' -print').splitlines())
    dirs={r['target'] for r in plan['directories']};allowed=dirs|set(expected)
    if with_payload:
        allowed|={r['target'] for r in plan['members'] if r['target']!=CFG and dev.probe(r['target'])['exists']}
    need(paths==allowed,'unknown/missing package member or mount: '+repr(sorted(paths^allowed)))
    for path,row in expected.items():need(core.equal(dev.probe(path),row),'audit bytes/metadata drift: '+path)
    mountinfo=dev.shell('audit-mounts','cat /proc/self/mountinfo')
    for line in mountinfo.splitlines():
        fields=line.split();need(len(fields)>6,'bad mount row')
        need(not (fields[4]==ROOT or fields[4].startswith(ROOT+'/')),'foreign mount in audit directory')
    for n,row in enumerate(plan['directories']):
        own=core.read(out/('directory-created-%03d.json'%n));need(own['target']==row['target'] and own['plan_sha256']==plan['_sha'],'directory journal drift')
        actual=dev.shell('audit-directory-meta',"set -eu; test ! -L "+core.q(row['target'])+"; stat -c '%a:%u:%g:%C:%d:%i' "+core.q(row['target']))
        wanted=':'.join(str(row['after'][k]) for k in ['mode','uid','gid','label'])+':'+own['identity'];need(actual==wanted,'directory identity/metadata drift')

def rollback_preflight(plan,dev,out,core):
    """Original core intent/observation rule; all ten backups checked before first unmount."""
    tx=core.read(out/'transaction.json')
    expected=[dict(target=r['target'],before=r['before'],backup='backup-%03d'%n if r['before']['exists'] else None,candidate_sha256=r['sha256']) for n,r in enumerate(plan['members'])]
    need(tx.get('plan_sha256')==plan['_sha'] and tx.get('serial')==plan['serial'] and tx.get('boot_id')==plan['boot_id'],'transaction identity drift')
    need(tx.get('backups')==expected,'transaction exact members differ')
    for row in expected:
        if row['before']['exists']:
            backup=out/row['backup'];need(backup.is_file() and sha(backup)==row['before']['sha256'],'backup missing/drift')
    current={}
    for n,row in enumerate(expected):
        observed=dev.probe(row['target']);current[row['target']]=observed;known_partial=False
        failure_file=out/('failed-%03d.json'%n)
        if failure_file.exists():
            failure=core.read(failure_file);intent_file=out/('intent-%03d.json'%n)
            expected_intent={'plan_sha256':plan['_sha'],'serial':plan['serial'],'boot_id':plan['boot_id'],'target':row['target'],'candidate_sha256':row['candidate_sha256'],'before':row['before']}
            need(intent_file.is_file() and core.read(intent_file)==expected_intent and failure.get('intent_sha256')==sha(intent_file),'failed operation intent mismatch')
            need(failure.get('plan_sha256')==plan['_sha'] and failure.get('target')==row['target'],'failed operation binding')
            known_partial=failure.get('observation') is not None and core.equal(observed,failure['observation'])
        candidate={'exists':True,'sha256':row['candidate_sha256'],**plan['members'][n]['after']}
        need(core.equal(observed,row['before']) or core.equal(observed,candidate) or known_partial,'foreign/unobserved partial replacement: '+row['target'])
    return tx,current

def rollback(plan,dev,out,core,auth):
    # Reuse per-file backup records from core.apply. Exact cfg restored; no RouteB stop/quarantine code.
    cleanup=auth['cleanup_receipt'];cleanup_path=resolve(cleanup['path']);need(sha(cleanup_path)==cleanup['sha256'],'cleanup receipt pin');clean=read(cleanup_path)
    need(clean['serial']==plan['serial'] and clean['boot_id']==auth['boot_id'] and clean['package']==plan['boat_package'] and clean['uid']==plan['boat_uid'] and clean['remaining_processes']==[] and clean['success'] is True,'outer cleanup receipt binding')
    tx,current=rollback_preflight(plan,dev,out,core)
    core.check_identity(dev,plan);no_consumers(plan,dev)
    retained=audit_rows(plan,auth);audit_verify(plan,dev,out,core,retained,True)
    # Remove only owned six-bind tops, in reverse donor order. No global unmount or process signals.
    for row in reversed(plan['binds']):
        no_consumers(plan,dev)
        target=row['target'];source=row['source'];bound=dev.probe(target)
        if core.equal(bound,row['before']):continue
        need(core.equal(bound,{'exists':True,'sha256':row['sha256'],**row['after']}),'foreign bind bytes/metadata: '+target)
        script='set -eu; test "$(readlink /proc/self/ns/mnt)" = "$(readlink /proc/1/ns/mnt)"; test "$(stat -c %d:%i '+core.q(target)+')" = "$(stat -c %d:%i '+core.q(source)+')"; '
        # Source device+inode equality plus exact candidate SHA identifies this bind; foreign tops reject.
        dev.shell('owned-boat-unbind',script+'umount '+core.q(target))
        need(core.equal(dev.probe(target),row['before']),'revealed preimage differs: '+target)
    # Recheck the same exact candidate/partial observation immediately before each restoration.
    for row in reversed(tx['backups']):
        before=row['before'];target=row['target'];now=dev.probe(target)
        need(core.equal(now,current[target]),'rollback target changed after guard: '+target)
        if core.equal(now,before):continue
        if before['exists']:core.place(dev,{'target':target,'source':str(out/row['backup']),'sha256':before['sha256'],'after':{k:before[k] for k in ['mode','uid','gid','label']}})
        else:
            dev.shell('remove-owned-boat-file','set -eu; ! grep -F '+core.q(' '+target+' ')+' /proc/self/mountinfo; rm '+core.q(target))
            need(not dev.probe(target)['exists'],'remove readback')
    before=plan['members'][-1]['before'];stage=ROOT+'/cfg-stage-'+before['sha256']
    if dev.probe(stage)['exists']:retained[stage]={'target':stage,'exists':True,'sha256':before['sha256'],'mode':'644','uid':0,'gid':0,'label':'u:object_r:data_file:s0'}
    audit_verify(plan,dev,out,core,retained,False)
    for row in plan['binds']:need(core.equal(dev.probe(row['target']),row['before']),'restored bind drift')
    for row in plan['preserved']:need(core.equal(dev.probe(row['target']),row['before']),'protected controls drift')
    ref=plan['baseline319'];need(sha(resolve(ref['path']))==ref['sha256'],'baseline source drift');expected=read(resolve(ref['path']))['expected'];need(len(expected)==319,'full baseline required')
    actual={};paths=list(expected)
    for offset in range(0,len(paths),24):
        text=dev.shell('restored-full319','sha256sum '+' '.join(core.q(p) for p in paths[offset:offset+24]));rows=re.findall(r'^([a-f0-9]{64})\s+(/\S+)$',text,re.M)
        need(len(rows)==len(paths[offset:offset+24]),'missing restored SHA');actual.update({p:h for h,p in rows})
    need(actual==expected,'restored 319 mismatch');core.check_identity(dev,plan)
    for row in plan['prerequisites']:need(dev.probe(row['target']).get('sha256')==row['sha256'],'protected prerequisite drift')
    core.save(out/('rollback-'+str(time.time_ns())+'.json'),{'state':'RESTORED_RETAINED_AUDIT_VERIFIED','success':True,'files_and_binds_restored':True,'baseline319_equal':True,'retained_audit':list(retained.values()),'retained_directories':plan['directories'],'user_data_deleted':False,'app_signals':0,'reboots':0,'live_parent_library_reload_claimed':False})
    return 0

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--action',choices=['apply','rollback'],default='apply');ap.add_argument('--execute',action='store_true');ap.add_argument('--authorization',type=Path);ap.add_argument('--authorization-sha256');ap.add_argument('--out',type=Path);a=ap.parse_args()
    plan=read(a.plan);plan['_sha']=sha(a.plan);core=core_for(plan);validate(plan,core)
    if not a.execute:print(json.dumps({'status':'PREVIEW','members':10,'boot_binds':6,'device_calls':0,'plan_sha256':plan['_sha']}));return 0
    need(plan['execution_enabled'] is True and not plan.get('synthetic') and not plan.get('pending_capture'),'disabled/synthetic/incomplete plan');need(a.authorization and sha(a.authorization)==a.authorization_sha256,'independent authorization pin');auth=read(a.authorization)
    need(auth['approved_by']=='outer(codex)' and auth['plan_sha256']==plan['_sha'] and auth['serial']==plan['serial'],'authorization binding')
    need(auth['origin_boot_id']==plan['boot_id'] and auth['expires_epoch']>time.time(),'origin/expiry');need(auth['action']==a.action,'action authorization')
    need(re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',auth['boot_id']),'boot identity');plan['_active_boot']=auth['boot_id']
    if a.action=='apply':need(auth['boot_id']==plan['boot_id'],'apply requires captured boot')
    need(a.out is not None,'transaction output required')
    if a.action=='apply':a.out.mkdir(parents=True,exist_ok=False)
    else:need(a.out.is_dir(),'original backups required')
    lock=resolve(plan['tools']['lock']['path'])
    class GuardedDevice(core.Device):
        def send(self,name,source,target):
            super().send(name,source,target)
            if name=='cfg-stage':
                need(target.startswith(ROOT+'/cfg-stage-'),'unexpected cfg stage')
                self.shell('cfg-stage-audit-metadata','set -eu; chown 0:0 '+core.q(target)+'; chmod 644 '+core.q(target)+'; chcon u:object_r:data_file:s0 '+core.q(target))
        def command(self,name,argv):
            need(auth['expires_epoch']>time.time(),'authorization expired')
            need(sha(lock)==plan['tools']['lock']['sha256'],'lock tool drift')
            held=subprocess.run(['bash',str(lock),'held',plan['serial']],capture_output=True,text=True,timeout=15)
            need(held.returncode==0 and not held.stderr and held.stdout.strip()==auth['holder'],'external lock holder mismatch')
            return super().command(name,argv)
    logs=a.out/('transport-'+str(time.time_ns()));logs.mkdir(exist_ok=False);dev=GuardedDevice(plan,logs)
    identity_ref=plan['boat_identity_program'];identity_path=resolve(identity_ref['path'])
    need(sha(identity_path)==identity_ref['sha256'],'UID reader independent pin')
    spec=importlib.util.spec_from_file_location('boat_uid_live',identity_path);identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity)
    identity.fresh(plan,dev)
    original_fresh=core.fresh
    def fresh_with_uid(device,checked_plan):
        original_fresh(device,checked_plan)
        identity.fresh(checked_plan,device)
    core.fresh=fresh_with_uid  # Both original all-preimage rounds, including immediately before the first write.
    if a.action=='apply':
        dev.shell('boat-switch-absence','test ! -e /data/westlake-demo/u13/BOAT_DISABLED && test ! -L /data/westlake-demo/u13/BOAT_DISABLED')
        core.apply(plan,dev,a.out)
        # core.apply already verifies every preserved object before writing placed.json.
        core.check_identity(dev,plan)
        core.save(a.out/'preserved-verified.json',{'plan_sha256':plan['_sha'],'serial':plan['serial'],'boot_id':plan['boot_id'],'count':len(plan['preserved']),'success':True})
    else:return rollback(plan,dev,a.out,core,auth)
    return 0
if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,KeyError,OSError,TypeError) as e:print('BOAT REJECT: '+str(e),file=sys.stderr);raise SystemExit(2)
