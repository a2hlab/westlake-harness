#!/usr/bin/env python3
"""Three-file cold-boot successor. Reuses W3 backup/preflight; never rebinds or reboots."""
import argparse, hashlib, importlib.util, json, os, re, subprocess, time, uuid
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = '/data/westlake-demo/u13/boat-v2-20261013-r4'
RT = '/system/android/lib64/liboh_android_runtime.so'
OLD = '94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354'
SERIAL = '5ea34a4500000000000000001123012c'
BOOT = '14a4b932-f396-40fa-864c-543c47b99875'
META = ('mode','uid','gid','label')
def need(ok, msg):
    if not ok: raise ValueError(msg)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def resolve(p): return Path(os.path.expandvars(str(p)))
def ref(p):
    p=Path(p).resolve(); ws=Path(os.environ['WORKSPACES']).resolve()
    return {'path':'$WORKSPACES/'+str(p.relative_to(ws)), 'sha256':sha(p)}
def load(r, name):
    p=resolve(r['path']); need(sha(p)==r['sha256'], name+' pin')
    s=importlib.util.spec_from_file_location(name,p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def derive(table, worker, candidate):
    need(re.fullmatch('[a-f0-9]{64}',candidate) and candidate!=OLD,'new runtime SHA required')
    rows=table.splitlines(keepends=True); need(len(rows)==7,'seven table rows')
    hit=[i for i,r in enumerate(rows) if r.split('\t')[1]==RT]; need(len(hit)==1,'unique runtime row')
    parts=rows[hit[0]].rstrip('\n').split('\t'); need(len(parts)==6 and parts[3]==OLD,'old runtime table pin')
    parts[3]=candidate; rows[hit[0]]='\t'.join(parts)+'\n'; newtable=''.join(rows)
    old_table=hashlib.sha256(table.encode()).hexdigest(); new_table=hashlib.sha256(newtable.encode()).hexdigest()
    need(worker.count('TABLE_SHA='+old_table)==1 and worker.count(OLD)==1,'worker exact two substitutions')
    newworker=worker.replace('TABLE_SHA='+old_table,'TABLE_SHA='+new_table).replace(OLD,candidate)
    return newtable,newworker

def prepare(a):
    main=resolve(a.main); cap=main/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-interactive-readonly/control'
    w3=main/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/candidate-window3'
    for r in read(HERE/'source-pins.json'): need(sha(resolve(r['path']))==r['sha256'],'actual capture pin')
    capture=read(cap/'capture.json'); need(capture['serial']==SERIAL and capture['metadata_rc']==0,'capture identity')
    metatext=(cap/'metadata.stdout.txt').read_text(); lines=metatext.splitlines(); need(lines[-1]==BOOT,'capture boot')
    need(sha(a.runtime)==a.runtime_sha256,'candidate runtime pin')
    table,worker=derive((cap/'binds.tsv').read_text(),(cap/'worker.sh').read_text(),a.runtime_sha256)
    wp=read(w3/'plan.json'); need(wp['serial']==SERIAL and wp['boat_uid']>10000,'W3 board/UID')
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'binds.tsv').write_text(table); (a.out/'worker.sh').write_text(worker)
    original={r['target']:r for r in wp['members']}
    targets=[ROOT+'/sources/liboh_android_runtime.so',ROOT+'/binds.tsv',ROOT+'/worker.sh']
    sources=[a.runtime,a.out/'binds.tsv',a.out/'worker.sh']; rows=[]
    for target,source in zip(targets,sources):
        old=original[target]; before=dict(exists=True,sha256=old['sha256'],**old['after'])
        before['source']=old['source'] if target==targets[0] else ref(cap/Path(target).name)['path']
        need(sha(resolve(before['source']))==before['sha256'],'original CAS')
        if target!=targets[0]:
            n=next(i for i,s in enumerate(lines) if s.endswith('  '+target)); need(lines[n].split()[0]==before['sha256'],'actual control SHA')
            need(lines[n+1].startswith(':'.join(str(before[k]) for k in META)+':'),'actual metadata')
        rows.append(dict(target=target,source=ref(source)['path'],sha256=sha(source),before=before,after=old['after']))
    # Runtime metadata/inode comes from the independent live read, not the historical placement plan.
    probe=main/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-interactive-readonly/probe.stdout.txt'; text=probe.read_text()
    need(text.splitlines()[0]==BOOT and OLD+'  '+targets[0] in text and '755 0 0 66352:95228' in text and 'u:object_r:system_lib_file:s0 '+targets[0] in text,'actual runtime source evidence')
    preserved=[]
    for row in wp['members']:
        if row['target'] not in targets: preserved.append(dict(target=row['target'],before=dict(exists=True,sha256=row['sha256'],**row['after'])))
    preserved.append({'target':'/system/etc/init/01_westlake_u13_toutiao.cfg','before':{'exists':False}})
    expected=read(resolve(wp['baseline319']['path']))['expected']; need(len(expected)==319,'full319 membership')
    for b in wp['binds']:
        if b['target'] in expected: expected[b['target']]=b['sha256']
    p=dict(schema='boat-runtime-successor-v1',serial=SERIAL,boot_id=BOOT,boat_uid=wp['boat_uid'],boat_package=wp['boat_package'],execution_enabled=False,hdc=a.hdc,
           core=wp['core'],w3_installer=ref(w3/'package/installer.py'),bms=ref(main/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),
           executor=ref(Path(__file__)),members=rows,preserved=preserved,prerequisites=[r for r in wp['prerequisites'] if r['target']!=RT],directories=[],tools=wp['tools'],
           binds=wp['binds'],expected319=expected,evidence=read(HERE/'source-pins.json')+[ref(probe),ref(w3/'plan.json')],candidate_runtime_sha256=a.runtime_sha256)
    (a.out/'plan.disabled.json').write_text(json.dumps(p,indent=2)+'\n')
    print(json.dumps({'plan':str(a.out/'plan.disabled.json'),'sha256':sha(a.out/'plan.disabled.json'),'members':3,'binds_unchanged':7,'device_calls':0}))

def validate(p):
    need(p['serial']==SERIAL and p['boot_id']==BOOT,'origin identity')
    need(p['executor']['sha256']==sha(__file__),'self pin')
    targets=[ROOT+'/sources/liboh_android_runtime.so',ROOT+'/binds.tsv',ROOT+'/worker.sh']
    need([r['target'] for r in p['members']]==targets and p['directories']==[],'exact three members')
    for r in p['evidence']+[p['core'],p['w3_installer'],p['bms']]+list(p['tools'].values()): need(sha(resolve(r['path']))==r['sha256'],'input/tool pin')
    for r in p['members']:
        need(sha(resolve(r['source']))==r['sha256'] and sha(resolve(r['before']['source']))==r['before']['sha256'],'payload/preimage pin')
        need(r['after']=={k:r['before'][k] for k in META},'metadata changed')
    table,worker=derive(resolve(p['members'][1]['before']['source']).read_text(),resolve(p['members'][2]['before']['source']).read_text(),p['candidate_runtime_sha256'])
    need(resolve(p['members'][1]['source']).read_text()==table and resolve(p['members'][2]['source']).read_text()==worker,'nonminimal controls delta')
    need(p['members'][0]['sha256']==p['candidate_runtime_sha256'],'runtime mismatch')
    need(len(p['expected319'])==319 and len(p['binds'])==7,'membership')

def identity(c,dev,p,live_sha,bms):
    c.check_identity(dev,p)
    bundle=bms.parse_bundle(dev.shell('boat-bms','bm dump -n '+c.q(p['boat_package'])),p['boat_package'])
    need(bundle['uid']==p['boat_uid'],'actual Boat UID drift')
    for row in p['preserved']: need(c.equal(dev.probe(row['target']),row['before']),'preserved drift '+row['target'])
    for row in p['prerequisites']: need(dev.probe(row['target']).get('sha256')==row['sha256'],'prerequisite drift')
    expected=dict(p['expected319']); expected[RT]=live_sha
    for offset in range(0,319,24):
        paths=list(expected)[offset:offset+24]; got=dev.shell('full319','sha256sum '+' '.join(c.q(v) for v in paths))
        actual={path:s for s,path in re.findall(r'^([a-f0-9]{64})\s+(/\S+)$',got,re.M)}
        need(actual=={v:expected[v] for v in paths},'full319 mismatch')
    for row in p['binds']:
        s=live_sha if row['target']==RT else row['sha256']
        need(c.equal(dev.probe(row['target']),dict(exists=True,sha256=s,**row['after'])),'bind mismatch')

def restore_sources_guard(c,dev,p):
    # A failed cold boot may leave any prefix of the seven live binds. Those
    # ephemeral targets must not block restoration of this transaction's sources.
    c.check_identity(dev,p)
    for row in p['preserved']:
        need(c.equal(dev.probe(row['target']),row['before']),'persistent preserved drift '+row['target'])

def atomic_place(c,dev,row):
    """Only a new sibling inode is sent; mv replaces the name, never the mapped inode."""
    target=row['target']; before=dev.probe(target)
    expected=row.get('expected_before',row.get('before')); need(expected is not None and c.equal(before,expected),'atomic signed preimage drift')
    need(before['exists'],'atomic target absent')
    stage=target+'.successor-'+uuid.uuid4().hex; m=row['after']; q=c.q
    dev.shell('stage-absence','test ! -e '+q(stage)+' && test ! -L '+q(stage))
    dev.send('atomic-stage',c.resolve(row['source']),stage)
    dev.shell('stage-metadata','set -eu; chown '+q(str(m['uid'])+':'+str(m['gid']))+' '+q(stage)+'; chmod '+q(m['mode'])+' '+q(stage)+'; chcon '+q(m['label'])+' '+q(stage))
    need(c.equal(dev.probe(stage),dict(exists=True,sha256=row['sha256'],**m)),'stage readback')
    need(c.equal(dev.probe(target),before),'atomic preimage changed')
    dev.shell('atomic-replace','set -eu; '+('test "$(cat /proc/sys/kernel/random/boot_id)" = '+q(dev.expected_boot)+'; ' if hasattr(dev,'expected_boot') else '')+'test ! -L '+q(target)+'; test "$(sha256sum '+q(target)+" | cut -d' ' -f1)"+'" = '+q(before['sha256'])+'; test "$(stat -c '+q('%a:%u:%g:%C')+' '+q(target)+')" = '+q(':'.join(str(before[k]) for k in META))+'; test "$(stat -c %d:%i '+q(stage)+')" != "$(stat -c %d:%i '+q(target)+')"; mv '+q(stage)+' '+q(target))
    need(c.equal(dev.probe(target),dict(exists=True,sha256=row['sha256'],**m)),'atomic result')

def execute(a):
    p=read(a.plan); p['_sha']=sha(a.plan); validate(p)
    if not a.execute: print(json.dumps({'status':'PREVIEW','members':3,'device_calls':0})); return
    need(p['execution_enabled'] is True,'disabled plan')
    need(a.authorization and sha(a.authorization)==a.authorization_sha256,'independent auth pin'); auth=read(a.authorization)
    need(auth['approved_by']=='outer(codex)' and auth['plan_sha256']==p['_sha'] and auth['action']==a.action,'auth binding')
    need(auth['serial']==SERIAL and auth['origin_boot_id']==BOOT,'auth identity')
    need(re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',auth['boot_id']),'current boot')
    need(re.fullmatch('[a-f0-9]{64}',auth['live_runtime_sha256']),'observed live runtime SHA')
    if a.action=='rollback': need(auth.get('source_restore_only') is True,'explicit source-only rollback authorization')
    if a.action=='apply': need(auth['boot_id']==BOOT and auth['live_runtime_sha256']==OLD,'apply origin')
    p['_active_boot']=auth['boot_id']; c=load(p['core'],'successor_core'); c.SERIAL=SERIAL
    w3=load(p['w3_installer'],'successor_w3'); bms=load(p['bms'],'successor_bms')
    if a.action=='apply': a.out.mkdir(parents=True,exist_ok=False)
    else: need(a.out.is_dir(),'original transaction required')
    logs=a.out/('transport-'+str(time.time_ns())); logs.mkdir(exist_ok=False)
    class Device(c.Device):
        def command(self,name,argv):
            need(auth['expires_epoch']>time.time(),'authorization expired')
            lock=resolve(p['tools']['lock']['path']); need(sha(lock)==p['tools']['lock']['sha256'],'lock drift')
            held=subprocess.run(['bash',str(lock),'held',SERIAL],capture_output=True,text=True,timeout=15)
            need(held.returncode==0 and not held.stderr and held.stdout.strip()==auth['holder'] and auth['holder'].split()[0]=='outer(codex)','full held line mismatch')
            return super().command(name,argv)
    dev=Device(p,logs); dev.expected_boot=auth['boot_id']
    if a.action=='apply': identity(c,dev,p,auth['live_runtime_sha256'],bms)
    else: restore_sources_guard(c,dev,p)
    c.place=lambda dev,row: atomic_place(c,dev,row)
    if a.action=='apply': c.apply(p,dev,a.out)
    else:
        tx,current=w3.rollback_preflight(p,dev,a.out,c)
        for row in reversed(tx['backups']):
            c.check_identity(dev,p); need(c.equal(dev.probe(row['target']),current[row['target']]),'rollback drift')
            if c.equal(current[row['target']],row['before']): continue
            c.place(dev,dict(target=row['target'],source=str(a.out/row['backup']),sha256=row['before']['sha256'],after={k:row['before'][k] for k in META},expected_before=current[row['target']]))
        for row in p['members']: need(c.equal(dev.probe(row['target']),row['before']),'restored source mismatch')
    if a.action=='apply': identity(c,dev,p,auth['live_runtime_sha256'],bms)
    else: restore_sources_guard(c,dev,p)
    c.save(a.out/('source-'+a.action+'-'+str(time.time_ns())+'.json'),dict(state='SOURCE_STAGED_COLD_BOOT_REQUIRED' if a.action=='apply' else 'SOURCE_RESTORED_COLD_BOOT_REQUIRED',success=True,live_runtime_sha256=auth['live_runtime_sha256'],reboots=0,binds=0,app_signals=0,complete_runtime_rollback=False))

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    q=sub.add_parser('prepare');q.add_argument('--main',default='$WORKSPACES/westlake-harness');q.add_argument('--runtime',type=Path,required=True);q.add_argument('--runtime-sha256',required=True);q.add_argument('--hdc',required=True);q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('run');q.add_argument('--plan',type=Path,required=True);q.add_argument('--action',choices=['apply','rollback'],required=True);q.add_argument('--out',type=Path,required=True);q.add_argument('--execute',action='store_true');q.add_argument('--authorization',type=Path);q.add_argument('--authorization-sha256')
    a=ap.parse_args(); prepare(a) if a.cmd=='prepare' else execute(a)
if __name__=='__main__': main()
