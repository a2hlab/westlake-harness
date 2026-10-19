"""One-off outer execution of the reviewed two-file card using bms_batch.Board."""
import argparse,hashlib,json,re,shlex,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','apply','rollback']);p.add_argument('--boot',required=True);p.add_argument('--parent',required=True);p.add_argument('--birth',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--apply-plan',type=Path);a=p.parse_args()
repo=Path.cwd();sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
q=shlex.quote;sha=lambda x:hashlib.sha256(x).hexdigest()
RT='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d';DSO='libopensles_android_compat.so';DSHA='9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f';CFG='/system/etc/init/01_westlake_u13_toutiao.cfg';CSHA='91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e'
assert re.fullmatch('[0-9a-f-]{36}',a.boot) and a.parent.isdigit() and a.birth.isdigit()
a.out.mkdir(parents=True,exist_ok=False)
board=b.Board('61b0657200000000000000000324012c','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+q(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',a.out/'commands');board.boot=a.boot
read=lambda c:board.shell(c)[1]
def pathguard(path):
 return 'walk='+q(path)+'; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done\n'
def fg(path,digest,meta,label):
 return pathguard(path)+f'test -f {q(path)}\ntest "$(sha256sum {q(path)} | cut -d\' \' -f1)" = {q(digest)}\ntest "$(stat -c %a:%u:%g {q(path)})" = {q(meta)}\nls -Zd {q(path)} | grep -F {q(label)} >/dev/null\n'
def shell(c):return board.shell('( set -eu;\n'+c+'\n)')[1]
board.ready()
wm=read("hidumper -s WindowManagerService -a '-a'");(a.out/'wms.txt').write_text(wm)
rows=[l.split() for l in wm.splitlines() if l.split() and l.split()[0]=='imehost0'];assert len(rows)==1
wid=rows[0][3];assert wid.isdigit()
actual=read('sha256sum '+RT+'/run.sh').split()[0]
meta=read('stat -c %a:%u:%g '+RT+'/run.sh').strip();assert meta=='755:20011206:20011206',meta
label=read('ls -Zd '+RT+'/run.sh').split()[0];dlabel=read('ls -Zd '+RT+'/libandroid_native_network_compat.so').split()[0]
assert re.fullmatch(r'u:object_r:[A-Za-z0-9_]+:s0',label) and re.fullmatch(r'u:object_r:[A-Za-z0-9_]+:s0',dlabel),(label,dlabel)
base=repo/'benchmark/2026-10-19-toutiao-video-playback'
before=(base/'static/selected-change/run.sh.d3518cef.orig').read_bytes();after=(base/'static/selected-change/run.sh.candidate').read_bytes()
assert sha(before)=='d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4' and sha(after)=='ea98494255b05699ca24b134e6ada8849b023b4ab59d3d7e291194cfa8425f73'
for data in [before,after]:assert data.count(b'export WL_PARENT_ID=33\n')==1
before=before.replace(b'export WL_PARENT_ID=33\n',f'export WL_PARENT_ID={wid}\n'.encode());after=after.replace(b'export WL_PARENT_ID=33\n',f'export WL_PARENT_ID={wid}\n'.encode())
expected=sha(before)
apply_plan=None; dso_present=False
if a.mode=='rollback':
 assert a.apply_plan is not None,'bound original apply plan required'
 apply_plan=json.loads(a.apply_plan.read_text())
 assert apply_plan['mode']=='apply' and apply_plan['runtime']==RT and apply_plan['dso_sha']==DSHA and apply_plan['cfg_sha']==CSHA
 assert re.fullmatch('[0-9a-f-]{36}',apply_plan['boot'])
 assert actual in (sha(before),sha(after)),(actual,'foreign run.sh')
 assert (meta,label,dlabel)==(apply_plan['run_metadata'],apply_plan['run_label'],apply_plan['dso_label'])
 expected=actual
 dso_present=read(f'if [ -e {RT}/{DSO} ]; then echo yes; else echo no; fi').strip()=='yes'
else:assert actual==expected,(actual,expected,wid)
parent_guard=f'''test "$(cat /proc/sys/kernel/random/boot_id)" = {q(a.boot)}
row=$(cat /proc/{a.parent}/stat); rest=${{row##*) }}; set -- $rest; test "${{20}}" = {q(a.birth)}
test "$(sha256sum /proc/{a.parent}/exe | cut -d' ' -f1)" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
test "$(stat -L -c %d:%i {RT}/run.sh)" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/run.sh)"
test "$(sha256sum {CFG} | cut -d' ' -f1)" = {CSHA}
'''
pre=parent_guard+fg(RT+'/run.sh',expected,meta,label)
pre+=fg(RT+'/'+DSO,DSHA,'644:20011206:20011206',dlabel) if dso_present else pathguard(RT+'/'+DSO)+f'test ! -e {RT}/{DSO}\n'
if a.mode=='rollback':
 backup=RT+'/run.sh.ttvideo-before-'+apply_plan['boot'][:8]
 pre+=fg(backup,apply_plan['before_sha'],meta,label)

shell(pre)
plan={'mode':a.mode,'boot':a.boot,'parent':a.parent,'parent_birth':a.birth,'wid':wid,'before_sha':sha(before),'after_sha':sha(after),'run_metadata':meta,'run_label':label,'dso_label':dlabel,'dso_sha':DSHA,'cfg_sha':CSHA,'runtime':RT}
(a.out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');(a.out/'before.run.sh').write_bytes(before);(a.out/'after.run.sh').write_bytes(after)
if a.mode=='preflight':print(json.dumps(plan));sys.exit()
stage='/data/local/tmp/ttvideo-'+a.mode+'-'+a.boot[:8]+'-'+sha(str(a.out).encode())[:8];shell(parent_guard+pathguard(stage)+f'test ! -e {stage}; mkdir {stage}; chmod 700 {stage}\n')
new=before if a.mode=='rollback' else after;newfile=a.out/('before.run.sh' if a.mode=='rollback' else 'after.run.sh')
board.send(newfile,stage+'/run.sh');shell(f'test "$(sha256sum {stage}/run.sh | cut -d\' \' -f1)" = {sha(new)}\n')
if a.mode=='apply':
 dso=base/'candidate/deploy-inputs'/DSO;assert sha(dso.read_bytes())==DSHA
 board.send(dso,stage+'/'+DSO);shell(f'test "$(sha256sum {stage}/{DSO} | cut -d\' \' -f1)" = {DSHA}\n')
def swap(name,source,digest,fmeta,flabel):
 dst=RT+'/'+name;tmp=dst+'.ttvideo-'+a.boot[:8]+'.tmp';mode,uid,gid=fmeta.split(':')
 return pathguard(tmp)+f'test ! -e {q(tmp)}\ncp {q(source)} {q(tmp)}\nchown {uid}:{gid} {q(tmp)}\nchmod {mode} {q(tmp)}\nchcon {q(flabel)} {q(tmp)}\n'+fg(tmp,digest,fmeta,flabel)+f'mv {q(tmp)} {q(dst)}\n'+fg(dst,digest,fmeta,flabel)
script=pre
if a.mode=='apply':
 backup=RT+'/run.sh.ttvideo-before-'+a.boot[:8]
 script+=pathguard(backup)+f'test ! -e {q(backup)}\ncp -p {RT}/run.sh {q(backup)}\n'+fg(backup,expected,meta,label)
if a.mode=='apply':script+=swap(DSO,stage+'/'+DSO,DSHA,'644:20011206:20011206',dlabel)
script+=fg(RT+'/run.sh',expected,meta,label)+swap('run.sh',stage+'/run.sh',sha(new),meta,label)
if a.mode=='rollback' and dso_present:script+=fg(RT+'/'+DSO,DSHA,'644:20011206:20011206',dlabel)+f'rm {RT}/{DSO}\ntest ! -e {RT}/{DSO}\n'
script+=parent_guard+'echo VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED\n'
(a.out/'swap.sh').write_text(script);result=shell(script);assert 'VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED' in result
(a.out/'result.json').write_text(json.dumps(dict(plan,status='PLACED_REQUIRES_FRESH_BOOT',backup=backup),indent=2)+'\n');print(result)
