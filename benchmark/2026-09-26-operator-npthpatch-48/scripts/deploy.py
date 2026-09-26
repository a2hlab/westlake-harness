from pathlib import Path
import sys,json,hashlib
p=Path('/Users/zhaoyue/orca/workspaces/westlake-harness-npthpatch48/benchmark/2026-09-26-operator-npthpatch-48/scripts/warm48.py');sys.argv=[str(p),'deployment','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];rt=x['rt'];target=rt+'/lib/arm64-v8a/libnpth.so';old='8b8d559c50130a997b5fbf3383e8ebf6291ebe54ab2b5ed5fbc8e1ac73fe36af';new='4f7cc3a62b08216b4ad3e114ec13f1468256b76ad35c94d870a83a052c27b0d2'
src=Path.home()/'a2hlab/tmp/libnpth-nohooks.so';assert hashlib.sha256(src.read_bytes()).hexdigest()==new
s=dev('touch /data/local/tmp/operator45/stop; echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo HASH; sha256sum '+target+'; ls -lZ '+target,10);(r/'before.txt').write_text(s)
assert not s.split('APP\n')[1].split('PARENT')[0].strip();assert not s.split('PARENT\n')[1].split('HASH')[0].strip();assert old in s
backup='/data/local/tmp/operator45-crashes/npthpatch48-original/libnpth.so.'+old
s=dev('mkdir -p /data/local/tmp/operator45-crashes/npthpatch48-original; test -e '+backup+' || cp -p '+target+' '+backup+'; sha256sum '+backup,10);assert old in s
x['hdc'](['file','send',src.name,'/data/local/tmp/npth48-nohooks.so'],src.parent,15)
assert new in dev('sha256sum /data/local/tmp/npth48-nohooks.so',5)
s=dev('cat /data/local/tmp/npth48-nohooks.so > '+target+'; chmod 755 '+target+'; sha256sum '+target+' '+backup+'; ls -lZ '+target,10);assert new in s and old in s;(r/'after.txt').write_text(s)
(r/'deployment.json').write_text(json.dumps(dict(source=str(src),before=old,after=new,backup=backup,target=target),indent=2));print(s)
