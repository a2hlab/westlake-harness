"""Deploy only speed run.sh and guarded JIT preparation onto an idle baseline."""
from pathlib import Path
import sys,json,re,hashlib
p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'install','inspect'];x={'__file__':str(p)};exec(p.read_text(),x)
r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];hdc=x['hdc'];rt=x['rt'];F='/data/local/tmp/operator45/selfheal48'
assert not dev('pidof com.ss.android.article.news appspawn-x',5).strip()
assert 'STOPPED' in dev('test -f '+F+'/stop && test ! -d '+F+'/lock && echo STOPPED',5)
expected={}
for l in (x['R'].parent/'r1control48/deployment/after-hashes.txt').read_text().splitlines():
 h,n=l.split(maxsplit=1)
 if n!=rt+'/run.sh':expected[n]=h
out=dev('sha256sum '+' '.join(expected),20);(r/'baseline-hashes.txt').write_text(out)
for n,h in expected.items():assert h+'  '+n in out,n
lock=json.loads((x['ROOT']/'aot/speed-lock.json').read_text())
# Deployment SHA values derive from the rebuilt, locally validated speed package.
artifacts={'toutiao.odex':'c7ad2a0b58dc2fe5a18e92196a37183f0d41012689c1c20ade1c500a99914a32','toutiao.vdex':'e6f5c1aaf69bdec6975fc08c238f6090f7ef1a0e784e098c9ee35d476748106d','toutiao.art':'5ed9e8b2dcb44ae82808532610b26b1d48e462fecf73eaaa3c4c8395c991f3ee'}
s=dev('sha256sum '+' '.join(rt+'/oat/arm64/'+n for n in artifacts),30);(r/'aot-sha.txt').write_text(s)
for n,h in artifacts.items():assert h+'  '+rt+'/oat/arm64/'+n in s
backup=rt+'/operator-speed50-launcher-backup'
print(dev('test -e '+backup+' || { mkdir -p '+backup+'; cp '+F+'/watchdog.sh '+backup+'/watchdog.sh; cp '+rt+'/run.sh '+backup+'/run.sh; }; sha256sum '+backup+'/*',8))
# Preserve the original no-speed launcher separately; trial run.sh may already be fast.
x['hdc'](['file','send','run.sh',backup+'/run.baseline.sh'],x['R']/'preflight',10)
s=p.with_name('watchdog.sh.in').read_text()
for k,v in {'RUNTIME':rt,'STAGE':x['stage'],'SOCKET':x['c']['socket']}.items():s=s.replace('@@'+k+'@@',v)
assert '@@' not in s;(r/'watchdog.sh').write_text(s)
run=(x['R']/'preflight/run.sh').read_text();run,n=re.subn(r'^(?:export WESTLAKE_OH_JIT_FILE_CACHE_DIR=.*|unset WESTLAKE_OH_JIT_FILE_CACHE_DIR)$','export WESTLAKE_OH_JIT_FILE_CACHE_DIR=/data/data/com.ss.android.article.news/code_cache/art-volatile',run,flags=re.M);assert n==1;(r/'run.sh').write_text(run)
hdc(['file','send','watchdog.sh',F+'/watchdog.sh'],r,10)
hdc(['file','send','run.sh',rt+'/run.sh'],r,10)
hdc(['file','send','prepare_jit50.sh',rt+'/prepare_jit50.sh'],p.parent,10)
s=dev('/system/bin/sh -n '+F+'/watchdog.sh && /system/bin/sh -n '+rt+'/prepare_jit50.sh && /system/bin/sh -n '+rt+'/run.sh; sha256sum '+F+'/watchdog.sh '+rt+'/run.sh '+rt+'/prepare_jit50.sh',8);(r/'installed.txt').write_text(s);print(s)
