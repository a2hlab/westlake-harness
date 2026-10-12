#!/usr/bin/env python3
"""Isolated HDC protocol recorder; never opens USB/network or executes a command."""
import hashlib,json,os,re,shlex,sys
from pathlib import Path
state=Path(os.environ['RECOVERY_TEST_DEVICE']);d=json.loads(state.read_text());args=sys.argv[1:]
def sha(b):return hashlib.sha256(b).hexdigest()
def get(p):return d['objects'].get(p)
def fail():print('record-hdc rejected unmodelled operation',file=sys.stderr);sys.exit(7)
if args[:2]!=['-t',d['serial']]:fail()
d['events'].append(args)
if args[2:4]==['file','recv']:
 obj=get(args[4]);Path(args[5]).write_bytes(bytes.fromhex(obj['hex']))
elif args[2:4]==['file','send']:
 b=Path(args[4]).read_bytes();partial=d.get('partial_send_once',False);
 if partial:d['partial_send_once']=False;b=b[:3]
 d['objects'][args[5]]=dict(exists=True,sha256=sha(b),mode='644',uid=0,gid=0,label='u:object_r:data_file:s0',hex=b.hex())
 if partial:
  state.write_text(json.dumps(d,indent=2)+'\n');sys.exit(9)
elif args[2]=='shell':
 tokens=shlex.split(args[3]);script=tokens[2].removesuffix(';');out='';rc=0
 if script=='cat /proc/sys/kernel/random/boot_id':out=d['boot']
 elif '\np=' in script:
  target=shlex.split(script.split('\np=',1)[1].split('\n',1)[0])[0];o=get(target)
  if o:
   out='EXISTS\n{mode} {uid} {gid}\n{sha256} {target}\n-rw------- 1 {uid} {gid} {label} 0 {target}'.format(target=target,**o)
  else:out='ABSENT'
 elif script.startswith('set -eu; mkdir -p '):
  if d.get('mkdir_fail_once'):
   d['mkdir_fail_once']=False;state.write_text(json.dumps(d,indent=2)+'\n');print('\nRE_REMOTE_RC=8');sys.exit(0)
 elif script.startswith('set -eu; chown '):
  ts=shlex.split(script);target=ts[4].rstrip(';');o=get(target);u,g=ts[3].split(':');o['uid']=int(u);o['gid']=int(g);o['mode']=ts[6];o['label']=ts[9]
 elif script.startswith('test ! -e '):
  target=shlex.split(script)[3];rc=int(get(target) is not None)
 elif script.startswith('set -eu; ! grep -F '):
  target=shlex.split(script)[-1];d['objects'].pop(target,None)
 elif script.startswith('set -eu; set -C; umask 077; : > '):
  target=shlex.split(script.split(': > ',1)[1])[0].rstrip(';')
  if get(target):fail()
  d['objects'][target]=dict(exists=True,sha256=sha(b''),mode='600',uid=0,gid=0,label='u:object_r:data_file:s0',hex='')
 elif 'mount -o ' in script:
  # Protocol-only simulation. Separate real shell test checks the trap semantics.
  cp=re.search(r'cp ([^;]+);',script); mv=re.search(r'mv ([^;]+)$',script)
  if not cp or not mv:fail()
  source,temp=shlex.split(cp.group(1));_,target=shlex.split(mv.group(1));o=dict(get(source));o['mode']='550';o['uid']=0;o['gid']=0;o['label']='u:object_r:system_etc_file:s0';d['objects'][target]=o
  d['mount_mode']='ro'
 else:fail()
 print(out+'\nRE_REMOTE_RC='+str(rc))
else:fail()
state.write_text(json.dumps(d,indent=2)+'\n')
