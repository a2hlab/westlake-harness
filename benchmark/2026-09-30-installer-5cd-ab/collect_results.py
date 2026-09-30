#!/usr/bin/env python3
"""Archive installer A/B observations without inferring UI success from liveness."""
import argparse, csv, hashlib, json, shutil
from pathlib import Path
from permission_evidence import extract, permission_state
R = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('run', type=Path, help='serial directory containing facts.txt and app records')
a = p.parse_args()
keys = (R/'keys.txt').read_text().strip().split(',')
old_run = Path((R/'baseline/path.txt').read_text().strip())
assert old_run.is_dir(), old_run
out = R/'evidence'
out.mkdir(exist_ok=True)
rows = []
for name in ['facts.txt','preflight.json','runtime-fingerprint.txt']:
    shutil.copy2(a.run/name, out/name)
for key in keys:
    src = (a.run/key).resolve()
    d = json.loads((src/'record.json').read_text())
    dst = out/key
    dst.mkdir(exist_ok=True)
    for name in ['record.json','bundle.txt','processes-t5.txt','processes-t20.txt']:
        f = src/name
        if f.exists():
            if name.startswith('processes-'):
                (dst/name).write_text('\n'.join(l.rstrip() for l in f.read_text().splitlines())+'\n')
            else: shutil.copy2(f,dst/name)
    for shot in d.get('screenshots',[]):
        if shot.get('captured'): shutil.copy2(shot['path'],dst/Path(shot['path']).name)
    log = extract(src/'record.json')
    (dst/'log-evidence.json').write_text(json.dumps(log,ensure_ascii=False,indent=2)+'\n')
    old = json.loads((old_run/key/'record.json').read_text()) if (old_run/key/'record.json').exists() else None
    grant = permission_state(src/'bundle.txt','ohos.permission.START_ABILITIES_FROM_BACKGROUND')
    linked_allow = [x for x in log['background_trace_evidence'] if 'canStartAbilityFromBackground:1' in x['text']]
    rows.append(dict(key=key, background_permission=grant,
                     old_background_permission=permission_state(old_run/key/'bundle.txt','ohos.permission.START_ABILITIES_FROM_BACKGROUND'),
                     apk_same=old['apk_sha256']==d['apk_sha256'] if old else None,
                     old_launcher=old.get('desktop_activity') if old else None,
                     new_launcher=d.get('desktop_activity'),
                     linked_allow=linked_allow, linked_denials=log['background_denials'],
                     launch_requests=log['launch_requests'],
                     t20_path=str(src/'t20.jpeg') if (src/'t20.jpeg').exists() else None,
                     screenshot_review='pending_outer_review'))
def hashes(path):
    return {parts[1]:parts[0] for l in path.read_text().splitlines() if len(parts:=l.split())==2}
old_hash=hashes(R/'baseline/runtime-fingerprint.txt');new_hash=hashes(out/'runtime-fingerprint.txt')
diff={k:{'old':old_hash.get(k),'new':new_hash.get(k)} for k in old_hash.keys()|new_hash.keys() if old_hash.get(k)!=new_hash.get(k)}
expected_installer={'/system/lib64/libbms.z.so','/system/lib64/libapk_installer.so'}
result={'run':str(a.run),'facts_verbatim':(out/'facts.txt').read_text(),'apps':rows,'fingerprint_diff':diff,
        'only_installer_changed':set(diff)==expected_installer,'outer_visual_review':'pending_review'}
(R/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
with (R/'per-app.csv').open('w') as f:
    fields=['key','background_permission','old_background_permission','apk_same','old_launcher','new_launcher','t20_path','screenshot_review']
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n');w.writeheader();w.writerows(rows)
print(json.dumps({'only_installer_changed':result['only_installer_changed'],'granted':sum(x['background_permission']=='granted' for x in rows),'linked_allow_apps':sum(bool(x['linked_allow']) for x in rows),'linked_denial_apps':sum(bool(x['linked_denials']) for x in rows)},indent=2))
