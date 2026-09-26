from pathlib import Path
import sys,json,hashlib,subprocess
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'deployment7639','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];rt=x['rt']
s=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo STATE; test -f /data/local/tmp/operator45/stop && echo STOP; test -f /data/local/tmp/operator45/fresh48/stop && echo FRESH_STOP',10);(r/'preflight.txt').write_text(s)
assert not s.split('APP\n')[1].split('PARENT')[0].strip();assert not s.split('PARENT\n')[1].split('STATE')[0].strip();assert 'FRESH_STOP' in s
old='4f7cc3a62b08216b4ad3e114ec13f1468256b76ad35c94d870a83a052c27b0d2';newsha='7639af0004a2a0da079e3ad3af339cb3aa341d4a9fe9d4cdce3983db6d80d39e'
target=rt+'/lib/arm64-v8a/libnpth.so';orig=r/'original.so';new=r/'libnpth.so'
x['recv'](target,orig,15);assert hashlib.sha256(orig.read_bytes()).hexdigest()==old
ob=str(Path.home()/'a2hlab/ws/toolchains/ohos-sdk/native/llvm/bin/llvm-objdump')
out=subprocess.check_output([sys.executable,str(p.parent/'patch_npth_sigaction.py'),str(orig),str(new),'--objdump',ob],text=True,timeout=45);(r/'patch.txt').write_text(out);print(out)
assert hashlib.sha256(new.read_bytes()).hexdigest()==newsha
out=subprocess.check_output(['bash',str(p.parent/'assert_npth_all_48.sh'),str(new)],text=True,timeout=45);(r/'static-assert.txt').write_text(out);print(out)
backup='/data/local/tmp/operator45-crashes/combo48-original/libnpth.so.'+old
assert old in dev('mkdir -p /data/local/tmp/operator45-crashes/combo48-original; test -e '+backup+' || cp -p '+target+' '+backup+'; sha256sum '+backup,10)
remote='/data/local/tmp/combo48-final-libnpth.so';x['hdc'](['file','send',new.name,remote],r,15);assert newsha in dev('sha256sum '+remote,5)
s=dev('cat '+remote+' > '+target+'; chmod 755 '+target+'; sha256sum '+target,10);assert newsha in s;(r/'after.txt').write_text(s)
(r/'provenance.json').write_text(json.dumps(dict(source_commit='bb6d06e',old_sha256=old,new_sha256=newsha,backup=backup,target=target),indent=2));print(s)
