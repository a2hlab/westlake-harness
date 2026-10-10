#!/usr/bin/env python3
"""Read only the selected 61b U13 identities before/after an install-only batch."""
import argparse, importlib.util, json, os, re, subprocess, sys, time, uuid
from pathlib import Path
REPO=Path(__file__).resolve().parents[3]
WS=Path(os.environ.get('WORKSPACES',str(REPO.parent)))
MASTER=WS/'westlake-harness'
SERIAL='61b0657200000000000000000324012c'
ALLOWED_SERIALS = frozenset({'61b0657200000000000000000324012c', '5cd1e3dd00000000000000000923012c', '5ea34a4500000000000000001123012c'})

def validate_serial(serial):
    if serial not in ALLOWED_SERIALS:
        raise ValueError('serial outside demo whitelist: ' + str(serial))
    return serial

class Reader:
 def __init__(self,out,serial=SERIAL): self.out=out;self.n=0;self.serial=validate_serial(serial)
 def shell(self,command,required=False):
  if not (command.startswith('sha256sum ') or command in ('cat /proc/sys/kernel/random/boot_id','df -k /data','ps -A -o PID,PPID,UID,NAME','param get const.ohos.fullname')):raise ValueError('read not whitelisted')
  marker='__DEMO_RC_'+uuid.uuid4().hex+'__';cmd=command+'; x=$?; printf "\\n'+marker+'%s\\n" "$x"'
  r=subprocess.run(['bash',str(WS/'westlake-inputs/tools/hdc_mac.sh'),'-t',self.serial,'shell',cmd],capture_output=True,text=True,timeout=90)
  self.n+=1;(self.out/f'read-{self.n:03}.txt').write_text(r.stdout+r.stderr)
  m=re.search(re.escape(marker)+r'(\d+)\s*$',r.stdout)
  if r.returncode or not m:raise RuntimeError('read transport/status failure: '+command)
  return int(m.group(1)),r.stdout[:m.start()].strip()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--serial',choices=sorted(ALLOWED_SERIALS),default=SERIAL);a=ap.parse_args()
 if sys.platform=='darwin':
  return subprocess.run(['orb','-m','a2hlab','env','WORKSPACES='+str(WS),'MAC_HOME='+str(Path.home()),'python3',str(Path(__file__).resolve()),'--out',str(a.out),'--serial',a.serial]).returncode
 if a.out.exists():raise RuntimeError('fresh output required')
 a.out.mkdir(parents=True);b=Reader(a.out,a.serial)
 sys.path.insert(0,str(MASTER/'scripts/lab'))
 spec=importlib.util.spec_from_file_location('batch',MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 expected=json.loads((MASTER/'benchmark/2026-10-03-u14-stage-a-plan/inputs/recovery-61b.json').read_text())['expected']
 before=b.shell('cat /proc/sys/kernel/random/boot_id')[1];actual={}
 paths=list(expected)
 for i in range(0,len(paths),24):
  rc,text=b.shell('sha256sum '+' '.join(paths[i:i+24]));actual.update({p:h for h,p in re.findall(r'^([0-9a-f]{64})\s+(/\S+)$',text,re.M)})
 diff={p:{'expected':h,'actual':actual.get(p)} for p,h in expected.items() if actual.get(p)!=h}
 runtime=mod.runtime_fingerprint(b,a.out);boot=mod.boot_image_fingerprint(b,a.out)
 ps=b.shell('ps -A -o PID,PPID,UID,NAME')[1];parents=[r['pid'] for r in mod.processes(ps) if r['name']=='appspawn-x' and r['uid']==0 and r['ppid']==1];parent=' '.join(map(str,parents));storage=b.shell('df -k /data')[1];version=b.shell('param get const.ohos.fullname')[1];after=b.shell('cat /proc/sys/kernel/random/boot_id')[1]
 good=not diff and before==after and bool(before) and runtime=='452447a4a0ba' and boot=='ee927db88a67' and len(parent.split())==1 and parent.isdigit() and version in ('OpenHarmony-6.1.0.31','OpenHarmony 6.1.0.31')
 result={'state':'U13','serial':a.serial,'unique_identity_paths':len(expected),'diff':diff,'runtime':runtime,'boot':boot,'boot_before':before,'boot_after':after,'parent_pid':parent,'storage':storage,'system_version':version,'remote_writes':0,'passed':good}
 (a.out/'identity.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return 0 if good else 1
if __name__=='__main__':raise SystemExit(main())
