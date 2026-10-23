#!/usr/bin/env python3
"""Bounded offline source/receipt check. No device, network or artifact execution."""
from pathlib import Path
import argparse,hashlib,json
p=argparse.ArgumentParser();p.add_argument('--workspaces',type=Path,default=Path(__file__).resolve().parents[4]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
files=[
 'westlake-harness/sources/api-implementations/shared-native-production/related-source/framework/android-runtime/src/android_os_MessageQueue.cpp',
 'westlake-harness/sources/api-implementations/source-build-native691/westlake/native/android_message_queue.cpp',
 'vm-copies/westlake-current/framework/android-runtime/src/android_os_MessageQueue.cpp',
 'vm-copies/westlake-current/native/android_message_queue.cpp',
 '00.Workspace/src/adapter/framework/android-runtime/src/android_os_MessageQueue.cpp',
 '00.Workspace/src/AlexBridge/framework/android-runtime/src/android_os_MessageQueue.cpp',
 '00.Workspace/src/adapter/sources/oh61-v7-b2133b5b/framework/android-runtime/src/android_os_MessageQueue.cpp']
pins=[]
for name in files:
 f=a.workspaces/name
 if not f.is_file():pins.append({'path':name,'exists':False});continue
 b=f.read_bytes();hits=[i for i,l in enumerate(b.decode().splitlines(),1) if 'TOUCH21-POLL' in l or 'TOUCH21-WAKE' in l]
 pins.append({'path':name,'exists':True,'sha256':hashlib.sha256(b).hexdigest(),'marker_lines':hits})
receipt=a.workspaces/'westlake-harness/benchmark/2026-10-23-apk-runtime-identity-comparison/B/raw/B1_sha.stdout'
b=receipt.read_bytes();rows=[{'line':i,'text':s} for i,s in enumerate(b.decode().splitlines(),1) if 'liboh_android_runtime.so' in s]
r={'source_checks':pins,'historical_artifact_receipt':{'path':str(receipt.relative_to(a.workspaces)),'sha256':hashlib.sha256(b).hexdigest(),'rows':rows,'limit':'Known historical runtime filename/SHA only. This does not prove it produces TOUCH21 logs or bind its source.'},'clock_api':'unknown','unit':'unknown','deployed_producer_chain':'unknown'}
a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'checked_sources':len(pins),'marker_hits':sum(len(x.get('marker_lines',[])) for x in pins),'status':'unknown'}))
