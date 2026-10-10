#!/usr/bin/env python3
"""Complete same authorized v2 recovery after asynchronous READY; no enable/reboot/installer."""
import hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; WS=HERE.parents[3];MASTER=WS/"westlake-harness"
SERIAL="5cd1e3dd00000000000000000923012c";BOOT="567ee543-00b3-4eb8-839f-6dce8b8552e7"
def main():
 if sys.argv[1:]!=["--execute"]:raise SystemExit("explicit recovery continuation + --execute required")
 out=HERE/"restore-v2-enabled-complete";out.mkdir(exist_ok=False)
 s=importlib.util.spec_from_file_location("safe",HERE/"safe_bare_prepare.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.OUT=out;sh=m.Shell()
 result={"serial":SERIAL,"lock_retained":True,"additional_reboots":0,"installer_called":False}
 def save(): (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
 try:
  assert sh.read("boot-before","cat /proc/sys/kernel/random/boot_id")==BOOT
  assert sh.read("enforce","getenforce")=="Enforcing"
  text=sh.read("receipt","cat /data/westlake-demo/u13/receipt.env")
  fields=dict(l.split("=",1) for l in text.splitlines() if "=" in l)
  assert fields["state"]=="READY" and fields["boot_id"]==BOOT and fields["layers"]=="56"
  sh.read("enabled","test ! -e /data/westlake-demo/u13/DISABLED")
  batch=MASTER/"benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py"
  args=["python3",str(batch),"--execute","--serial",SERIAL,"--lane","cx-t0","--hdc-cmd",str(WS/"westlake-inputs/tools/hdc_mac.sh"),"--lock-cmd","mac "+str(m.NOTE),"--manifest",str(MASTER/"knowledge/smoke/controls-apps.json"),"--input-root",str(WS/"westlake-b90-controls-inputs"),"--keys","helloworld","--out",str(out/"hw"),"--run-id","restore-v2-hw","--launch-only","--wait","20","--hilog","20","--shots","20"]
  with (out/"hw.log").open("w") as f:r=subprocess.run(["orb","-m","a2hlab","env","WORKSPACES="+str(WS),"MAC_HOME="+str(Path.home()),*args],stdout=f,stderr=subprocess.STDOUT,timeout=240)
  result["hw_exit"]=r.returncode
  records=list((out/"hw").glob("*/*/*/record.json"));assert len(records)==1
  rec=json.loads(records[0].read_text());assert rec.get("finished_at"),rec.get("status")
  result["hw_record"]=str(records[0]).replace(str(WS),"$WORKSPACES");save()
  with (out/"final-identity.log").open("w") as f:r=subprocess.run([sys.executable,str(HERE.parents[1]/"2026-10-09-demo-baseline/t3/verify_identity.py"),"--serial",SERIAL,"--out",str(out/"final-identity")],stdout=f,stderr=subprocess.STDOUT,timeout=180)
  if r.returncode:raise RuntimeError("final identity rejected")
  assert sh.read("boot-final","cat /proc/sys/kernel/random/boot_id")==BOOT
  assert sh.read("enforce-final","getenforce")=="Enforcing"
  result.update(status="V2_RECOVERED",ui_verdict="pending outer screenshot review",boot_id=BOOT);save()
  facts="\n".join(p.read_text() for p in (out/"hw").glob("*/*/facts.txt"));(out/"facts.txt").write_text(facts)
  m.note("5cd已恢复v2新boot567ee543，READY56/Enforcing；319 diff{} runtime452447a4a0ba/boot ee927db88a67、init父在；HW t20与facts原样：\n"+facts+"\n截图="+str(records[0].parent/"t20.jpeg").replace(str(WS),"$WORKSPACES")+"；保锁等master place-only，不自报亮数。")
 except BaseException as e:
  result.update(status="STOP_PRESERVE_LOCK",error=str(e));save();m.note("5cd v2恢复续读STOP保锁："+str(e)+"；raw="+str(out).replace(str(WS),"$WORKSPACES"));raise
if __name__=="__main__":main()
