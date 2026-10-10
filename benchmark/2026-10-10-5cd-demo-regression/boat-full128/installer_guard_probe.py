#!/usr/bin/env python3
"""Read-only exact installer preconditions on authorized bare 5cd; stop on any refusal.
Executes master installer only through its step-1 prefix; no ARCHIVE/placement/enable code.
"""
import hashlib,importlib.util,json,os,shlex,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('bare',HERE/'safe_bare_prepare.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
if sys.argv[1:]!=['--execute']:raise SystemExit('--execute requires outer-approved same lock')
b.OUT=HERE/'installer-guard-probe';b.OUT.mkdir(exist_ok=False)
shell=b.Shell();r=json.loads((HERE/'safe-bare-prepare/result.json').read_text())
assert r['bare_base_passed'] and r['disabled']
assert shell.read('current-boot','cat /proc/sys/kernel/random/boot_id')==r['boot_after']
assert shell.read('current-enforce','getenforce')=='Enforcing'
shell.read('state-before','test -f /data/westlake-demo/u13/DISABLED && ps -A -o PID,PPID,UID,NAME')
p=b.MASTER/'benchmark/2026-10-10-u13-autostart/payload/scripts/install-westlake-u13-autostart.sh'
source=p.read_text();prefix=source.split('# --- 2. snapshot the 56 live targets into the durable archive ----------------')[0]
assert 'APPSPAWN_NOT_RUNNING' in prefix and 'RECOVERED_BOARD' in prefix and 'ARCHIVE_DIR' not in prefix
(b.OUT/'installer-step1-exact.sh').write_text(prefix)
cmd='DEPLOY=/data/westlake-demo/u13 WITH_BOAT=1 ALLOW_REMOUNT=1 sh -c '+shlex.quote(prefix)
try:
 text=shell.read('installer-step1',cmd)
 b.save(b.OUT/'result.json',{'step1_passed':True,'output':text,'installer_source_sha256':b.sha(p),'prefix_sha256':b.sha(b.OUT/'installer-step1-exact.sh'),'archive_called':False,'enable_called':False})
 print(text)
except BaseException as e:
 b.save(b.OUT/'result.json',{'step1_passed':False,'error':str(e),'installer_source_sha256':b.sha(p),'prefix_sha256':b.sha(b.OUT/'installer-step1-exact.sh'),'archive_called':False,'enable_called':False,'boot':r['boot_after'],'lock_retained':True})
 b.note('5cd Boat后半段原installer第1步guard拒绝，保锁、仍DISABLED裸态；原文='+str(e)+'；未进ARCHIVE/placement/ENABLE，未绕parent或两道guard。证据='+str(b.OUT).replace(str(b.WS),'$WORKSPACES'))
 raise
