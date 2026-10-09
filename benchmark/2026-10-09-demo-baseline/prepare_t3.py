#!/usr/bin/env python3
"""Offline-only: convert cx-bms's pinned apps list into disabled, ordered board_run batches.

Input: {apps: [{key, package, apk_sha256, needs_first_tap?, ...}]}.
Input roots come from original/corpus-v2 receipts; unknown keys need an explicit
input_root in the manifest. APK validation is subsequently performed in the VM
with bms_batch --resolve-inputs; this tool never locks or contacts a board.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
WS='$WORKSPACES'
SERIAL='61b0657200000000000000000324012c'
SHA=re.compile(r'[0-9a-f]{64}\Z')

def plans(doc, out, smoke, count=12):
    if not isinstance(doc.get('apps'),list) or not doc['apps']: raise ValueError('nonempty apps[] required')
    seen_keys=set();seen_packages=set();entries=[];taps=[]
    for app in doc['apps']:
        if app.get('install') is False: continue
        key=app['key'];pkg=app['package'];sha=app['apk_sha256']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',key) or not SHA.fullmatch(sha): raise ValueError('invalid key/SHA: '+key)
        if key in seen_keys or pkg in seen_packages: raise ValueError('duplicate key/package: '+key)
        seen_keys.add(key);seen_packages.add(pkg)
        root=app.get('input_root')
        if not root: root=WS+'/westlake-inputs/corpus-v2/app-inputs' if key.startswith('cv2-') else '$HOME/a2hlab/app-inputs'
        if app.get('needs_first_tap'):
            instruction=app.get('first_tap') or app.get('tap_instruction')
            if not instruction: raise ValueError('needs_first_tap without explicit instruction: '+key)
            taps.append({'key':key,'instruction':instruction,'status':'pending recorded manual first interaction; initial t20 is not a content verdict'})
        entries.append((dict(app,phase='blocked'),root))
    if not entries: raise ValueError('no install entries')
    output=[]
    for start in range(0,len(entries),count):
        group=entries[start:start+count];n=start//count+1;folder=f'window-{n:02d}'
        shards=[{'name':f'{i+start+1:03d}-{app["key"]}','manifest':out+'/batch-apps.json','input_root':root,'keys_file':out+'/'+folder+'/'+app['key']+'.keys'} for i,(app,root) in enumerate(group)]
        p={'serial':SERIAL,'lane':'cx-t0','entry':'91','why':'Demo t3 install and own-content t20 review; no runtime deployment',
           'board':WS+'/westlake-harness/.octos/boards/app-lighting.md','out':out+'/'+folder+'/runner',
           'execution_enabled':False,'window_limit_minutes':45,'stop_new_tests_by_minute':35,
           'smoke_spec':smoke,'offline_precheck':{'hypothesis':'Pinned historical demo set can render own content on the selected signed U13 baseline; first interaction may be required.',
           'evidence':[WS+'/westlake-harness/benchmark/2026-10-09-demo-baseline/board-choice.md',WS+'/westlake-harness/benchmark/2026-10-08-lit-apps-report/apps.json'],
           'expect':{'confirm':'Each key has own-content t20 capture; required first tap is recorded separately before content signoff.','refute':'Missing capture, failed installation, loading/empty/error UI or first fatal -> retain evidence and classify; no wall fix.'},'result':'not-falsified'},
           'shards':shards,'pending_before_execution':['Fresh infra and APK --resolve-inputs checks','Outer approval of t3 and smoke against effective state','Fill after_lock and before_unlock read-only identity verification hooks','Record first-tap actions and post-tap snapshot without reinstalling'],'after_lock':None,'before_unlock':None}
        output.append((folder,p,group))
    return entries,taps,output

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--smoke',required=True);a=ap.parse_args()
    if a.out.exists(): raise SystemExit('fresh output required')
    entries,taps,windows=plans(json.loads(a.manifest.read_text()),str(a.out.resolve()),a.smoke)
    a.out.mkdir(parents=True)
    (a.out/'batch-apps.json').write_text(json.dumps({'apps':[v for v,_ in entries]},indent=2)+'\n')
    (a.out/'first-tap-pending.json').write_text(json.dumps(taps,indent=2)+'\n')
    for folder,p,group in windows:
        d=a.out/folder;d.mkdir()
        for app,_ in group:(d/(app['key']+'.keys')).write_text(app['key']+'\n')
        (d/'plan.json').write_text(json.dumps(p,indent=2)+'\n')
    receipt={'execution_enabled':False,'device_access':False,'manifest_sha256':hashlib.sha256(a.manifest.read_bytes()).hexdigest(),'selected_packages':len(entries),'windows':len(windows),'manual_first_tap_pending':len(taps)}
    (a.out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
