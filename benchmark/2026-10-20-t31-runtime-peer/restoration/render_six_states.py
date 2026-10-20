#!/usr/bin/env python3
"""Render only; never executes the read-only remote shell."""
from pathlib import Path
import argparse,json,shlex,re,hashlib
p=argparse.ArgumentParser();p.add_argument('--parent',type=int,required=True);p.add_argument('--parent-birth',type=int,required=True);p.add_argument('--host',type=int,required=True);p.add_argument('--host-birth',type=int,required=True);p.add_argument('--parent-exe-sha',required=True);a=p.parse_args()
W=Path(__file__).resolve().parent.parent
plan=json.loads((W/'apply/plan.json').read_text());boot=json.loads((W/'restored-boot.json').read_text())['boot']
assert re.fullmatch(r'[0-9a-f-]{36}',boot) and boot!=plan['boot']
assert re.fullmatch(r'[0-9a-f]{64}',a.parent_exe_sha)
assert min(a.parent,a.parent_birth,a.host,a.host_birth)>1 and a.host!=a.parent
q=shlex.quote
checks=[f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(boot)}']
for pid,birth,uid in [(a.parent,a.parent_birth,0),(a.host,a.host_birth,plan['uid'])]:
 checks += [f'r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {birth}; test "$1" != Z; test "$1" != X',f'u=$(sed -n "s/^Uid:[[:space:]]*//p" /proc/{pid}/status); set -- $u; test "$1:$2:$3:$4" = {uid}:{uid}:{uid}:{uid}',f'cat /proc/{pid}/stat']
checks += [f'test "$(sha256sum /proc/{a.parent}/exe | cut -d\' \' -f1)" = {a.parent_exe_sha}',f'test "$(readlink /proc/{a.parent}/ns/mnt)" != "$(readlink /proc/1/ns/mnt)"',f'readlink /proc/{a.parent}/ns/mnt']
lines=['(set -eu','echo T31_SIX_ORIGINAL_STATE_BEGIN']+checks
items=[('run.sh','before_sha','run_metadata','run_label'),('lib/arm64-v8a/libmffmpeg.so','media_before_sha','media_metadata','media_label')]+[(plan[k+'_path'],k+'_before_sha',k+'_metadata',k+'_label') for k in ['player','bridge','shim']]
for rel,sha,meta,label in items:
 physical=plan['runtime']+'/'+rel;private=f'/proc/{a.parent}/root/data/local/tmp/asx/'+rel
 for kind,target in [('physical',physical),('private',private)]:
  t=q(target)
  lines += [f'test -f {t}; test ! -L {t}',f'test "$(sha256sum {t} | cut -d\' \' -f1)" = {q(plan[sha])}',f'test "$(stat -L -c %a:%u:%g {t})" = {q(plan[meta])}',f'test "$(ls -Zd {t} | cut -d\' \' -f1)" = {q(plan[label])}',f'echo {q(kind+" "+rel)}; sha256sum {t}; stat -L -c %a:%u:%g:%d:%i {t}; ls -Zd {t}']
 lines += [f'test "$(stat -L -c %d:%i {q(physical)})" = "$(stat -L -c %d:%i {q(private)})"']
assert plan['compat_before_absent'] is True
for root in [plan['runtime'],f'/proc/{a.parent}/root/data/local/tmp/asx']:
 t=q(root+'/libopensles_android_compat.so');lines += [f'test ! -e {t}; test ! -L {t}',f'echo {q("COMPAT_ABSENT "+root)}']
lines += checks+['echo T31_SIX_ORIGINAL_STATES_VERIFIED',')']
print('\n'.join(lines))
