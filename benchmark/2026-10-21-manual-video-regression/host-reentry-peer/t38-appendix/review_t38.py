#!/usr/bin/env python3
"""Offline T38 assembly/main-path review; never runs author entry against device state."""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import assembly_audit
from candidate_review import functions
WD='c73dadb3c0d6ba082c030d7c1096810129b5afec7e3aced4d896dce86e59f0e5'
CM='b806eb6c1bb390be357f2ac689024bf3947217611bf637850cfc65e7538681c9'
def sha(b): return hashlib.sha256(b).hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def capture(package,out):
 files={str(p.relative_to(package)):p.read_bytes() for p in package.rglob('*') if p.is_file() and 'diffs' not in p.parts and p.suffix not in ('.log',) and p.name!='build-command.txt'}
 snap=out/'snapshot';snap.mkdir()
 for name,data in files.items():
  if name.endswith(('screen-gate','decoder-probe.jpeg')): continue
  p=snap/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 pins={n:sha(b) for n,b in files.items()}
 save(out/'pins.json',{'files':pins,'binary_members_hashed_not_copied':['screen-gate','decoder-probe.jpeg'],'unchanged':all((package/n).read_bytes()==b for n,b in files.items())})
 result=assembly_audit.audit(package/'payload',WD,CM)
 save(out/'assembly.json',result)
 return result,snap
SETUP=r'''
set -u
F=fixture; PROC=$F/proc; BOOT=fixture-boot; parent=none; parent_birth=none; child=none; child_birth=none; seq=0
self_birth=1; keep_lock=0; owner_verified=0; rc_epoch_hold=0; starts=0; spawns=0; terms=0
SOCKET=$F/socket; mkdir -p "$PROC/sys/kernel/random"; echo "$BOOT" > "$PROC/sys/kernel/random/boot_id"
preconditions() { return 0; }
rb_birth() { if [ "$1" = "$$" ]; then echo 1; else echo 5834; fi; }
parent_owned() { return 0; }
event() { echo EVENT "$*"; }
state() { echo STATE "$*"; }
instance() { :; }
capture_init() { :; }
release_lock() { :; }
rc_epoch_binding() { [ "$binding" = bound ] || return 1; echo 'mntns=mnt:[100] sock=333 sockfile=1:20 runid=1:21'; }
timeout() { starts=$((starts+1)); echo 5177; }
do_one_launch() { spawns=$((spawns+1)); echo AT_SPAWN epoch="$(cat "$F/parent-epoch" 2>/dev/null || echo MISSING)"; return 0; }
monitor_child() { touch "$F/stop"; return 0; }
rc_send_term() { terms=$((terms+1)); echo UNEXPECTED_SIGNAL >&2; return 99; }
kill() { echo UNEXPECTED_DIRECT_SIGNAL >&2; return 99; }
'''
def run_cases(snap,out):
 prod=functions(snap/'payload/watchdog.sh')
 cases=[('main_bootstrap_records_before_spawn','binding=bound', 'phase=bound'),('main_bootstrap_unknown_still_spawns','binding=unknown','phase=unbound'),('main_adopt_r3_no_epoch','binding=bound; TT_PARENT_PID=5177; TT_PARENT_BIRTH=5834','MISSING')]
 rows=[]
 for name,init,expected in cases:
  body='\n'+init+'\nmain; mr=$?; rc_parent_epoch_switch 31; er=$?; echo RESULT main_rc=$mr starts=$starts spawns=$spawns epoch_rc=$er reason=${rc_epoch_reason:-none} terms=$terms\n'
  # Bound control does not exercise switch: that is in immutable T37 receipts.
  if name=='main_bootstrap_records_before_spawn':body='\n'+init+'\nmain; mr=$?; echo RESULT main_rc=$mr starts=$starts spawns=$spawns terms=$terms\n'
  script=prod+'\n'+SETUP+body
  with tempfile.TemporaryDirectory(prefix='t38-main-') as td:
   p=Path(td)/'case.sh';p.write_text(script);r=subprocess.run(['/bin/sh','case.sh'],cwd=td,text=True,capture_output=True,timeout=5)
  ok=r.returncode==0 and not r.stderr and expected in r.stdout and 'spawns=1' in r.stdout and 'terms=0' in r.stdout
  if name=='main_adopt_r3_no_epoch':ok=ok and 'starts=0' in r.stdout and 'epoch_record_missing' in r.stdout
  elif name=='main_bootstrap_unknown_still_spawns':ok=ok and 'starts=1' in r.stdout and 'epoch_not_bound' in r.stdout
  else:ok=ok and 'starts=1' in r.stdout
  (out/(name+'.sh')).write_text(script)
  row={'case':name,'passed':ok,'argv':['/bin/sh','case.sh'],'script_sha256':sha(script.encode()),'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'scope':'Real production main/record/write functions, synthetic preconditions/process observations/start/spawn/monitor; no device signals.'};save(out/(name+'.json'),row);rows.append(row)
 # Execute unchanged entry, using local synthetic config/foreground/decoder seams.
 entry=(snap/'payload/entry.sh').read_bytes()
 with tempfile.TemporaryDirectory(prefix='t38-entry-') as td:
  p=Path(td);(p/'entry.sh').write_bytes(entry)
  config='AUTH_STATE_ROOT=$HERE; ROOT=$HERE; AUTH_SOCKET=$HERE/socket; AUTH_BOOT=fixture; STARTUP_DECODER_SHA=fixture; STARTUP_PROBE_SHA=fixture; STARTUP_TAP_WAIT_POLICY=until-human-or-stop-or-boot-change\nfail(){ echo REFUSE "$*"; exit 2; }\nsha256sum(){ echo "fixture  file"; }\ntimeout(){ echo feed; }\n'
  launch='foreground_window_id(){ echo 31; }\n'
  (p/'config-common.sh').write_text(config);(p/'launch-common.sh').write_text(launch);(p/'screen-gate').write_text('');(p/'screen-gate').chmod(0o700);(p/'socket').touch()
  r=subprocess.run(['/bin/sh',str(p/'entry.sh')],cwd=td,text=True,capture_output=True,timeout=5)
  row={'case':'entry_existing_r3_socket','passed':r.returncode==2 and not r.stderr and 'EXISTING_SOCKET_NO_TAKEOVER' in r.stdout,'rc':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'entry_sha256':sha(entry),'config_fixture':config,'launch_fixture':launch,'scope':'Unmodified entry with local config/foreground/decoder seams; existing pathname gate before guardian exec. No device access.'};save(out/'entry_existing_r3_socket.json',row);rows.append(row)
 save(out/'path-replay.json',{'passed':all(r['passed'] for r in rows),'cases':rows,'device_access':False,'candidate_accepted':False})
 return rows
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--package',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 assembly,snap=capture(a.package,a.out);rows=run_cases(snap,a.out)
 print(json.dumps({'assembly_pass':assembly['passed'],'assembly_checks':len(assembly['rows']),'path_replay':[(r['case'],r['passed']) for r in rows]}))
 raise SystemExit(0 if assembly['passed'] and all(r['passed'] for r in rows) else 1)
