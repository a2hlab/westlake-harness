from pathlib import Path
import sys,json,hashlib,subprocess
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'deployment','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
r=x['r'];dev=x['dev'];rt=x['rt'];target=rt+'/lib/arm64-v8a/libnpth.so'
old='7639af0004a2a0da079e3ad3af339cb3aa341d4a9fe9d4cdce3983db6d80d39e';newsha='9966e2966057c4d7d31f81232decf58da046898b9a2be900df675d44d016a107';new=r/'libnpth.so'
assert hashlib.sha256(new.read_bytes()).hexdigest()==newsha
out=subprocess.check_output(['bash',str(p.parent/'assert_npth_hollow_48.sh'),str(new),str(p.parent.parent/'evidence/npth-app-abi-48.txt')],text=True,timeout=45);(r/'static-assert.txt').write_text(out);print(out)
s=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo STATE; test -f /data/local/tmp/operator45/stop && echo STOP; test -f /data/local/tmp/operator45/fresh48/stop && echo FRESH_STOP; test ! -d /data/local/tmp/operator45/fresh48/lock && echo NO_LOCK; sha256sum '+rt+'/webview-t-lib/libwebview_bionic_shim.so '+target,10);(r/'preflight.txt').write_text(s)
assert not s.split('APP\n')[1].split('PARENT')[0].strip();assert not s.split('PARENT\n')[1].split('STATE')[0].strip();assert all(v in s for v in ['FRESH_STOP','NO_LOCK','85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a',old])
x['recv'](target,r/'original7639.so',15);assert hashlib.sha256((r/'original7639.so').read_bytes()).hexdigest()==old
backup='/data/local/tmp/operator45-crashes/hollow48-original/libnpth.so.'+old
assert old in dev('mkdir -p /data/local/tmp/operator45-crashes/hollow48-original; test -e '+backup+' || cp -p '+target+' '+backup+'; sha256sum '+backup,10)
remote='/data/local/tmp/hollow48-libnpth.so';x['hdc'](['file','send',new.name,remote],r,15);assert newsha in dev('sha256sum '+remote,5)
s=dev('cat '+remote+' > '+target+'; chmod 755 '+target+'; sha256sum '+target,10);assert newsha in s;(r/'after.txt').write_text(s)
(r/'provenance.json').write_text(json.dumps(dict(source_commit='b21b284',old_sha256=old,new_sha256=newsha,backup=backup,target=target),indent=2));print(s)
