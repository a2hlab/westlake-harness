"""Root-only replay of original r6 read commands; default preview, no device writes."""
import argparse,hashlib,json,os,re,shlex,subprocess,time
from pathlib import Path
SERIAL='5ea34a4500000000000000001123012c';ROOT='/data/westlake-demo/u13/boat-v2-20261013-r4'
FILES=[ROOT+'/'+n for n in ['binds.tsv','worker.sh','recover-v3-boat.sh']]+['/system/etc/init/00_westlake_u13_recover-v3.cfg']
PROBE='cat /proc/sys/kernel/random/boot_id; getenforce; cat /data/westlake-demo/u13/receipt.env; cat '+ROOT+'/binds.tsv; sha256sum /system/android/lib64/liboh_android_runtime.so /system/android/lib64/libandroid.so '+ROOT+'/sources/liboh_android_runtime.so '+ROOT+'/worker.sh; stat -c "%a %u %g %d:%i" '+ROOT+'/sources/liboh_android_runtime.so; ls -Z '+ROOT+'/sources/liboh_android_runtime.so; ps -A -o PID,PPID,UID,NAME; cat /proc/self/mountinfo; cat /proc/sys/kernel/random/boot_id'
METADATA='cat /proc/sys/kernel/random/boot_id; '+''.join('sha256sum '+shlex.quote(p)+'; stat -c "%a:%u:%g:%C:%d:%i" '+shlex.quote(p)+'; ' for p in FILES)+'cat /proc/sys/kernel/random/boot_id'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def run(argv,stem):
 now=time.time();r=subprocess.run(argv,capture_output=True,timeout=90);stem.with_suffix('.stdout.txt').write_bytes(r.stdout);stem.with_suffix('.stderr.txt').write_bytes(r.stderr)
 save(stem.with_suffix('.receipt.json'),dict(argv=argv,rc=r.returncode,started=now,finished=time.time(),stdout_sha256=sha(stem.with_suffix('.stdout.txt')),stderr_sha256=sha(stem.with_suffix('.stderr.txt'))))
 if r.returncode:raise ValueError('read-only transport failed; retained '+str(stem))
 return r.stdout.decode().replace('\r',''),r.stderr.decode()
def shell(a,command,stem):
 wrapped='/system/bin/sh -c '+shlex.quote('set -eu; '+command)+'; rc=$?; printf "\\nCAPTURE_RC=%s\\n" "$rc"'
 text,err=run([a.hdc,'-t',SERIAL,'shell',wrapped],stem.with_name(stem.name+'-transport'))
 m=re.search(r'\nCAPTURE_RC=(\d+)\n?\Z',text)
 if not m or m.group(1)!='0' or err.strip():raise ValueError('read-only remote rc/stderr refused')
 body=text[:m.start()].rstrip('\n')+'\n';stem.with_suffix('.stdout.txt').write_text(body);stem.with_suffix('.stderr.txt').write_text(err);return body

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-boot',required=True);p.add_argument('--hdc',default='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc');p.add_argument('--execute',action='store_true');a=p.parse_args()
 if not a.execute:print(json.dumps(dict(serial=SERIAL,expected_boot=a.expected_boot,probe=PROBE,metadata=METADATA,recv=FILES,device_calls=0),indent=2));return
 a.out.mkdir(parents=True,exist_ok=False);control=a.out/'control';control.mkdir()
 raw=shell(a,PROBE,a.out/'probe')
 if raw.splitlines()[0]!=a.expected_boot or raw.splitlines()[-1]!=a.expected_boot:raise ValueError('probe boot mismatch')
 save(a.out/'probe.json',dict(serial=SERIAL,command=PROBE,rc=0,epoch=time.time(),stdout_sha256=sha(a.out/'probe.stdout.txt')))
 before=shell(a,METADATA,control/'metadata-before')
 if before.splitlines()[0]!=a.expected_boot or before.splitlines()[-1]!=a.expected_boot:raise ValueError('metadata boot mismatch')
 files=[]
 for index,remote in enumerate(FILES):
  local=control/Path(remote).name;run([a.hdc,'-t',SERIAL,'file','recv',remote,str(local)],control/('recv-%d'%index))
  if not local.is_file() or sha(local)+'  '+remote not in before.splitlines():raise ValueError('recv does not match independently read device SHA')
  files.append(dict(remote=remote,local='$WORKSPACES/'+str(local.resolve().relative_to(Path(os.environ['WORKSPACES']).resolve())),sha256=sha(local),rc=0))
 after=shell(a,METADATA,control/'metadata')
 if before!=after:raise ValueError('control metadata/boot changed during receive')
 save(control/'capture.json',dict(serial=SERIAL,epoch=time.time(),files=files,metadata_rc=0,boot_id=a.expected_boot))
 print('READONLY_CAPTURE_COMPLETE: device mutations=0')
if __name__=='__main__':main()
