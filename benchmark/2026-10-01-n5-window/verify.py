#!/usr/bin/env python3
import json,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
if sys.argv[1]=='scope':
 subprocess.run([sys.executable,str(H/'test_window.py')],check=True)
 a=json.loads((R/'knowledge/gates/native-predeploy-exceptions.json').read_text())['exceptions'];b=json.loads((H/'one-window-entries.json').read_text())
 assert len(a)==257 and len(b)==57
 assert not ({x['issue_id'] for x in a}&{x['issue_id'] for x in b})
 assert json.loads((H/'window.json').read_text())['status']=='revoked'
 assert 'expired or revoked' in (H/'revoked-dry-run.txt').read_text()
elif sys.argv[1]=='evidence':
 d=json.loads((H/'duplicate-baseline.json').read_text());assert d['n5']['samples'] and d['u5']['samples']
 assert d['n5']['duplicate_seen'] and d['u5']['duplicate_seen'] and d['conclusion']=='preexisting_alias_double_mapping'
 final=json.loads((H/'end-receipt.json').read_text());assert final['fingerprint']=='73ecf422dba2' and final['boot_image_fingerprint']=='0876029078e2'
 assert json.loads((H/'unlock.json').read_text())['held_empty']
 for x in json.loads((H/'run-index.json').read_text()):
  assert (H/x['record']).is_file() and (H/x['t20']).is_file()
else:raise SystemExit('unknown case')
print('PASS',sys.argv[1])
