"""Explicit full-SHA candidate identity; original 319 membership is never reduced.
Compile is local-only. The round hook uses the existing read-only Reader only.
"""
import argparse, hashlib, importlib.util, json, os, re, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[5])))
MAIN=WS/'westlake-harness'
R4=WS/'westlake-harness-t4/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/minimal-r4'
BASE=MAIN/'benchmark/2026-10-03-u14-stage-a-plan/inputs/recovery-61b.json'
UPSTREAM=MAIN/'benchmark/2026-10-09-demo-baseline/t3/verify_identity.py'
ADAPTER='/system/android/lib64/liboh_adapter_bridge.so'
JAR='/system/android/framework/oh-adapter-runtime.jar'
RUNTIME='/system/android/lib64/liboh_android_runtime.so'
ANDROID='/system/android/lib64/libandroid.so'
CHANGES={ADAPTER:'8ab85446f8b386c4a649576326d5f393669b3a22529874fb673eea7c3b1cd71e',JAR:'6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852',RUNTIME:'94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354',ANDROID:'adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130'}
PRIVATE={'libunity.so':'1bea0fae1e6e76db15f17fca2bfa91b9c303ce278d6a4dcfba6af233b68b64ac','libil2cpp.so':'f6b806b5c55e702b98caa2e85d2f9afb678bc47dcc4067017b33f5269afed746','libwestlake_bionic_signal_box.so':'7a931c79c0be28468bdd02a626a637431f2447f5fd0aba87176e5acdb071f5da'}
OWN='/data/westlake-demo/u13/boat-v2-20261013-r4'
CFG='/system/etc/init/00_westlake_u13_recover-v3.cfg'
ROUTEB='/system/etc/init/01_westlake_u13_toutiao.cfg'
SPARE='5ea34a4500000000000000001123012c'
LIB='/data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/lib/arm64-v8a/'
RUNTIME_PATTERNS=[r'/system/bin/appspawn-x',JAR,r'/system/android/lib64/[^/]+\.so',r'/system/lib64/westlake/route-a/[^/]+/[^/]+\.so',r'/system/lib64/(platformsdk/)?(libapk_installer|libbms\.z|libinstalls\.z)\.so']
BOOT_PATTERN=r'/system/android/framework/(arm64/[^/]+|(core-oj|core-libart|core-icu4j|okhttp|bouncycastle|apache-xml|adapter-mainline-stubs|framework|oh-adapter-framework)\.jar)'

def need(ok,msg):
    if not ok: raise ValueError(msg)
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def expand(p): return Path(str(p).replace('$WORKSPACES',str(WS)))
def portable(p):
    resolved=Path(p).resolve();workspace=WS.resolve()
    if resolved.is_relative_to(workspace):return '$WORKSPACES/'+str(resolved.relative_to(workspace))
    if resolved.is_relative_to(workspace.parent):return '$WORKSPACES/../'+str(resolved.relative_to(workspace.parent))
    return str(resolved)
def pin(p): return {'path':portable(p),'sha256':sha(p)}
def pinned(p):
    path=expand(p['path']); need(sha(path)==p['sha256'],'source pin drift: '+str(path)); return path

def fp(rows): return hashlib.sha256('\n'.join(sorted(h+'  '+p for p,h in rows.items())).encode()).hexdigest()
def parts(rows):
    runtime={p:h for p,h in rows.items() if any(re.fullmatch(x,p) for x in RUNTIME_PATTERNS)}
    boot={p:h for p,h in rows.items() if re.fullmatch(BOOT_PATTERN,p)}
    return runtime,boot

def valid_rows(rows):
    need(bool(rows),'empty SHA inventory')
    for p,h in rows.items():
        need(re.fullmatch(r'/(system|data)/[A-Za-z0-9_./+-]+',p) and '..' not in p.split('/'),'unsafe target: '+p)
        need(re.fullmatch('[a-f0-9]{64}',h) is not None,'not full SHA: '+p)

def generation(doc):
    value={k:doc[k] for k in ['serial','expected','absent_files','placement_plan','r4_freeze']}
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(doc):
    need(doc['schema']=='boat-candidate-identity/v4','schema')
    need(doc['serial']==SPARE,'this proof scope is 5ea only; 5cd/61b require full actual RouteB inventory')
    need(doc['baseline']==pin(BASE),'exact original baseline pin required')
    base=read(pinned(doc['baseline']))['expected']; need(len(base)==319,'original 319 inventory required')
    valid_rows(base); expected=dict(base)
    need(doc['replacements']=={p:{'before':base[p],'after':h} for p,h in CHANGES.items()},'only exact four replacements permitted')
    expected.update(CHANGES)
    extras=doc['additional_files']; need(len({r['target'] for r in extras})==len(extras),'duplicate extra target')
    for row in extras:
        p=row['target']; need(p not in expected,'extra overlaps baseline: '+p)
        need(sha(pinned(row['source']))==row['sha256'],'source/target SHA differs')
        expected[p]=row['sha256']
    valid_rows(expected)
    protected=read(pinned(doc['protected_files'])); valid_rows(protected)
    cfg=CFG
    current=pinned(doc['current_cfg']);need(sha(current)=='7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1','CURRENT cfg pin')
    need(protected.get(cfg)==sha(current),'cfg preimage protection missing')
    source_by_target={r['target']:pinned(r['source']) for r in extras}
    wanted=current.read_bytes().replace(b'"/system/etc/westlake-u13-recover-v3.sh"',b'"'+OWN.encode()+b'/recover-v3-boat.sh"').replace(b'"/system/etc/westlake-u13-boat-overlay.sh"',b'"'+OWN.encode()+b'/worker.sh"')
    need(wanted.count(b'"SYS_ADMIN"')==2,'two service caps expected')
    wanted=wanted.replace(b'"SYS_ADMIN"',b'"SYS_ADMIN",\n        "SYS_PTRACE"')
    need(source_by_target[cfg].read_bytes()==wanted,'cfg must be exact two paths plus two SYS_PTRACE additions')
    for target,digest in protected.items():
        if target not in CHANGES and target!=cfg:need(expected.get(target)==digest,'protected object drift: '+target)
    plan_path=pinned(doc['placement_plan']);plan=read(plan_path)
    need(sha(plan_path)=='8ee3a7e4ea6bb68a7482b3aafb635920bc1e1716a01cc2161b4acfc05a2a18b1','reviewed actual r4 placement pin')
    freeze=pinned(doc['r4_freeze']);need(sha(freeze)=='c72fa0b2f63a7a4a4da5431538bd0fe322108f1cd9e5037987ab802529204677','reviewed r4 freeze pin')
    need(plan['serial']==doc['serial'],'placement serial mismatch')
    members={r['target']:r for r in plan['members']};need(len(members)==11,'eleven placement objects required')
    for target,row in members.items():need(expected.get(target)==row['sha256'],'placement identity differs: '+target)
    need(len(plan['binds'])==7 and plan['binds'][-1]['target']==ANDROID and plan['binds'][-2]['target']==RUNTIME,'seven binds with runtime sixth/libandroid last required')
    for row in plan['binds']:
        need(expected.get(row['target'])==row['sha256']==expected.get(row['source']),'bind target/source identity differs')
        if row['target'] in base:need(row['before']['sha256']==base[row['target']],'bind baseline preimage differs')
    need(expected[OWN+'/worker.sh']=='3f1a464338ce5b2f4c4d93ed0dc0db9c5fdf52c1e3156fae4d7e9e056b6898c2','reviewed r4 worker required')
    need(expected[OWN+'/recover-v3-boat.sh']=='291451a1a3b821a5527e3c8619d932664d047e25116e9c653d185d2ea5ee878f','reviewed synchronous recover required')
    for name,h in PRIVATE.items():need(expected.get(LIB+name)==h,'missing Boat private SHA: '+name)
    for p in [CFG,'/system/etc/westlake-u13-recover-v3.sh',OWN+'/worker.sh',OWN+'/recover-v3-boat.sh',OWN+'/binds.tsv','/data/westlake-demo/u13/selinux-mode','/data/westlake-demo/u13/u13-recover-table.json','/data/westlake-demo/u13/u13-recover-table.tsv']:
        need(p in expected,'required control missing: '+p)
    for name,h in {**PRIVATE,'liboh_adapter_bridge.so':CHANGES[ADAPTER],'oh-adapter-runtime.jar':CHANGES[JAR],'liboh_android_runtime.so':CHANGES[RUNTIME],'libandroid.so':CHANGES[ANDROID]}.items():
        need(expected.get(OWN+'/sources/'+name)==h,'missing durable Boat source: '+name)
    absent=doc['absent_files'];need(len(absent)==1 and absent[0]['target']==ROUTEB and absent[0]['exists'] is False,'exact typed 5ea RouteB absence required')
    need(ROUTEB not in expected and ROUTEB not in protected,'absent RouteB cannot be a SHA row')
    evidence=read(pinned(absent[0]['evidence']))
    need(evidence['serial']==SPARE and {'target':ROUTEB,'before':{'exists':False}} in evidence['preserved'],'absence not grounded in actual serial-specific placement plan')
    need(expected['/system/etc/westlake-u13-recover-v3.sh']=='43491d3aae7dbded7fec2aee38a448087270261a795402c6955db6e7d5de0fae','CURRENT recovery only')
    need(expected[RUNTIME]==CHANGES[RUNTIME],'exact geometry runtime947 required')
    need(doc['expected']==expected,'complete candidate inventory mismatch')
    need(doc['generation_sha256']==generation(doc),'full generation digest mismatch')
    runtime,boot=parts({p:expected[p] for p in base})
    need(doc['fingerprints']=={'runtime_sha256':fp(runtime),'boot_sha256':fp(boot)},'full fingerprints differ')
    need(fp(parts(base)[0]).startswith('452447a4a0ba') and fp(parts(base)[1]).startswith('ee927db88a67'),'baseline fingerprint coverage mismatch')
    for p in doc['programs'].values(): pinned(p)
    need(doc['programs']['absence_reader']==pin(HERE/'absence_reader.py'),'absence reader pin differs')
    need(doc['programs']['identity']==pin(Path(__file__)),'identity self-pin differs')
    need(doc['programs']['reader']==pin(UPSTREAM),'reader pin differs')
    need(doc['serial'] in ('5cd1e3dd00000000000000000923012c','5ea34a4500000000000000001123012c','61b0657200000000000000000324012c'),'serial whitelist')
    return expected

def load_proof(path,digest):
    need(sha(path)==digest,'independent candidate proof pin differs'); d=read(path); validate(d); return d

def parse_hashes(text):
    rows={}
    for line in text.splitlines():
        m=re.fullmatch(r'([a-f0-9]{64})\s+(/\S+)',line.strip()); need(m is not None,'malformed SHA output')
        h,p=m.groups(); need(p not in rows,'duplicate SHA output'); rows[p]=h
    return rows

def check(reader,proof,out,boot_before):
    expected=validate(proof)
    def shell(cmd):
        rc,text=reader.shell(cmd); need(rc==0,'read rc nonzero: '+cmd); return text
    before=shell('cat /proc/sys/kernel/random/boot_id'); need(before!=boot_before,'not a post-reboot round')
    for row in proof['absent_files']:need(reader.absent(row['target']),'protected absence changed: '+row['target'])
    actual={}; paths=list(expected)
    for i in range(0,len(paths),24):
        group=paths[i:i+24]; got=parse_hashes(shell('sha256sum '+' '.join(group))); need(set(got)==set(group),'missing/unexpected SHA rows'); actual.update(got)
    diff={p:{'expected':h,'actual':actual.get(p)} for p,h in expected.items() if actual.get(p)!=h}
    # Preserve original broad runtime/boot collection: full digest AND complete membership.
    runtime_command='sha256sum /system/bin/appspawn-x /system/android/framework/oh-adapter-runtime.jar /system/android/lib64/*.so /system/lib64/westlake/route-a/*/*.so '+' '.join('/system/lib64/'+d+n for d in ('','platformsdk/') for n in ('libbms.z.so','libapk_installer.so','libinstalls.z.so'))+' 2>/dev/null'
    boot_command='sha256sum /system/android/framework/arm64/* '+' '.join('/system/android/framework/'+n+'.jar' for n in ('core-oj','core-libart','core-icu4j','okhttp','bouncycastle','apache-xml','adapter-mainline-stubs','framework','oh-adapter-framework'))+' 2>/dev/null'
    expected_runtime,expected_boot=parts({p:expected[p] for p in read(pinned(proof['baseline']))['expected']})
    for name,cmd,rows in [('runtime',runtime_command,expected_runtime),('boot',boot_command,expected_boot)]:
        got=parse_hashes(shell(cmd)); need(got==rows,'full '+name+' membership/hash differs'); (out/(name+'-fingerprint.txt')).write_text('\n'.join(sorted(h+'  '+p for p,h in got.items()))+'\n')
    ps=shell('ps -A -o PID,PPID,UID,NAME'); parents=[]
    for line in ps.splitlines():
        words=line.split()
        if len(words)>=4 and all(x.isdigit() for x in words[:3]) and words[1:4]==['1','0','appspawn-x']:
            if shell('readlink /proc/'+words[0]+'/exe').split(' (deleted)')[0].strip()=='/system/bin/appspawn-x': parents.append(words[0])
    storage=shell('df -k /data'); version=shell('param get const.ohos.fullname'); after=shell('cat /proc/sys/kernel/random/boot_id')
    result={'passed':not diff and before==after and bool(before) and len(parents)==1 and version in ('OpenHarmony-6.1.0.31','OpenHarmony 6.1.0.31'),'diff':diff,'boot_before':before,'boot_after':after,'parent_pids':parents,'storage':storage,'system_version':version,'original_319_members':319,'candidate_paths':len(expected),'generation_sha256':proof['generation_sha256'],'remote_writes':0,'scope':'5ea init/global view; no Toutiao slot credit; Boat child view remains separate evidence','absent_targets':[r['target'] for r in proof['absent_files']]}
    (out/'identity.json').write_text(json.dumps(result,indent=2)+'\n'); return result

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--round',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    config=read(a.round/'round.json'); binding=config['bindings']['candidate_proof']; proof=load_proof(pinned(binding),binding['sha256']);need(config['serial']==proof['serial'],'serial mismatch')
    spec=importlib.util.spec_from_file_location('boat_readonly_reader',pinned(proof['programs']['reader']));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    a.out.mkdir(parents=True,exist_ok=False);from absence_reader import with_absence
    result=check(with_absence(module.Reader)(a.out,config['serial']),proof,a.out,config['boot_before_reboot'])
    if not result['passed']: return 1
    mark=a.round/'observed-post-reboot-boot.json'
    if mark.exists(): need(read(mark)['boot_id']==result['boot_after'],'boot changed across windows')
    else:
        with mark.open('x') as f: json.dump({'boot_id':result['boot_after']},f)
    print(json.dumps(result));return 0
if __name__=='__main__': raise SystemExit(main())
