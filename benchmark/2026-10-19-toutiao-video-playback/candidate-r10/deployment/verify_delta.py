#!/usr/bin/env python3
"""Exact reviewed delta and early CLI refusal; no Board/device calls."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source-repo',required=True,type=Path);a=p.parse_args()
d=Path(__file__).resolve().parent;b=a.source_repo/'benchmark/2026-10-19-toutiao-video-playback'
old='6e83e924aae709f0c90ba2a966910febb63471b7a9a6294c6dee585a73ff3b4b'
new='5f591f5ed92e608a622ab4b59bb2061a846600d0ac5e5d4698405e6301ac8c3c'
x=(d/'video_guarded_window_r10.py').read_text();y=(d/'read_binding.py').read_text()
assert x.replace("EXECUTION_REVIEW='UNAPPROVED'","EXECUTION_REVIEW='APPROVED'").replace(new,old).replace("dso=base/'candidate-r10/deploy-inputs'/DSO","dso=base/'candidate-r8/deploy-inputs'/DSO")==(b/'candidate-r9/video_guarded_window_r9.py').read_text()
assert y.replace(new,old).replace('candidate-r10/deploy-inputs/libopensles_android_compat.so','candidate-r8/deploy-inputs/libopensles_android_compat.so')==(b/'candidate-r8/deployment/read_binding.py').read_text()
assert x.index("sys.exit('UNAPPROVED_DRAFT")<x.index('import bms_batch')<x.index('board=b.Board(')
r=subprocess.run(['python3',str(d/'video_guarded_window_r10.py'),'apply'],capture_output=True,text=True)
assert r.returncode!=0 and 'UNAPPROVED_DRAFT' in r.stderr and 'Traceback' not in r.stderr
print(json.dumps({'status':'PASS','device_calls':0,'early_refusal_rc':r.returncode,'executor_sha256':hashlib.sha256(x.encode()).hexdigest(),'reader_sha256':hashlib.sha256(y.encode()).hexdigest()},indent=2))
