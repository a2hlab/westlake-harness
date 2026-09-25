from board45 import *
r=R/'live';r.mkdir(exist_ok=True)
d=json.loads((R/'warm/device-report.json').read_text())
d['child']=int(dev('cat /data/local/tmp/operator45/child.pid').strip());d['parent']=int(dev('cat /data/local/tmp/operator45/parent.pid').strip())
(r/'device-report.json').write_text(json.dumps(d,indent=2)+'\n')
state=dev('date; cat /proc/uptime; cat /data/local/tmp/operator45/guard.pid; cat /data/local/tmp/operator45/child.pid; cat /data/local/tmp/operator45/parent.pid; cat /data/local/tmp/operator45/child.stderr.path; cat /data/local/tmp/operator45/watchdog.log; pidof com.ss.android.article.news; ps -ef | grep article.news; ls /data/local/tmp/operator45/stop 2>/dev/null')
(r/'state.txt').write_text(state);print(state)
for label,remote in [('child.stderr',d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr'),('parent.log',d['stage']+'/parent.log'),('watchdog.sh','/data/local/tmp/operator45/watchdog.sh')]:recv(remote,r/label)
text=dev("hidumper -s WindowManagerService -a '-a'");(r/'windows.txt').write_text(text)
print('\n'.join(l for l in text.splitlines() if 'com.ss.android' in l or 'Focus window' in l))
for name in ('guard-test','guard-test2'):
 if not (R/name).exists():continue
 (R/name/'recovery-lifecycle.txt').write_text('\n'.join(l for l in (r/'child.stderr').read_text(errors='replace').splitlines() if l.startswith(('[ABILITY38-RESUMED]','[B47-SLA]')))+'\n') if name=='guard-test2' else None
archive='/data/local/tmp/operator45-crashes'
# Snapshot only our own crash directory. Preserve extensionless INDEX as text.
for remote in dev('find '+archive+' -type f').splitlines():
 rel=pathlib.PurePosixPath(remote).relative_to(archive)
 recv(remote,R/'crash-archives'/str(rel))
for p in (R/'crash-archives').rglob('*'):
 if p.is_file() and not p.suffix:p.rename(p.with_name(p.name+'.txt'))
