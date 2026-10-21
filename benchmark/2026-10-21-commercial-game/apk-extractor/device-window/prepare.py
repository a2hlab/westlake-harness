#!/usr/bin/env python3
"""Create a disabled, local G13 plan from original G06 inputs and fresh160 receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from policy import APK,CANDIDATE,ORIGINAL,TARGETS,need

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--window',type=Path,required=True)
    p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[4])
    p.add_argument('--g06',type=Path,default=Path.home()/'.local/share/westlake/commercial-game-20261021/first-launch/plan-outer-02')
    p.add_argument('--runtime-fresh',type=Path,default=Path.home()/'.local/share/westlake/commercial-game-20261021/apk-extractor/runtime-fresh-01')
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--lane',default='outer');p.add_argument('--transaction',default='g13-native03-01')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    need(sha(a.candidate)==CANDIDATE and a.candidate.stat().st_size==1286024,'candidate pin')
    cfg=json.loads((a.g06/'hook-config.approved.json').read_text())
    fingerprints={}
    for name,kind,count in [('runtime-fingerprint.txt','runtime',124),('boot-image-fingerprint.txt','boot',36)]:
        rows=[l.split() for l in (a.runtime_fresh/name).read_text().splitlines()];need(len(rows)==count,'fresh member count')
        fingerprints[kind]={r[1]:r[0] for r in rows};need(fingerprints[kind]==cfg['fingerprints'][kind],'fresh members differ from accepted160')
    boot=(a.runtime_fresh/'boot-before.stdout').read_text().splitlines()[0]
    need(boot==(a.runtime_fresh/'boot-after.stdout').read_text().splitlines()[0]=='a1d869b4-69a2-40a4-937e-4860f5b54239','fresh boot mismatch')
    need('true' in (a.runtime_fresh/'ready.stdout').read_text(),'READY not true')
    repo=a.repo.resolve();out=a.out.resolve();window=a.window.resolve();kit=out/'kit';kit.mkdir()
    shutil.copyfile(a.candidate,kit/'libinstalls.z.so')
    save(kit/'manifest.json',dict(schema=1,baseline={'libinstalls.z.so':ORIGINAL},candidate={'libinstalls.z.so':CANDIDATE}))
    provider_paths=set(cfg['source_pins'])|{'scripts/lab/swap_installer.py','scripts/lab/board_note.sh','scripts/lab/check_frozen.py','scripts/lab/lab_paths.py','benchmark/2026-10-21-commercial-game/apk-extractor/window-prep/next-reads.json'}
    here=Path(__file__).resolve().parent
    provider_paths|={str(f.relative_to(repo)) for f in here.glob('*.py')}
    pins={rel:sha(repo/rel) for rel in sorted(provider_paths)}
    cfg.update(repo=str(repo),window=str(window),expected_boot=boot,lane=a.lane,fingerprints=fingerprints,source_pins=pins,approved_by='outer(codex)',hook_path=str(repo/'benchmark/2026-10-21-commercial-game/first-launch/recovery_hook.py'))
    cfg['hook_sha256']=sha(cfg['hook_path']);save(out/'g06-hook.json',cfg)
    plan=json.loads((here/'plan.disabled.json').read_text());plan['bindings'].update(repo=str(repo),window=str(window),hdc=cfg['hdc'],lane=a.lane,transaction=a.transaction,kit=str(kit),hook_config=str(out/'g06-hook.json'),manifest=str(a.g06.resolve()/'manifest.json'),input_root=str(a.g06.resolve()/'input-root'),source_pins=pins)
    plan['local_pins']={str(out/'g06-hook.json'):sha(out/'g06-hook.json'),str(a.g06.resolve()/'manifest.json'):sha(a.g06/'manifest.json'),str(kit/'manifest.json'):sha(kit/'manifest.json'),str(kit/'libinstalls.z.so'):sha(kit/'libinstalls.z.so')}
    plan['stage_argv']=[["python3",str(here/'run_window.py'),phase,'--plan',str(out/'plan.disabled.json'),'--execute'] for phase in ['before','apply','install','restore']]
    plan['control_argv']=['python3',str(repo/'scripts/lab/activation_smoke.py'),'--spec',str(a.g06.resolve()/'smoke.json'),'--serial',plan['serial'],'--lane',a.lane,'--out',str(window/'control'),'--hdc',cfg['hdc']]
    plan['runtime_fresh_alias']='$HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/runtime-fresh-01'
    save(out/'plan.disabled.json',plan)
    print(json.dumps(dict(plan=str(out/'plan.disabled.json'),execution_enabled=False,missing=['holder','control_review (only if launch enabled)'],device_operations=0)))
if __name__=='__main__':main()
