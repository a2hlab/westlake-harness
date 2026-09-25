"""Restore the saved five-fix operator baseline after the isolated #48 trials.

VM only. All trial profiles and the original pretrial profile remain preserved.
This restores configuration, not a promise that the known metasec exit is fixed.
"""
from board48 import *

r=R/'restored-operator45';assert not r.exists();r.mkdir()
c=json.loads((R/'config.json').read_text());runtime=c['runtime'];stage=c['stage']
backup='/data/local/tmp/operator45-crashes/metasec48-original'
stock='009a08fb8282b4ed8b857eaf014038adb93bb5cac0daa5d32ab89a13f29c8bbc'
original=runtime+'/profile-backups/metasec48-before-a2-r1'
saved=runtime+'/profile-backups/metasec48-before-restore'
assert not dev('ls -d '+saved+' 2>/dev/null').strip()
assert dev('sha256sum '+backup+'/libart.'+stock+'.so').split()[0]==stock
for part in ('app-data','data','webview-t-data'):
 assert 'EXISTS' in dev('if [ -d '+original+'/'+part+' ]; then echo EXISTS; fi')

guard=dev('cat '+D+'/guard.pid').strip()
dev('touch '+D+'/stop; kill '+guard);time.sleep(4);assert not live(guard)
parent=dev('cat '+D+'/parent.pid').strip()
for pid in dev('pidof '+PKG).split():kill_checked(pid)
kill_checked(parent)
assert not any(live(pid) for pid in dev('pidof '+PKG).split())
dev('mkdir -p '+saved)
for part in ('app-data','data','webview-t-data'):
 dev('mv '+runtime+'/'+part+' '+saved+'/'+part+'; cp -a '+original+'/'+part+' '+runtime+'/'+part)
dev('cp '+backup+'/libart.'+stock+'.so '+runtime+'/libart.so')
assert dev('sha256sum '+runtime+'/libart.so').split()[0]==stock
dev('cp '+backup+'/watchdog.sh '+D+'/watchdog.sh; chmod 755 '+D+'/watchdog.sh; rm -f '+D+'/preseed48.enabled')
dev('echo 1048576 > /proc/sys/vm/max_map_count; power-shell timeout -o 86400000; power-shell wakeup; aa start -b org.westlake.imehost -a EntryAbility; rm -f '+c['socket'])
c['parent']=int(dev(c['parent_command']).strip())
for _ in range(120):
 if 'READY' in dev('if [ -S '+c['socket']+' ]; then echo READY; fi'):break
 time.sleep(.25)
else:raise RuntimeError('parent socket not ready')
c['child']=int(re.search(r'result=0 pid=(\d+)',dev(c['spawn_command']))[1])
s=stat(c['child']);assert s;c['birth']=s.rsplit(') ',1)[1].split()[19]
c['restored_profile_copy']=original;c['saved_trial_profile']=saved
(r/'device-report.json').write_text(json.dumps(c,indent=2)+'\n')
dev(f'echo {c["child"]} > {D}/child.pid; echo {c["parent"]} > {D}/parent.pid; echo {runtime}/private-tmp/adapter_child_{c["child"]}.stderr > {D}/child.stderr.path; rm -f {D}/guard.pid {D}/stop; rmdir {D}/guard.lock 2>/dev/null')
guard=dev(f'nohup /system/bin/sh {D}/watchdog.sh >{D}/watchdog.log 2>&1 </dev/null & echo $!').strip()
dev('echo '+guard+' > '+D+'/guard.pid')
(r/'restoration.txt').write_text(dev('date; cat /proc/uptime; cat '+D+'/child.pid '+D+'/parent.pid '+D+'/guard.pid; sha256sum '+runtime+'/libart.so '+runtime+'/run.sh '+runtime+'/webview-t-lib/libwebview_bionic_shim.so '+runtime+'/liboh_adapter_bridge.so '+runtime+'/lib/arm64-v8a/libnpth.so; cat /proc/sys/vm/max_map_count'))
print('RESTORED',c['child'],c['parent'],'GUARD',guard,flush=True)
