#!/usr/bin/env python3
"""One bookended readonly metadata collection; default prints argv, never calls HDC."""
import argparse,hashlib,json,os,re,shlex,subprocess,time
from pathlib import Path
SERIAL='5cd1e3dd00000000000000000923012c'
WS=Path(os.environ.get('WORKSPACES',str(Path(__file__).resolve().parents[6])))
OLD=WS/'westlake-harness/benchmark/2026-10-12-v1-seal-execution/exact-5cd-preview/plan.json'
SUPPLEMENT='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/webview-t-data'
STOP='/data/local/tmp/operator45/selfheal48/stop'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def targets():
 p=json.loads(OLD.read_text());return sorted({d['target'] for d in p['directories']+p['directory_prerequisites']}|{SUPPLEMENT})
def script(boot):
 q=shlex.quote;s=['set -eu','printf "BOOT_BEFORE\\n"','cat /proc/sys/kernel/random/boot_id','test "$(cat /proc/sys/kernel/random/boot_id)" = '+q(boot)]
 for target in targets():
  t=q(target);s += ['printf "TARGET=%s\\n" '+t,'test -d '+t+'; test ! -L '+t,"stat -c '%a:%u:%g:%C:%d:%i' "+t]
 s += ['printf "STOP\\n"','if test -e '+q(STOP)+'; then test -f '+q(STOP)+'; test ! -L '+q(STOP)+'; echo EXISTS; stat -c "%a:%u:%g:%C:%d:%i" '+q(STOP)+'; sha256sum '+q(STOP)+'; else test ! -L '+q(STOP)+'; test -d '+q(str(Path(STOP).parent))+'; echo ABSENT; fi','printf "BOOT_AFTER\\n"','cat /proc/sys/kernel/random/boot_id']
 return '\n'.join(s)
def parse(raw,boot):
 lines=raw.replace('\r','').splitlines();assert lines[:2]==['BOOT_BEFORE',boot];assert lines[-4:]==['BOOT_AFTER',boot,'','FRESH_DIR_RC=0'];rows={};i=2
 for target in targets():
  assert lines[i]=='TARGET='+target;i+=1;mode,uid,gid,rest=lines[i].split(':',3);label,device,inode=rest.rsplit(':',2);i+=1
  assert re.fullmatch('[0-7]{3,4}',mode) and re.fullmatch('u:object_r:[A-Za-z0-9_]+:s0',label) and uid.isdigit() and gid.isdigit() and device.isdigit() and inode.isdigit()
  rows[target]=dict(exists=True,mode=mode,uid=int(uid),gid=int(gid),label=label,identity=device+':'+inode)
 assert lines[i]=='STOP';i+=1
 if lines[i]=='ABSENT':stop={'exists':False};i+=1
 else:
  assert lines[i]=='EXISTS';i+=1;mode,uid,gid,rest=lines[i].split(':',3);label,device,inode=rest.rsplit(':',2);i+=1;digest,target=lines[i].split();i+=1;assert target==STOP and re.fullmatch('[a-f0-9]{64}',digest);stop=dict(exists=True,sha256=digest,mode=mode,uid=int(uid),gid=int(gid),label=label,identity=device+':'+inode)
 assert i==len(lines)-4
 return dict(schema='routeb-fresh-directories/v1',serial=SERIAL,boot_before=boot,boot_after=boot,complete=True,directories=rows,preserved_stop=stop,device_writes=0)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--boot-id',required=True);ap.add_argument('--hdc',default='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--execute',action='store_true');a=ap.parse_args();assert re.fullmatch('[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',a.boot_id)
 command='/system/bin/sh -c '+shlex.quote(script(a.boot_id))+'; rc=$?; printf "\\nFRESH_DIR_RC=%s\\n" "$rc"';argv=[a.hdc,'-t',SERIAL,'shell',command]
 if not a.execute:print(json.dumps(dict(status='READONLY_PREVIEW',directories=len(targets()),argv=argv,device_calls=0)));return
 a.out.mkdir(parents=True,exist_ok=False);start=time.time();r=subprocess.run(argv,capture_output=True,timeout=120);(a.out/'stdout.txt').write_bytes(r.stdout);(a.out/'stderr.txt').write_bytes(r.stderr)
 receipt=dict(argv=argv,rc=r.returncode,started=start,finished=time.time(),device_writes=0,stdout_sha256=sha(a.out/'stdout.txt'),stderr_sha256=sha(a.out/'stderr.txt'),source_plan_sha256=sha(OLD),collector_sha256=sha(__file__))
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');assert r.returncode==0 and not r.stderr;result=parse(r.stdout.decode(),a.boot_id);result['receipt_sha256']=sha(a.out/'receipt.json');(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status='READONLY_COMPLETE',directories=len(result['directories']),device_writes=0)))
if __name__=='__main__':main()
