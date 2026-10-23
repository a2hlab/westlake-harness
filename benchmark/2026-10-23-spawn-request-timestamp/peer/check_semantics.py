#!/usr/bin/env python3
import argparse, hashlib, json, os, shlex, subprocess, sys, tempfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--candidate-dir',type=Path,required=True);p.add_argument('--original',type=Path,required=True);a=p.parse_args()
base=a.original.read_bytes();cand=(a.candidate_dir/'candidate.sh').read_bytes()
command=base.decode().splitlines()[1];client=command.split()[0]
assert cand.decode().splitlines()[-1]==command
assert (a.candidate_dir/'baseline.sh').read_bytes()==base
cases=[('success',0,'ok','pipe'),('nonzero',37,'ok','pipe'),('exit127',127,'ok','pipe'),('missing_uptime',43,'missing','pipe'),('empty_uptime',47,'empty','pipe'),('directory_uptime',51,'directory','pipe'),('closed_stderr',23,'ok','closed'),('readonly_stderr',27,'ok','readonly')]
input_bytes=b'fixed stdin\x00binary\xff\nwithout final newline'
rows=[]
with tempfile.TemporaryDirectory(prefix='t90-peer-') as td:
 root=Path(td);fake=root/'fake-client';meta=root/'meta.json';up=root/'uptime';up.write_text('1234.56 5678.90\n');empty=root/'empty';empty.touch();ro=root/'readonly';ro.write_text('read-only fd\n')
 fake.write_text('#!'+sys.executable+'\n'+'''import json,os,sys
from pathlib import Path
data=sys.stdin.buffer.read()
Path(os.environ['T90_META']).write_text(json.dumps({'argv':sys.argv[1:],'stdin_hex':data.hex(),'pid':os.getpid(),'ppid':os.getppid()}))
sys.stdout.buffer.write(b'fake-client-stdout\\n'+data)
try: os.write(2,b'fake-client-stderr\\n')
except OSError: pass
sys.exit(int(os.environ['T90_RC']))
''');fake.chmod(0o700)
 for shell in ['/bin/sh','/bin/bash','/bin/dash']:
  if not Path(shell).exists():continue
  for label,rc,time_kind,err_kind in cases:
   pair=[]
   for which,text in [('baseline',base.decode()),('candidate',cand.decode())]:
    upath={'ok':up,'missing':root/'missing','empty':empty,'directory':root}[time_kind]
    script=root/(which+'.sh');script.write_text(text.replace(client,shlex.quote(str(fake)),1).replace('/proc/uptime',shlex.quote(str(upath))))
    env=os.environ.copy();env.update(T90_META=str(meta),T90_RC=str(rc))
    fd=os.open(ro,os.O_RDONLY) if err_kind=='readonly' else None
    proc=subprocess.Popen([shell,str(script)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=fd if fd is not None else subprocess.PIPE,env=env,preexec_fn=(lambda:os.close(2)) if err_kind=='closed' else None)
    stdout,stderr=proc.communicate(input_bytes,timeout=5)
    if fd is not None:os.close(fd)
    m=json.loads(meta.read_text());meta.unlink()
    hierarchy='exec_replacement' if m['pid']==proc.pid else ('direct_child' if m['ppid']==proc.pid else 'other')
    pair.append({'rc':proc.returncode,'stdout_hex':stdout.hex(),'stderr':(stderr or b'').decode(),'argv':m['argv'],'stdin_hex':m['stdin_hex'],'hierarchy':hierarchy})
   b,c=pair
   expected_marker='[WL-SPAWN-REQUEST] uptime_s=1234.56\n' if time_kind=='ok' and err_kind=='pipe' else ''
   checks={'return_code':b['rc']==c['rc']==rc,'stdout':b['stdout_hex']==c['stdout_hex'],'stdin':b['stdin_hex']==c['stdin_hex']==input_bytes.hex(),'argv':b['argv']==c['argv']==command.split()[1:],'hierarchy':b['hierarchy']==c['hierarchy'] and c['hierarchy']!='other','stderr_only_expected_marker':c['stderr']==expected_marker+b['stderr']}
   rows.append({'shell':shell,'case':label,'checks':checks,'baseline':b,'candidate':c})
r={'baseline_sha256':hashlib.sha256(base).hexdigest(),'candidate_sha256':hashlib.sha256(cand).hexdigest(),'case_count':len(rows),'all_passed':all(all(x['checks'].values()) for x in rows),'rows':rows,'limit':'Local shells and fake client only; no claim of target /system/bin/sh execution or deployment. Only original executable and uptime paths are mapped in isolated fixtures.'}
print(json.dumps(r,indent=2));sys.exit(0 if r['all_passed'] else 1)
