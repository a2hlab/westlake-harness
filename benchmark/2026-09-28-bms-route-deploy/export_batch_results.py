#!/usr/bin/env python3
"""Run in a2hlab. Export completed records without changing any board state."""
from pathlib import Path
import collections
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent
VM = Path.home() / 'a2hlab/board/bms-batch-runs'
PREFIX = 'bms-*-20260928T175726*'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)

def main():
    apps = json.loads((ROOT/'batch/apps.json').read_text())['apps']
    shards = json.loads((ROOT/'batch-shards.json').read_text())['shards']
    assignment = {key:s['serial'] for s in shards for key in s['keys']}
    attempts = collections.defaultdict(list)
    for run in sorted(VM.glob(PREFIX+'/*')):
        if not run.is_dir(): continue
        dest = ROOT/'runs'/run.parent.name/run.name
        for name in ['plan.json', 'baseline.json', 'summary.json', 'batch-stop.json']:
            if (run/name).exists():
                dest.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(run/name,dest/name)
        for record_path in run.glob('*/record.json'):
            rec = json.loads(record_path.read_text())
            if rec['status']=='started': continue
            app_dir = record_path.parent
            app_dest = dest/app_dir.name
            app_dest.mkdir(parents=True,exist_ok=True)
            keep = ['record.json','install.txt','bundle.txt','processes-after.txt','windows.txt',
                    'cold-before.txt','cold-cleanup.txt','existing-apk-hash.txt','prior-install.json']
            artifacts = {}
            for file in app_dir.iterdir():
                if file.is_file() and (file.name in keep or file.suffix=='.jpeg'):
                    shutil.copyfile(file,app_dest/file.name)
                    artifacts[file.name]={'path':str((app_dest/file.name).relative_to(ROOT)),
                                          'sha256':sha(file),'source':str(file)}
            # Keep the actual layout containing the selected exact icon, not every search page.
            chosen = rec.get('selected_icon',{}).get('id')
            if chosen:
                for file in sorted(app_dir.glob('icons*.json')):
                    if chosen in file.read_text():
                        shutil.copyfile(file,app_dest/'selected-layout.json')
                        artifacts['selected-layout.json']={'path':str((app_dest/'selected-layout.json').relative_to(ROOT)),
                                                          'sha256':sha(file),'source':str(file)}
                        break
            attempts[rec['key']].append({'record':rec,'source':str(record_path),
                'record_sha256':sha(record_path),'artifacts':artifacts,'run_id':run.parent.name})
        # Command receipts stay in the VM; pin their bytes and preserve the paths.
        command_files = sorted((run/'commands').glob('*'))
        save(dest/'command-provenance.json',[
            {'source':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
            for p in command_files if p.is_file()])
    prior_lit = {a['key'] for a in apps if a['phase']=='controls'}|{'burgerking','noice'}
    special = {'fd-stk':'native-lib-missing','fd-mobile':'black-render','fd-client':'blank-white',
               'fd-binaryeye':'exited-to-desktop','toutiao':'base-mismatch','mcdonalds':'base-mismatch'}
    rows=[]
    for app in apps:
        key=app['key']; aa=sorted(attempts[key],key=lambda a:a['record'].get('finished_at',0))
        terminal=[a for a in aa if a['record']['status'] not in ('started','batch_interrupted')]
        selected=(terminal or aa or [None])[-1]
        rec=selected['record'] if selected else {}
        history=[{'run_id':a['run_id'],'install':a['record'].get('install')} for a in aa if a['record'].get('install')]
        rows.append({'key':key,'phase':app['phase'],'serial':assignment[key],
            'package':rec.get('package',app.get('package')),'apk_sha256':rec.get('apk_sha256',app.get('apk_sha256')),
            'westlake_2026_09_27':{'verdict':'LIT' if key in prior_lit else 'BLOCKED',
                'category':'own-ui' if key in prior_lit else special.get(key,'host-launcher-fallback'),
                'source':'historical/README.md',
                'note':{'burgerking':'key mislabeled; historical screen was McDonalds; not an independent win',
                        'noice':'same app as fd-noice; preserve separate launch key'}.get(key,'')},
            'status':rec.get('status','not_run'),'review':'pending_review',
            'selected_run_id':selected['run_id'] if selected else None,
            'install_attempts':history,'record':rec,'attempts':aa})
    baseline=ROOT/'baseline-results.json'
    if not baseline.exists(): shutil.copyfile(ROOT/'results.json',baseline)
    report={'schema':'bms-66-execution-v1','count':len(rows),'phase_order':['controls','blocked','tail'],
        'completed':sum(r['status'] not in ('not_run','started','batch_interrupted') for r in rows),
        'status_counts':dict(collections.Counter(r['status'] for r in rows)),
        'visual_verdict':'pending_review','baseline_results':'baseline-results.json','apps':rows}
    save(ROOT/'results.json',report)
    print(json.dumps({'completed':report['completed'],'status_counts':report['status_counts']},ensure_ascii=False))

if __name__=='__main__': main()
