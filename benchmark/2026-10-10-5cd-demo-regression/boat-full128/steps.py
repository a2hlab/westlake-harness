#!/usr/bin/env python3
"""5cd installer-free Boat checklist using existing master tools; fresh outputs.
Only signed Boat bytes are staged. A/B must already be restored to Enforcing.
Reboot prediction is advisory per t2e and the explicit outer clarification.
"""
import argparse,hashlib,json,os,re,shlex,shutil,subprocess,sys,time,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent;WS=Path(os.environ.get('WORKSPACES',HERE.parents[3]));MASTER=WS/'westlake-harness';NOTE=WS/'westlake-inputs/tools/board_note.sh';SERIAL='5cd1e3dd00000000000000000923012c';BOARD=MASTER/'.octos/boards/app-lighting.md';HDC=os.environ.get('HDC') or shutil.which('hdc');ROOT='/data/westlake-demo/u13';PKG='com.Unity3d.BoatAttackDay'
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def note(x):subprocess.run([str(NOTE),'progress',str(BOARD),'91','cx-t0',x],check=True)
def held():assert 'cx-t0' in subprocess.check_output([str(NOTE),'held',SERIAL],text=True)
def shell(cmd,out,name):
 held();marker='__BOAT_RC_'+uuid.uuid4().hex+'__';remote=cmd+'; s=$?; printf "\\n'+marker+'%s\\n" "$s"'
 p=subprocess.run([HDC,'-t',SERIAL,'shell',remote],capture_output=True,text=True,timeout=120);(out/(name+'.txt')).write_text(p.stdout+p.stderr)
 m=re.search(re.escape(marker)+r'(\d+)\s*$',p.stdout);assert p.returncode==0 and m and int(m[1])==0,(name,p.returncode,p.stderr[-600:]);return p.stdout[:m.start()].strip()
def stage(out):
 held();r=json.loads((HERE.parent/'selinux-ab/window2/result.json').read_text());assert r['restored_enforcing'] and r['final319'] and r['lock_retained'];assert shell('cat /sys/fs/selinux/enforce',out,'enforce')=='1'
 # Read exact pre-state and capture recursive declared U13 scope, with all raw reads.
 plan=MASTER/'benchmark/2026-10-10-u13-autostart/payload/u13-recover-table.json'
 note('宣布5cd Boat新阶段<=45min，沿用户指令保留cx-t0锁；snapshot→六件SHA staged→sepolicy→target boot→只读健康/五触→runtime Permissive→全128分批。安装器/seq1零改。')
 subprocess.run([sys.executable,str(MASTER/'scripts/lab/board_state_snapshot.py'),SERIAL,'--hdc',HDC,'--plan',str(plan),'--out',str(out/'pre-snapshot'),'--label','cx-t0-5cd-boat-pre'],check=True)
 s=json.loads((out/'pre-snapshot/snapshot.json').read_text());assert s['boot_stable'] and s['selinux_enforce']=='Enforcing'
 shell('sha256sum /system/android/lib64/liboh_android_runtime.so /system/android/lib64/liboh_adapter_bridge.so /system/android/framework/oh-adapter-runtime.jar',out,'base-shared-sha')
 # Sources were copied from original signed candidates and have exact full digests.
 signed=HERE/'signed-artifacts'
 for row in json.loads((HERE/'artifact-receipt.json').read_text())['members']:assert hashlib.sha256((signed/row['name']).read_bytes()).hexdigest()==row['sha256']
 cfg=shell('cat /system/etc/init/00_westlake_u13_recover.cfg',out,'cfg');assert 'westlake-u13-boat-overlay' in cfg
 # APK is not part of the 128 demo manifest. Install only if absent, via its prior approved path.
 bundle=shell('bm dump -n '+PKG+'; true',out,'boat-bundle-before')
 if '"bundleName"' not in bundle:
  apk=WS.parent/'00.Workspace-games-ad1ab0a7/APKS/BoatAttack/dist/boat-attack-a.apk';assert hashlib.sha256(apk.read_bytes()).hexdigest()=='8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444'
  remote='/data/local/tmp/cx-t0-boat-full128.apk';subprocess.run([HDC,'-t',SERIAL,'file','send',str(apk),remote],check=True);text=shell('bm install -p '+remote,out,'boat-install');assert 'success' in text.lower();save(out/'installed-boat.json',{'installed_by_this_window':True,'apk_sha256':hashlib.sha256(apk.read_bytes()).hexdigest()})
 # Existing B1 preparation copied from the prior Boat window, not a new sandbox mechanism.
 code="import importlib.util;from pathlib import Path;p=Path("+repr(str(MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'))+");s=importlib.util.spec_from_file_location('b',p);b=importlib.util.module_from_spec(s);s.loader.exec_module(b);o=Path("+repr(str(out/'boat-sandbox'))+");o.mkdir();d=b.Board("+repr(SERIAL)+","+repr(str(WS/'westlake-inputs/tools/hdc_mac.sh'))+","+repr('mac '+str(NOTE))+",'cx-t0',o);d.ready();bundle=b.parse_bundle(d.shell('bm dump -n '+"+repr(PKG)+")[1],"+repr(PKG)+");assert isinstance(bundle['uid'],int);b.prepare_sandbox(d,"+repr(PKG)+",bundle['uid'],o)"
 with (out/'boat-sandbox.txt').open('w') as f:subprocess.run(['orb','-m','a2hlab','env','WORKSPACES='+str(WS),'MAC_HOME='+str(Path.home()),'python3','-c',code],stdout=f,stderr=subprocess.STDOUT,check=True)
 for label,extra in [('stage-dry-run',[]),('stage-execute',['--execute'])]:
  with (out/(label+'.txt')).open('w') as f:subprocess.run(['bash',str(MASTER/'scripts/lab/boat_layer_stage.sh'),'--serial',SERIAL,'--src',str(signed),'--hdc',HDC,*extra],stdout=f,stderr=subprocess.STDOUT,check=True)
 with (out/'sepolicy.txt').open('w') as f:subprocess.run([sys.executable,str(MASTER/'scripts/lab/sepolicy_gate.py'),'--recipe',str(MASTER/'knowledge/gates/selinux-label-recipe.json'),'--evidence',str(out/'sepolicy.json')],stdout=f,stderr=subprocess.STDOUT,check=True)
 save(out/'reboot-advisory.json',{'status':'advisory skipped: no exporter for Boat-layer inputs','not_a_PASS':True,'reason':'Existing sample is observed-label audit, not eight-input Boat closure/hidden-underlay exporter; no complete producer found in four trees. Outer clarified t2e forbids treating this as hard seal prerequisite.','evidence':'specs/demo-baseline/t2e-reboot-sim-min.spec.md; outer question reply 2026-10-10','hard_gates_retained':['fresh snapshot','signed six SHA','sepolicy32','postboot readonly identity and screenshots']})
 save(out/'staged.json',{'boot_before':s['boot_id'],'state':'staged-not-rebooted','serial':SERIAL});print('STAGED_NOT_REBOOTED',s['boot_id'],flush=True)
def boot(out):
 held();before=json.loads((HERE/'stage/staged.json').read_text())['boot_before'];subprocess.run([HDC,'-t',SERIAL,'target','boot'],check=True)
 for i in range(18):
  time.sleep(5)
  try:
   b=shell('cat /proc/sys/kernel/random/boot_id',out,'boot-'+str(i))
   if b and b!=before:save(out/'boot.json',{'before':before,'after':b,'attempts':1});print('NEW_BOOT',b);return
  except (AssertionError,subprocess.TimeoutExpired):pass
 raise RuntimeError('target boot did not return new boot within90s; preserve lock, no hub/HDC restart')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['stage','boot']);a=ap.parse_args();assert HDC;os.environ['WORKSPACES']=str(WS);out=HERE/a.mode;out.mkdir(exist_ok=False)
 {'stage':stage,'boot':boot}[a.mode](out)
if __name__=='__main__':main()
