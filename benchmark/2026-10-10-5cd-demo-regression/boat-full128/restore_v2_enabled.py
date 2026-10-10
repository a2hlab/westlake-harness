#!/usr/bin/env python3
"""Outer-approved recovery only: existing enable, one reboot, readonly checks, HelloWorld t20; retain lock."""
import argparse, hashlib, importlib.util, json, os, shlex, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get("WORKSPACES",HERE.parents[3])); MASTER=WS/"westlake-harness"
SERIAL="5cd1e3dd00000000000000000923012c"
BEFORE="426dfbbb-1da3-4a5b-824a-7dde7e426dd9"
def save(p,x):p.write_text(json.dumps(x,indent=2)+"\n")
def wait_ready(read,boot,timeout=120,clock=time.monotonic,sleep=time.sleep):
 deadline=clock()+timeout
 while True:
  receipt=read()
  fields=dict(l.split("=",1) for l in receipt.splitlines() if "=" in l)
  if fields.get("boot_id")==boot:
   if fields.get("state")=="FAILED":raise RuntimeError("recover failed this boot: "+receipt)
   if fields.get("state")=="READY" and fields.get("layers")=="56":return receipt
  if clock()>=deadline:raise RuntimeError("current-boot READY56 timeout: "+receipt)
  sleep(3)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--execute",action="store_true");a=ap.parse_args()
 if not a.execute:ap.error("explicit recovery authorization + --execute required")
 out=HERE/"restore-v2-enabled";out.mkdir(exist_ok=False)
 s=importlib.util.spec_from_file_location("safe",HERE/"safe_bare_prepare.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.OUT=out
 sh=m.Shell();result={"serial":SERIAL,"lock_retained":True,"installer_called":False,"boat_called":False,"reboot_attempts":0}
 try:
  m.held();assert sh.read("boot-before","cat /proc/sys/kernel/random/boot_id")==BEFORE
  assert sh.read("mode-before","getenforce")=="Enforcing"
  sh.read("disabled-before","test -f /data/westlake-demo/u13/DISABLED")
  sh.read("config-before","cat /system/etc/init/00_westlake_u13_recover.cfg; sha256sum /system/etc/westlake-u13-recover.sh; cat /data/westlake-demo/u13/receipt.env")
  script=MASTER/"benchmark/2026-10-10-u13-autostart/payload/scripts/westlake-u13-autostart-disable.sh"
  result["enable_script_sha256"]=hashlib.sha256(script.read_bytes()).hexdigest()
  m.note("宣布5cd恢复v2：按外环新批原enable→一次target boot→READY56/Enforcing/319只读核→HW t20；保cx-t0锁等place-only，零installer/Boat/其他板。")
  sh.read("enable", "sh -c "+shlex.quote(script.read_text())+" enable-only --enable")
  sh.read("enabled-readback","test ! -e /data/westlake-demo/u13/DISABLED")
  m.held();r=subprocess.run([m.HDC,"-t",SERIAL,"target","boot"],capture_output=True,text=True,timeout=25)
  (out/"target-boot.txt").write_text(r.stdout+r.stderr);result["reboot_attempts"]=1;result["target_boot_exit"]=r.returncode;save(out/"result.json",result)
  if r.returncode:raise RuntimeError("target boot refused")
  deadline=time.monotonic()+300;after=None
  while time.monotonic()<deadline:
   time.sleep(5)
   try:
    lines=sh.read("wait-boot","cat /proc/sys/kernel/random/boot_id; param get bootevent.boot.completed",timeout=12).splitlines()
    if len(lines)==2 and lines[0]!=BEFORE and lines[1]=="true":after=lines[0];break
   except (RuntimeError,subprocess.TimeoutExpired):pass
  if not after:raise RuntimeError("new ready boot unavailable; preserve lock, no repeated reboot")
  result["boot_after"]=after
  receipt=wait_ready(lambda:sh.read("ready-receipt","cat /data/westlake-demo/u13/receipt.env"),after)
  assert sh.read("enforce-after","getenforce")=="Enforcing"
  sh.read("enabled-after","test ! -e /data/westlake-demo/u13/DISABLED")
  sh.read("startup-readonly","sha256sum /system/bin/appspawn-x; grep AppSpawnX /proc/net/unix; ps -A -o PID,PPID,UID,NAME; dmesg | grep -E 'invalid:appspawn-x|pathArgs invalid' || true")
  result["ready_56"]=True;save(out/"result.json",result)
  batch=MASTER/"benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py"
  args=["python3",str(batch),"--execute","--serial",SERIAL,"--lane","cx-t0","--hdc-cmd",str(WS/"westlake-inputs/tools/hdc_mac.sh"),"--lock-cmd","mac "+str(WS/"westlake-inputs/tools/board_note.sh"),"--manifest",str(MASTER/"knowledge/smoke/controls-apps.json"),"--input-root",str(WS/"westlake-b90-controls-inputs"),"--keys","helloworld","--out",str(out/"hw"),"--run-id","restore-v2-hw","--launch-only","--wait","20","--hilog","20","--shots","20"]
  with (out/"hw.log").open("w") as f:r=subprocess.run(["orb","-m","a2hlab","env","WORKSPACES="+str(WS),"MAC_HOME="+str(Path.home()),*args],stdout=f,stderr=subprocess.STDOUT,timeout=240)
  result["hw_exit"]=r.returncode
  records=list((out/"hw").glob("*/*/*/record.json"));assert len(records)==1
  rec=json.loads(records[0].read_text());assert rec.get("finished_at"),rec.get("status")
  shots=rec.get("screenshots",[]);result["hw_record"]=str(records[0]).replace(str(WS),"$WORKSPACES")
  save(out/"result.json",result)
  with (out/"final-identity.log").open("w") as f:r=subprocess.run([sys.executable,str(HERE.parents[1]/"2026-10-09-demo-baseline/t3/verify_identity.py"),"--serial",SERIAL,"--out",str(out/"final-identity")],stdout=f,stderr=subprocess.STDOUT,timeout=180)
  # Existing verifier binds 319 U13 bytes + fingerprints + one root init parent.
  if r.returncode:raise RuntimeError("final identity refused; preserve lock")
  assert sh.read("boot-final","cat /proc/sys/kernel/random/boot_id")==after
  result.update(status="RECOVERED_V2_EVIDENCE_READY",ui_verdict="pending outer screenshot review");save(out/"result.json",result)
  m.note("5cd v2恢复读回READY56/Enforcing，新boot="+after+"；319/fingerprint原工具PASS，HW t20证据="+str(out/"hw").replace(str(WS),"$WORKSPACES")+"；保锁等place-only，UI交外环。")
 except BaseException as e:
  result.update(status="STOP_PRESERVE_LOCK",error=str(e));save(out/"result.json",result);m.note("5cd v2恢复STOP保锁："+str(e)+"；raw="+str(out).replace(str(WS),"$WORKSPACES"));raise
if __name__=="__main__":main()
