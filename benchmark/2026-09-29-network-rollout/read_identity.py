#!/usr/bin/env python3
import json,sys,subprocess
from pathlib import Path
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
serial=sys.argv[1];out=Path(sys.argv[2]);out.mkdir(exist_ok=True,parents=True)
assert serial in {'61b0657200000000000000000324012c','5cd1e3dd00000000000000000923012c'}
# Read-only inventory may run after releasing our lock; no device mutations.
class ReadOnly:
    hdc='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
    def raw(self, command):
        return subprocess.check_output([self.hdc,'-t',serial,'shell',command],text=True,timeout=30).strip()
    def __init__(self):self.boot=self.raw('cat /proc/sys/kernel/random/boot_id')
    def shell(self, command):
        assert self.raw('cat /proc/sys/kernel/random/boot_id')==self.boot,'boot changed'
        assert command.startswith(('sha256sum ','cat /proc/','ps -A '))
        return 0,self.raw(command)
board=ReadOnly()
paths=['/system/bin/appspawn-x','/system/lib64/libbms.z.so','/system/lib64/platformsdk/libbms.z.so','/system/lib64/libapk_installer.so','/system/lib64/platformsdk/libapk_installer.so','/system/android/framework/oh-adapter-runtime.jar','/system/android/lib64/liblog.so','/system/android/lib64/liboh_android_runtime.so','/system/android/lib64/liboh_adapter_bridge.so']
ps=board.shell('ps -A -o PID,PPID,UID,NAME')[1];(out/'processes.txt').write_text(ps)
rows=b.processes(ps);data={'boot_id':board.boot,'serial':serial}
for key,pid in [('shell',None)]+[(str(r['pid']),r['pid']) for r in rows if r['name'] in ['foundation','appspawn-x']]:
 selected=paths
 if pid is not None and any(r['pid']==pid and r['name']=='foundation' for r in rows):selected=paths[1:5]
 target=selected if pid is None else [f'/proc/{pid}/root'+p for p in selected]
 text=board.shell('sha256sum '+' '.join(target))[1];(out/f'{key}-sha.txt').write_text(text)
 data[key]={r.split()[-1]:r.split()[0] for r in text.splitlines() if len(r.split())==2}
 if pid is not None:
  for item in ['maps','status']:(out/f'{pid}-{item}.txt').write_text(board.shell(f'cat /proc/{pid}/{item}')[1])
(out/'identity.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({'serial':serial,'boot':board.boot,'shell':data['shell']},indent=2))
