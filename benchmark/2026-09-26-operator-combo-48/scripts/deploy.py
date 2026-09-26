from pathlib import Path
import sys,json,hashlib,subprocess
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'deployment','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];rt=x['rt'];q=__import__('shlex').quote
libs={'libgodzilla-memsponge.so':'2f066332','libmonitorcollector-lib.so':'f3918bdc','libgodzilla-sysopt.so':'c92d0ea5'}
s=dev('echo APP; pidof com.ss.android.article.news; echo PARENT; pidof appspawn-x; echo STATE; test -f /data/local/tmp/operator45/stop && echo LEGACY_STOP; test -f /data/local/tmp/operator45/fresh48/stop && echo FRESH_STOP; test ! -d /data/local/tmp/operator45/fresh48/lock && echo NO_GUARD; cat /proc/sys/vm/max_map_count; sha256sum '+rt+'/webview-t-lib/libwebview_bionic_shim.so '+rt+'/lib/arm64-v8a/libnpth.so',10);(r/'before.txt').write_text(s)
assert not s.split('APP\n')[1].split('PARENT')[0].strip();assert not s.split('PARENT\n')[1].split('STATE')[0].strip()
assert all(v in s for v in ['LEGACY_STOP','FRESH_STOP','NO_GUARD','1048576','85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a','4f7cc3a62b08216b4ad3e114ec13f1468256b76ad35c94d870a83a052c27b0d2'])
records=[];expected={}
for lib,prefix in libs.items():
 target=rt+'/lib/arm64-v8a/'+lib;orig=r/'original'/lib;new=r/'patched'/lib;new.parent.mkdir(exist_ok=True)
 x['recv'](target,orig,15);oldsha=hashlib.sha256(orig.read_bytes()).hexdigest()
 s=dev('sha256sum '+target,5);assert oldsha in s
 out=subprocess.check_output([sys.executable,str(p.parent/'patch_hook_installs.py'),str(orig),str(new),'--objdump',str(Path.home()/'a2hlab/ws/toolchains/ohos-sdk/native/llvm/bin/llvm-objdump')],text=True,timeout=45)
 (r/(lib+'.patch-log.txt')).write_text(out);newsha=hashlib.sha256(new.read_bytes()).hexdigest();assert newsha.startswith(prefix),(lib,newsha)
 backup='/data/local/tmp/operator45-crashes/combo48-original/'+lib+'.'+oldsha
 s=dev('mkdir -p /data/local/tmp/operator45-crashes/combo48-original; test -e '+backup+' || cp -p '+target+' '+backup+'; sha256sum '+backup,10);assert oldsha in s
 records.append(dict(lib=lib,target=target,backup=backup,original_sha256=oldsha,patched_sha256=newsha));expected['lib/arm64-v8a/'+lib]=newsha
# Generate and validate every candidate before replacing any target.
for d in records:
 lib=d['lib'];new=r/'patched'/lib;remote='/data/local/tmp/combo48-'+lib
 x['hdc'](['file','send',new.name,remote],new.parent,15);assert d['patched_sha256'] in dev('sha256sum '+remote,5)
 s=dev('cat '+remote+' > '+d['target']+'; chmod 755 '+d['target']+'; sha256sum '+d['target']+'; ls -lZ '+d['target'],10);assert d['patched_sha256'] in s;(r/(lib+'.after.txt')).write_text(s);print(s,flush=True)
(r/'patches.json').write_text(json.dumps(dict(expected=expected,records=records),indent=2))
