"""5cd-only offline derivation contract. Historical identity is never a fresh capture."""
import hashlib,json,os,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
SERIAL='5cd1e3dd00000000000000000923012c'
ROOT='/data/westlake-demo/u13/boat-v2-20261013-r4'
BOAT_APK='/data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/base.apk'
BOAT_SHA='8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444'
CFG='/system/etc/init/00_westlake_u13_recover-v3.cfg'
RT='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
ROUTE_DIRS={RT+'/'+n for n in ['app-data','data','webview-t-data']}
META=('mode','uid','gid','label')
SEAL_SHA='7f5b6f996482149ffd958bcdf55981cdc8ac6e69cb17738a2984153421f72780'
SELF_SHA='542c5176572dcde4ad8a89718bed486dca585457a3326dd5924b6e02026bceff'
R4_SHA='ba35319e22e0b160fadc24c3432ea8666fd2d7c0ae614a6f035a33c85247f798'
def need(ok,why):
    if not ok:raise ValueError(why)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolve(p):
    path=Path(os.path.expandvars(str(p).replace('$PACKAGE',str(HERE))))
    return path if path.is_absolute() else HERE/path
def pin(p):
    p=Path(p).resolve();ws=Path(os.environ['WORKSPACES']).resolve()
    return {'path':'$WORKSPACES/'+str(p.relative_to(ws)) if p.is_relative_to(ws) else str(p),'sha256':sha(p)}
def pinned(ref):
    need(isinstance(ref,dict) and set(ref)=={'path','sha256'},'typed pin required')
    p=resolve(ref['path']);need(sha(p)==ref['sha256'],'source drift: '+ref['path']);return p

def sources():
    refs=read(HERE/'source-pins.json')
    for name,h in [('seal',SEAL_SHA),('selfcheck',SELF_SHA),('r4_plan',R4_SHA)]:need(refs[name]['sha256']==h,'historical source identity')
    original=pinned(refs['r4_plan']);old=read(original)
    for row in old['members']:
        if row['source'].startswith('$PACKAGE/'):
            need(sha(original.parent/Path(row['source']).name)==row['sha256'],'frozen r4 control source drift')
    need(sha(original.parent/'installer.py')==old['installer_sha256'],'frozen r4 executor drift')
    return refs,read(pinned(refs['seal'])),read(pinned(refs['selfcheck'])),old

def protected():
    refs,seal,checked,old=sources()
    need(checked['passed'] is True and checked['serial']==SERIAL and not checked['synthetic'],'historical selfcheck identity')
    need(sha(HERE/'source_5cd.py')=='28a43f20003bd79cfcb195ec5e81f76987c86fa14f151949291b2046cbb126c6','5cd source helper pin')
    from source_5cd import validate_sources
    data=validate_sources()
    return data['protected']

def validate(plan,core):
    need(plan['serial']==SERIAL,'5cd only; no spare-board absence substitution')
    cap=read(pinned(plan['capture']))
    need(cap.get('schema')=='boat-5cd-capture/v1' and cap['serial']==SERIAL,'capture scope')
    need(cap.get('complete') is True and cap['boot_before']==cap['boot_after']==plan['boot_id'],'complete same-boot capture required')
    need(re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',plan['boot_id']),'boot format')
    need(cap.get('synthetic',False)==plan.get('synthetic',False),'synthetic provenance mismatch')
    need(cap['raw'],'raw capture pins required')
    for ref in cap['raw']:pinned(ref)
    _,_,_,old=sources();need(plan['core']==old['core'],'original executor required')
    need(plan['boat_package']==old['boat_package'] and type(plan['boat_uid']) is int and plan['boat_uid']>0,'actual Boat identity required')
    need(cap['boat_package']==plan['boat_package'] and cap['boat_uid']==plan['boat_uid'],'captured Boat UID')
    import importlib.util
    identity_path=pinned(plan['boat_identity_program'])
    spec=importlib.util.spec_from_file_location('boat_uid_capture',identity_path);identity=importlib.util.module_from_spec(spec);spec.loader.exec_module(identity)
    need(identity_path.resolve()==HERE/'boat_identity.py','local reviewed identity reader')
    identity.validate(cap['boat_identity'],SERIAL,plan['boot_id'],plan['boat_uid'],pinned,read)
    need(plan['prerequisites']==old['prerequisites'],'original prerequisites unchanged')
    need(sha(HERE/'source_5cd.py')=='28a43f20003bd79cfcb195ec5e81f76987c86fa14f151949291b2046cbb126c6','5cd source helper pin')
    from source_5cd import validate_sources
    source5cd=validate_sources()
    wanted=protected();seen={r['target']:r['before'] for r in plan['preserved']}
    need(len(seen)==len(plan['preserved'])==496 and set(seen)==set(wanted)|{r['target'] for r in old['binds']}|{BOAT_APK},'all RouteB488 plus seven stock targets and actual Boat APK required')
    for target,h in wanted.items():
        b=seen[target];core.metadata(b,'RouteB preimage')
        need(b['exists'] is True and b['sha256']==h,'RouteB identity drift (new WID needs new independently verified realization): '+target)
        need(b==cap['files'][target],'RouteB capture metadata mismatch')
        need({k:b[k] for k in META}==source5cd['metadata'][target],'actual5cd RouteB metadata differs')
    need(len(plan['binds'])==7,'seven binds')
    for row,original in zip(plan['binds'],old['binds']):
        need(all(row[k]==original[k] for k in ('target','source','sha256')),'original seven bind order/content')
        before=cap['files'][row['target']];core.metadata(before,'bind before')
        need(before['exists'] is True and before['sha256']==original['before']['sha256'],'stock bind preimage')
        need(row['before']==before==seen[row['target']],'bind before capture mismatch')
        need(row['after']=={k:before[k] for k in META},'bind metadata must preserve captured target metadata')
    apk=cap['files'][BOAT_APK];core.metadata(apk,'actual Boat APK')
    need(apk['exists'] is True and apk['sha256']==BOAT_SHA and seen[BOAT_APK]==apk,'actual Boat APK pin')
    wanted_capture={BOAT_APK}|set(wanted)|{r['target'] for r in old['binds']}|{CFG}
    need(set(cap['files'])==wanted_capture,'capture exact file membership')
    need(cap['files'][CFG]['sha256']==old['members'][-1]['before']['sha256'],'current v3 cfg differs')
    for row in plan['members']:
        if row['target']==CFG:
            need({k:v for k,v in row['before'].items() if k!='source'}==cap['files'][CFG],'cfg before metadata')
            need(row['after']=={k:cap['files'][CFG][k] for k in META},'cfg metadata preserve')
        else:need(row['before']=={'exists':False,'proof':plan['capture']},'new package absence source')
    need(cap['root_absent']=={'target':ROOT,'exists':False},'fresh package root absence')
    for d in plan['directories']:
        need(d['before']=={'exists':False,'proof':plan['capture']} and d['after']==cap['directory_after'][d['target']],'directory metadata declaration')
    baseline=read(pinned(plan['baseline319']))
    need(len(baseline['expected'])==319 and baseline['expected']==baseline['actual'],'full baseline319 equality')
    need(baseline['serial']==SERIAL and baseline['boot_before']==baseline['boot_after']==plan['boot_id'] and baseline['complete'] is True,'fresh319 scope')
    canonical=read(pinned(old['baseline319']))['expected']
    need(baseline['expected']==canonical,'319 membership/SHA cannot change')
    need(cap['baseline319']==plan['baseline319'],'captured baseline pin')
    need(set(cap['route_b_directories'])==ROUTE_DIRS,'all three RouteB directory prerequisites')
    need(plan['directory_prerequisites']==[{'target':t,'after':cap['route_b_directories'][t]} for t in sorted(ROUTE_DIRS)],'directory prerequisite capture binding')
    for d in plan['directory_prerequisites']:
        core.metadata(d['after'],'existing RouteB directory')
        need(d['after']==dict(mode='755',uid=20011300,gid=20011300,label='u:object_r:appdat:s0'),'actual5cd RouteB directory metadata')
    need(plan['tools']==old['tools'] and plan['hdc']==old['hdc'],'original transport/tool identities')
    old_members={r['target']:r for r in old['members']}
    original=pinned(sources()[0]['r4_plan']).parent
    table=''.join('\t'.join([Path(r['source']).name,r['target'],r['before']['sha256'],r['sha256'],
                ':'.join(str(r['before'][k]) for k in META),':'.join(str(r['after'][k]) for k in META)])+'\n' for r in plan['binds'])
    table_sha=hashlib.sha256(table.encode()).hexdigest()
    worker=(original/'worker.sh').read_text().replace('TABLE_SHA='+sha(original/'binds.tsv'),'TABLE_SHA='+table_sha)
    for row in plan['members']:
        path=resolve(row['source']);name=Path(row['target']).name
        if row['target']==ROOT+'/binds.tsv':need(path.read_text()==table,'exact derived table')
        elif row['target']==ROOT+'/worker.sh':need(path.read_text()==worker,'only worker table pin may derive')
        else:need(row['sha256']==old_members[row['target']]['sha256'],'original artifact/control byte identity')
        if row['target'] in (ROOT+'/worker.sh',ROOT+'/recover-v3-boat.sh',ROOT+'/binds.tsv'):
            need(row['after']==old_members[row['target']]['after'],'original control metadata policy')
        source_bind=[r for r in plan['binds'] if r['source']==row['target']]
        if source_bind:need(row['after']==source_bind[0]['after'],'source and target metadata must match')
