"""VM: collect this upgrade's archive rows and final authoritative instance pointers."""
from board45 import *
r=R/'morning46-handoff';r.mkdir(exist_ok=True)
d=json.loads((R/'morning46-first/device-report.json').read_text())
for key in ('child','parent'):d[key]=int(dev('cat /data/local/tmp/operator45/'+key+'.pid').strip())
(r/'device-report.json').write_text(json.dumps(d,indent=2)+'\n')
for label,cmd in [('state','date; cat /proc/uptime; cat /data/local/tmp/operator45/child.pid /data/local/tmp/operator45/parent.pid /data/local/tmp/operator45/guard.pid; cat /data/local/tmp/operator45/child.stderr.path; cat /proc/sys/vm/max_map_count; pidof com.ss.android.article.news'),('windows',"hidumper -s WindowManagerService -a '-a'")]:
 (r/(label+'.txt')).write_text(dev(cmd))
for label,remote in [('child.stderr',d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr'),('parent.log',d['stage']+'/parent.log'),('watchdog.sh','/data/local/tmp/operator45/watchdog.sh'),('INDEX.txt','/data/local/tmp/operator45-crashes/INDEX'),('startup-settings.log','/data/local/tmp/operator45/startup-settings.log')]:recv(remote,r/label)
archive='/data/local/tmp/operator45-crashes'
for remote in ([] if '--live-only' in sys.argv else dev('find '+archive+' -type f').splitlines()):
 rel=pathlib.PurePosixPath(remote).relative_to(archive);first=rel.parts[0]
 m=re.match(r'(\d+)-',first)
 if not m or int(m[1])<6:continue
 local=R/'morning46-archives'/str(rel)
 if not local.suffix:local=local.with_name(local.name+'.txt')
 recv(remote,local)
s=(r/'child.stderr').read_text(errors='replace')
lines=[l for l in s.splitlines() if l.startswith(('[B47-SLA] ENTRY','[ABILITY38-RESUMED]','Fatal signal')) or (len(l)<2000 and any(x in l for x in ['UnsatisfiedLinkError','main_threw','SQLiteException','SQLiteDatabaseCorruptException','GLES library translated','GrGLInterface creation failed','InitializeGL failure']))]
(r/'lifecycle-errors.txt').write_text('\n'.join(lines)+'\n')
print((r/'state.txt').read_text());print('CAPTURED',len(lines),'markers')
