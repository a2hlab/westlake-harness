from pathlib import Path
import sys,json,hashlib,shutil
p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'preflight','inspect'];x={'__file__':str(p)};exec(p.read_text(),x);r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];recv=x['recv']
ws=Path.home()/'a2hlab/ws';root=ws/'out-speed-delivery50';inp=root/'inputs';inp.mkdir(parents=True,exist_ok=True)
old=ws/'out-aot42';clamp=x['R'].parent/'clamp48/build'
names=['core-oj','core-libart','core-icu4j','conscrypt','okhttp','bouncycastle','apache-xml','framework','adapter-runtime-bcp']
rels=['fw/'+n+'.jar' for n in names]+['boot/boot'+('' if i==0 else '-'+n)+'.'+s for i,n in enumerate(names) for s in ['art','oat','vdex']]+['libart.so','toutiao.apk','run.sh']
out=dev('sha256sum '+' '.join(x['rt']+'/'+n for n in rels),20);(r/'actual-runtime-sha.txt').write_text(out)
remote={l.split()[1].removeprefix(x['rt']+'/'):l.split()[0] for l in out.splitlines()};assert len(remote)==39
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for rel in rels:
 q=inp/rel;q.parent.mkdir(parents=True,exist_ok=True)
 if rel.startswith(('fw/','boot/')):src=clamp/rel;assert sha(src)==remote[rel],rel;shutil.copy2(src,q)
 elif rel=='toutiao.apk':src=old/'inputs'/rel;assert sha(src)==remote[rel];shutil.copy2(src,q)
 else:recv(x['rt']+'/'+rel,q,30)
 assert sha(q)==remote[rel],rel
assert remote['fw/adapter-runtime-bcp.jar'].startswith('ea5d8b27');assert remote['libart.so'].startswith('78e34445')
manifest={n:{'sha256':h} for n,h in remote.items()};(root/'input-files.json').write_text(json.dumps(manifest,indent=2));(r/'framework-report.json').write_text(json.dumps({'files':manifest},indent=2))
if not (root/'tools').exists():(root/'tools').symlink_to(old/'tools',target_is_directory=True)
recv('/data/local/tmp/operator45/selfheal48/watchdog.sh',r/'watchdog-before.sh',10)
recv('/data/local/tmp/operator45/selfheal48/instance.txt',r/'instance-before.txt',5)
(r/'board-baseline.txt').write_text(dev('pidof com.ss.android.article.news appspawn-x; cat /proc/sys/vm/max_map_count; test ! -d /data/local/tmp/operator45/selfheal48/lock && echo NO_GUARD; ls -la '+x['rt']+'/oat/arm64; cat /proc/meminfo',10))
shutil.copy2(inp/'run.sh',r/'run.sh')
print('FROZEN',root,len(remote))
