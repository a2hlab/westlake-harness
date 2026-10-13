#!/usr/bin/env python3
"""Offline exact-parameter derivation from fresh post-rollback read-only capture."""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ['WORKSPACES']).resolve();MAIN=WS/'westlake-harness'
REL=Path('benchmark/2026-10-09-demo-boatattack/v2-20261013')
DONOR=MAIN/REL/'integration/runtime-successor-r6'
FREEZE='40f0b103afe4e4af767f95bee53f4c5e140ff9daf0c2c5f164b962964eb0508c'
OLD_BOOT='35da6f13-e7b1-4472-a36a-5c4a69d5f191';OLD_RT='94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354'
ROOT='/data/westlake-demo/u13/boat-v2-20261013-r4';SERIAL='5ea34a4500000000000000001123012c'
def need(x,msg):
 if not x:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def ref(p):return dict(path='$WORKSPACES/'+str(Path(p).resolve().relative_to(WS)),sha256=sha(p))
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def inspect(capture):
 probe=read(capture/'probe.json');raw=(capture/'probe.stdout.txt').read_text();boot=raw.splitlines()[0]
 need(probe['serial']==SERIAL and probe['rc']==0 and probe['stdout_sha256']==sha(capture/'probe.stdout.txt'),'probe receipt')
 need(re.fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',boot) and boot!=OLD_BOOT,'fresh real post-rollback boot')
 need(not (capture/'probe.stderr.txt').read_text().strip(),'probe stderr')
 need('state=READY' in raw.splitlines() and 'layers=56' in raw.splitlines() and 'boot_id='+boot in raw.splitlines() and 'Permissive' in raw.splitlines(),'sameboot READY56')
 for path in ['/system/android/lib64/liboh_android_runtime.so',ROOT+'/sources/liboh_android_runtime.so']:need(OLD_RT+'  '+path in raw.splitlines(),'restored947 target/source')
 inode=re.findall(r'^755 0 0 ([0-9]+:[0-9]+)$',raw,re.M);need(len(inode)==1,'unique actual runtime source inode')
 need('u:object_r:system_lib_file:s0 '+ROOT+'/sources/liboh_android_runtime.so' in raw.splitlines(),'runtime source label')
 c=capture/'control';meta=(c/'metadata.stdout.txt').read_text().splitlines();doc=read(c/'capture.json')
 need(meta[-1]==boot and doc['serial']==SERIAL and doc['metadata_rc']==0,'control sameboot receipt')
 originals=read(DONOR/'source-pins.json');pins={Path(r['path']).name:r['sha256'] for r in originals}
 expected={'binds.tsv':('440','data_file'),'worker.sh':('550','data_file'),'recover-v3-boat.sh':('550','data_file'),'00_westlake_u13_recover-v3.cfg':('550','system_etc_file')}
 need(len(doc['files'])==4 and {Path(r['remote']).name for r in doc['files']}==set(expected),'four exact controls')
 for row in doc['files']:
  name=Path(row['remote']).name;mode,label=expected[name];want=('/system/etc/init/' if name.endswith('.cfg') else ROOT+'/')+name
  need(row['remote']==want and row['rc']==0 and row['sha256']==sha(c/name)==pins[name],'actual control bytes')
  i=next(i for i,v in enumerate(meta) if v==row['sha256']+'  '+want)
  need(re.fullmatch(mode+':0:0:u:object_r:'+label+':s0:[0-9]+:[0-9]+',meta[i+1]),'actual control metadata')
 return boot,inode[0]
def build(capture,out,prepare_out=None):
 need(sha(DONOR/'freeze.json')==FREEZE,'40f0 donor freeze')
 files=read(DONOR/'freeze.json')['files'];pinned={Path(r['path']).name:r['sha256'] for r in files if '/window-final4-' not in r['path']}
 for n in ['successor.py','window_hooks.py','prepare_window.py','source-pins.json','SYNC-T0.md']:need(sha(DONOR/n)==pinned[n],'donor source drift '+n)
 capture=capture.resolve();relative=capture.relative_to(MAIN);boot,inode=inspect(capture)
 out.mkdir(parents=True,exist_ok=False)
 for n in ['window_hooks.py','prepare_window.py','SYNC-T0.md']:(out/n).write_bytes((DONOR/n).read_bytes())
 s=(DONOR/'successor.py').read_text();need(s.count(OLD_BOOT)==1 and s.count('66352:67173')==1,'exact donor parameters')
 s=s.replace(OLD_BOOT,boot).replace('66352:67173',inode)
 oldcap="main/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-5ea-readonly/control'";need(s.count(oldcap)==1,'capture root token')
 s=s.replace(oldcap,"main/"+repr(str(relative/'control')))
 oldprobe="w3.parent/'r6-5ea-readonly/probe.stdout.txt'";need(s.count(oldprobe)==1,'probe root token')
 s=s.replace(oldprobe,"main/"+repr(str(relative/'probe.stdout.txt')))
 (out/'successor.py').write_text(s)
 save(out/'source-pins.json',[ref(capture/'control'/n) for n in ['capture.json','metadata.stdout.txt','binds.tsv','worker.sh','recover-v3-boat.sh','00_westlake_u13_recover-v3.cfg']]+[ref(capture/n) for n in ['probe.json','probe.stdout.txt','probe.stderr.txt']])
 save(out/'derivation.json',dict(status='DISABLED_EXACT_REBIND',donor_freeze=FREEZE,serial=SERIAL,boot_before=OLD_BOOT,boot_after=boot,runtime_inode_before='66352:67173',runtime_inode_after=inode,source=ref(DONOR/'successor.py'),derived=ref(out/'successor.py'),changed=['origin boot','actual source inode evidence','capture/probe paths'],device_calls=0))
 # Existing prepare performs all real local input resolves and original plan_targets.
 if prepare_out:
  subprocess.run([sys.executable,str(out/'prepare_window.py'),'--out',str(prepare_out)],check=True)
 print(json.dumps(dict(status='REBIND_PREPARED_DISABLED',boot_id=boot,entry=str(out/'prepare_window.py'),device_calls=0)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--capture-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--prepare-out',type=Path);a=p.parse_args();build(a.capture_root,a.out,a.prepare_out)
