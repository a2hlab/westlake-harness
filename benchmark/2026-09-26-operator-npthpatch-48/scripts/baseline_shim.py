from pathlib import Path
import sys,json,hashlib
p=Path('/Users/zhaoyue/orca/workspaces/westlake-harness-npthpatch48/benchmark/2026-09-26-operator-npthpatch-48/scripts/warm48.py');sys.argv=[str(p),'baseline-shim','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];rt=x['rt'];target=rt+'/webview-t-lib/libwebview_bionic_shim.so';old='df7795746e2c14dd501c1130705f508f79fe845de96f1aa55aef5659b02c9f51';new='85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a'
src=Path.home()/'a2hlab/tmp/wv46-baseline-out/libwebview_bionic_shim.so';assert hashlib.sha256(src.read_bytes()).hexdigest()==new
s=dev('touch /data/local/tmp/operator45/stop; echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo HASH; sha256sum '+target+'; ls -lZ '+target,10);(r/'before.txt').write_text(s)
assert not s.split('APP\n')[1].split('PARENT')[0].strip();assert not s.split('PARENT\n')[1].split('HASH')[0].strip();assert old in s
backup='/data/local/tmp/operator45-crashes/npthpatch48-original/libwebview_bionic_shim.so.'+old
s=dev('mkdir -p /data/local/tmp/operator45-crashes/npthpatch48-original; test -e '+backup+' || cp -p '+target+' '+backup+'; sha256sum '+backup,10);assert old in s
x['hdc'](['file','send',src.name,'/data/local/tmp/npth48-baseline-shim.so'],src.parent,15)
assert new in dev('sha256sum /data/local/tmp/npth48-baseline-shim.so',5)
s=dev('cat /data/local/tmp/npth48-baseline-shim.so > '+target+'; chmod 755 '+target+'; sha256sum '+target+' '+backup+'; ls -lZ '+target,10);assert new in s and old in s;(r/'after.txt').write_text(s)
(r/'deployment.json').write_text(json.dumps(dict(source=str(src),before=old,after=new,backup=backup,target=target),indent=2));print(s)
