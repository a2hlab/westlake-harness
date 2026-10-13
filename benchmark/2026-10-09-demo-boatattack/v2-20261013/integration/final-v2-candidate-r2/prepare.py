"""Offline 61b Boat candidate compiler. Default emits a concrete pending blueprint; never probes a device."""
import argparse,copy,json,os,shutil
from pathlib import Path
import candidate_contract as c
HERE=Path(__file__).resolve().parent

def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def blueprint():
    refs,seal,checked,old=c.sources();wanted=c.protected()
    files={t:h for group in seal['files'].values() for t,h in group.items()}
    changes=[]
    for row in old['members']+old['binds']:
        changes.append({'target':row['target'],'source':row.get('source'),'candidate_sha256':row['sha256'],
                        'v1_seal_sha256':files.get(row['target']),'fresh_before':'pending',
                        'operation':'place' if row in old['members'] else 'cold-boot-bind'})
    return {'schema':'boat-61b-disabled-blueprint/v1','execution_enabled':False,'serial':c.SERIAL,
            'source_pins':refs,'placement_members':11,'boot_binds':7,'changes':changes,
            'route_b_protected':wanted,'route_b_count':488,'global319_members_retained':319,
            'pending':['fresh 61b bookend boot and raw capture','Boat installed UID and APK identity',
                       'cfg CAS and exact file metadata','all RouteB487 plus host HAP fresh SHA/metadata',
                       'seven stock bind preimages','r4 root absence and declared directory metadata',
                       'same-boot full319 equality','full128 candidate result and outer device authorization'],
            'device_calls':0,'sealed':False}

def build(capture_path,out):
    c.need(not out.exists(),'fresh output required')
    cap=c.read(capture_path);refs,seal,checked,old=c.sources();plan=copy.deepcopy(old)
    plan.update(serial=c.SERIAL,boot_id=cap['boot_before'],boat_uid=cap['boat_uid'],execution_enabled=False,
                synthetic=cap.get('synthetic',False),capture=c.pin(capture_path),baseline319=cap['baseline319'],
                candidate_contract=c.pin(HERE/'candidate_contract.py'),boat_identity_program=c.pin(HERE/'boat_identity.py'),pending_capture=[])
    plan['evidence']={'historical_sources':refs,'fresh_capture':plan['capture']}
    plan['directory_prerequisites']=[{'target':t,'after':cap['route_b_directories'][t]} for t in sorted(c.ROUTE_DIRS)]
    plan['notes']=['61b disabled candidate; historical r4 is not 61b admission','Full RouteB488 preserved; no data enumeration/copy/removal',
                   'Placement is not restoration; external single boot and full exact selfcheck required']
    absence={'exists':False,'proof':plan['capture']};by_target={r['target']:r for r in plan['members']}
    for row in plan['binds']:
        before=copy.deepcopy(cap['files'][row['target']]);row['before']=before;row['after']={k:before[k] for k in c.META}
        by_target[row['source']]['after']=dict(row['after'])
    for row in plan['members']:
        row['before']=copy.deepcopy(absence)
        if row['target']==c.CFG:
            row['before']=dict(cap['files'][c.CFG],source=cap['cfg_source']['path'])
            c.need(c.sha(c.pinned(cap['cfg_source']))==row['before']['sha256'],'cfg CAS binding')
            row['after']={k:row['before'][k] for k in c.META}
    for row in plan['directories']:row['before']=copy.deepcopy(absence);row['after']=cap['directory_after'][row['target']]
    plan['preserved']=[{'target':target,'before':cap['files'][target]} for target in sorted(c.protected())]
    plan['preserved'].append({'target':c.BOAT_APK,'before':cap['files'][c.BOAT_APK]})
    plan['preserved'] += [{'target':r['target'],'before':r['before']} for r in plan['binds']]
    out.mkdir(parents=True)
    original=c.pinned(refs['r4_plan']).parent
    for name in ['recover.cfg','recover-v3-boat.sh']:shutil.copyfile(original/name,out/name)
    table=''.join('\t'.join([Path(r['source']).name,r['target'],r['before']['sha256'],r['sha256'],
                     ':'.join(str(r['before'][k]) for k in c.META),':'.join(str(r['after'][k]) for k in c.META)])+'\n' for r in plan['binds'])
    (out/'binds.tsv').write_text(table)
    worker=(original/'worker.sh').read_text().replace('TABLE_SHA='+c.sha(original/'binds.tsv'),'TABLE_SHA='+c.sha(out/'binds.tsv'))
    (out/'worker.sh').write_text(worker)
    for row in plan['members']:
        if row['source'].startswith('$PACKAGE/'):
            row['source']=c.pin(out/Path(row['source']).name)['path'];row['sha256']=c.sha(c.resolve(row['source']))
    plan['installer_sha256']=c.sha(HERE/'installer.py')
    import installer
    core=installer.core_for(plan);installer.validate(plan,core)
    save(out/'plan.disabled.json',plan)
    save(out/'provider.json',{'layer':'boatattack','serial':c.SERIAL,'action':'apply','targets':[r['target'] for r in plan['members']+plan['binds']],
                            'program':c.pin(HERE/'boat_provider.py'),'common':c.pin(c.pinned(refs['common'])),'executor':c.pin(HERE/'installer.py'),
                            'prepared':c.pin(out/'plan.disabled.json')})
    return plan

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--capture',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.capture:build(a.capture,a.out);print('PREPARED_DISABLED: 11 placement / 7 cold-boot binds / 488 RouteB protections; zero device calls')
    else:c.need(not a.out.exists(),'fresh output required');save(a.out,blueprint());print('PENDING_CAPTURE: blueprint only; zero device calls')
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,TypeError) as e:raise SystemExit('REFUSED: '+str(e))
