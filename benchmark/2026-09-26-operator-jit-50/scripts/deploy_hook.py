"""VM-only: install the pre-spawn hook, verify it in the app mount namespace, stop parent."""
from boardjit50 import *
c=json.loads((R.parent/'stub48/config.json').read_text());runtime=c['runtime'];stage=c['stage']
assert not any(live(p) for p in dev('pidof '+PKG).split()),'app must remain stopped'
assert not live(dev('cat '+D+'/guard.pid').strip()),'guardian must remain stopped'
if not (R/'watchdog-before.sh').exists():recv(D+'/watchdog.sh',R/'watchdog-before.sh')
recv(runtime+'/run.sh',R/'run-before.sh')
if not (R/'cache-before.txt').exists():(R/'cache-before.txt').write_text(dev('ls -ldZ '+runtime+'/app-data/'+PKG+'/code_cache/art-volatile; stat -c "%u:%g:%a" '+runtime+'/app-data/'+PKG+'/code_cache/art-volatile'))
cache_hook=ROOT/'scripts/prepare_jit50.sh'
send(cache_hook,runtime+'/prepare_jit50.sh')
dev('chmod 644 '+runtime+'/prepare_jit50.sh')
assert dev('sha256sum '+runtime+'/prepare_jit50.sh').split()[0]==sha(cache_hook)
t=(ROOT.parent/'2026-09-26-operator-toutiao-45/scripts/watchdog45.sh.in').read_text()
for k,v in {'RUNTIME':shlex.quote(runtime),'STAGE':shlex.quote(stage),'SOCKET':shlex.quote(c['socket']),'UID':'20010053','PARENT_COMMAND':c['parent_command'],'SPAWN_COMMAND':c['spawn_command']}.items():t=t.replace('@@'+k+'@@',v)
(R/'watchdog-after.sh').write_text(t);send(R/'watchdog-after.sh',D+'/watchdog.sh');dev('chmod 755 '+D+'/watchdog.sh')
assert dev('sha256sum '+D+'/watchdog.sh').split()[0]==sha(R/'watchdog-after.sh')
dev('rm -f '+c['socket'])
parent=int(dev(c['parent_command']).strip())
try:
 for _ in range(120):
  if 'READY' in dev('if [ -S '+c['socket']+' ]; then echo READY; fi'):break
  time.sleep(.25)
 else:raise RuntimeError('parent not ready')
 out=dev('/bin/nsenter -t '+str(parent)+' -m -- /system/bin/sh /data/local/tmp/asx/prepare_jit50.sh')
 (R/'hook-namespace-result.txt').write_text(out)
 assert '[JIT50-PREPARE]' in out and '20010053:20010053:700 nonsymlink=1' in out,out
 verify=dev('/bin/nsenter -t '+str(parent)+' -m -- /system/bin/sh -c '+shlex.quote('stat -c "%u:%g:%a:%F" /data/data/com.ss.android.article.news/code_cache/art-volatile; readlink /proc/self/ns/mnt; test ! -L /data/data/com.ss.android.article.news/code_cache/art-volatile && echo NONSYMLINK'))
 (R/'hook-independent-stat.txt').write_text(verify)
 assert '20010053:20010053:700:directory' in verify and 'NONSYMLINK' in verify
finally:
 kill_checked(parent)
report={'hook_sha256':sha(cache_hook),'watchdog_sha256':sha(R/'watchdog-after.sh'),'test_parent':parent,'parent_alive_after':live(parent),'remaining_live_toutiao':[p for p in dev('pidof '+PKG).split() if live(p)],'guard_alive':live(dev('cat '+D+'/guard.pid').strip()),'stop_marker':dev('ls -l '+D+'/stop')}
(R/'hook-deployment.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
assert not report['parent_alive_after'] and not report['remaining_live_toutiao'] and not report['guard_alive']
