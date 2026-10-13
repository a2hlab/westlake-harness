#!/usr/bin/env python3
"""Mechanical expected identity inventory, not an observed selfcheck or signed seal."""
import argparse,hashlib,json
from pathlib import Path
APK='/data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/base.apk'
APK_SHA='8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444'
def inventory(seal,plan):
    assert len(seal['packages'])==129 and all(r['package']!='com.Unity3d.BoatAttackDay' for r in seal['packages'])
    files={}
    for group in seal['files'].values():
        for target,h in group.items():
            assert target not in files or files[target]==h
            files[target]=h
    boat={r['target']:r['sha256'] for r in plan['members']+plan['binds']};assert len(boat)==18
    result=files|boat;packages={r['apk_path']:r['apk_sha256'] for r in seal['packages']};assert APK not in packages
    packages[APK]=APK_SHA
    assert all(result.get(t)==h for t,h in files.items() if t not in boat)
    all_objects=dict(result)
    for t,h in packages.items():assert t not in all_objects or all_objects[t]==h;all_objects[t]=h
    return dict(status='EXPECTED_UNION_NOT_OBSERVED',v1_files=len(files),v2_files=len(result),v1_packages=129,v2_packages=len(packages),
                v2_unique_objects=len(all_objects),added_files=sorted(set(boat)-set(files)),changed_files=[dict(target=t,before=files[t],after=boat[t]) for t in sorted(set(boat)&set(files)) if files[t]!=boat[t]],
                private_targets={t:h for t,h in boat.items() if 'BoatAttackDay/' in t},all_expected_sha256=all_objects,
                boat_uid='pending actual postinstall BMS capture; not inferred',signed=False)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--v1-seal',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    result=inventory(json.loads(a.v1_seal.read_text()),json.loads(a.plan.read_text()))
    result['inputs']={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in [('v1_seal',a.v1_seal),('plan',a.plan)]}
    with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
if __name__=='__main__':main()
