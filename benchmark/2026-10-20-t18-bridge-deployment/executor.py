"""5cd R9 plus AudioTrack bridge CAS derivation. Preview default; separate exact-source admission required."""
import argparse,hashlib,json,re,shlex,sys,time,datetime,subprocess
from pathlib import Path
# Candidate source and bytes accepted by outer; unapproved sentinels still refuse before Board setup.
PLAYER='lib/arm64-v8a/libttmplayer.so'
PBEFORE='b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02'
PAFTER='0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471'
EXECUTION_REVIEW='PENDING_5CD'
DSHA='6e83e924aae709f0c90ba2a966910febb63471b7a9a6294c6dee585a73ff3b4b'
PLAYER_INPUT_REL='benchmark/2026-10-19-toutiao-video-playback/candidate-r8/deploy-inputs/libttmplayer.so'
PLAYER_METADATA='644:20011300:20011300'
PLAYER_LABEL='u:object_r:appdat:s0'
assert re.fullmatch(r'[0-7]{3,4}:20011300:20011300',PLAYER_METADATA)
assert re.fullmatch(r'u:object_r:[A-Za-z0-9_]+:s0',PLAYER_LABEL)
assert not Path(PLAYER_INPUT_REL).is_absolute() and '..' not in Path(PLAYER_INPUT_REL).parts
p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','apply','rollback'])
for key in ('boot','parent','birth','hdc','holder'):p.add_argument('--'+key)
for key in ('out','apply-plan','repo','inputs','admission'):p.add_argument('--'+key,type=Path)
p.add_argument('--start',type=float);p.add_argument('--execute',action='store_true');p.add_argument('--recovery-no-parent',action='store_true');a=p.parse_args()
assert not a.recovery_no_parent or a.mode=='rollback','recovery flag is rollback-only'
if not a.execute:
 print(json.dumps({'execute':False,'device_calls':0,'mode':a.mode,'serial':'5cd1e3dd00000000000000000923012c'}));sys.exit()
assert all([a.boot,a.hdc,a.holder,a.out,a.repo,a.inputs,a.admission,a.start]),'explicit inputs'
assert a.recovery_no_parent or (a.parent and a.birth),'live parent required except physical recovery'
assert a.out.is_absolute() and not str(a.out).startswith(('/tmp/','/private/tmp/')),'persistent output'
sha_file=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
here=Path(__file__).resolve().parent
candidate=json.loads((here/'bridge-candidate.json').read_text())
BRIDGE='liboh_adapter_bridge.so'
BBEFORE='d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b'
BAFTER=candidate['after_sha256']
assert candidate['path']==BRIDGE and candidate['before_sha256']==BBEFORE
assert isinstance(BAFTER,str) and re.fullmatch('[0-9a-f]{64}',BAFTER) and BAFTER!=BBEFORE,'candidate pin required'
assert candidate['build_status']=='PRODUCTION_BUILD_VERIFIED' and candidate['production_refs'],'production closure required'
for ref in candidate['production_refs']:
 assert not Path(ref['path']).is_absolute() and '..' not in Path(ref['path']).parts
 assert sha_file(a.repo/ref['path'])==ref['sha256'],'production receipt drift'
ad=json.loads(a.admission.read_text())
assert ad['bridge_candidate_sha256']==sha_file(here/'bridge-candidate.json'),'candidate admission drift'
assert re.fullmatch(r'[0-7]{3,4}:20011300:20011300',ad['bridge_metadata']),'fresh bridge metadata required'
assert ad['bridge_label']=='u:object_r:appdat:s0','bridge label'
assert ad['approved_by']=='outer(codex)' and ad['serial']=='5cd1e3dd00000000000000000923012c' and ad['uid']==20011300
assert ad['executor_sha256']==sha_file(Path(__file__)) and ad['parameters_sha256']==sha_file(here/'parameters.json')
assert ad['source_pins_sha256']==sha_file(here/'executor-source-pins.json') and ad['readonly_inputs_sha256']==sha_file(here/'readonly-inputs.json')
readonly=json.loads((here/'readonly-inputs.json').read_text())
assert ad['providers']==readonly['providers']
assert ad['holder']==a.holder and ad['window_start']==a.start and ad['boot']==a.boot
assert abs(a.start-datetime.datetime.fromisoformat(a.holder.split()[2]).timestamp())<1
age=time.time()-a.start;assert 0<=age<1800,'window expired'
deadline=time.monotonic()+1800-age
if a.mode!='rollback':assert age<1200,'10-minute recovery reserve'
for rel,digest in json.loads((here/'executor-source-pins.json').read_text()).items():
 assert sha_file(a.repo/rel)==digest,rel
if a.mode=='rollback':
 assert a.apply_plan and sha_file(a.apply_plan)==ad['origin_apply_plan_sha256'],'original apply-plan admission'
else:
 assert not a.apply_plan,'apply-plan only for rollback'
if a.mode=='apply':
 for name,digest in [('libopensles_android_compat.so',DSHA),('libmffmpeg.so','d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4'),('libttmplayer.so',PAFTER),(BRIDGE,BAFTER)]:
  assert sha_file(a.inputs/name)==digest,name
 check=subprocess.run([sys.executable,str(a.repo/'scripts/lab/check_frozen.py')],cwd=a.repo,capture_output=True,timeout=min(60,deadline-time.monotonic()-600))
 assert check.returncode==0,'check_frozen failed: '+check.stderr.decode('utf-8','replace')

repo=a.repo;sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
q=shlex.quote;sha=lambda x:hashlib.sha256(x).hexdigest()
RT='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d';DSO='libopensles_android_compat.so';CFG='/system/etc/init/01_westlake_u13_toutiao.cfg';CSHA='19d0201b59a6edac821feffa5f51ca8e9a08d6ba87d5bc9fd15b4e4d00775152'
MEDIA='lib/arm64-v8a/libmffmpeg.so'; MBEFORE='fecf91e1fcda600661f501ce76a97456ad7e330b584013f2b742afb680b337c9'; MAFTER='d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4'
assert re.fullmatch('[0-9a-f-]{36}',a.boot)
assert a.recovery_no_parent or (a.parent.isdigit() and a.birth.isdigit())
a.out.mkdir(parents=True,exist_ok=False)
if a.mode=='apply':
 (a.out/'frozen.stdout.txt').write_bytes(check.stdout);(a.out/'frozen.stderr.txt').write_bytes(check.stderr);(a.out/'frozen.rc.txt').write_text(str(check.returncode)+'\n')
class Board(b.Board):
 def command(self,argv,timeout=60):
  remaining=deadline-time.monotonic()-(0 if a.mode=='rollback' else 600)
  assert remaining>0,'deadline/recovery reserve'
  try:return super().command(argv,min(timeout,remaining))
  except b.BatchStop as e:
   cause=e.__cause__
   if hasattr(cause,'stdout'):
    stem=self.out/f'command-{self.index:05d}'
    stem.with_suffix('.stdout.txt').write_bytes(cause.stdout or b'');stem.with_suffix('.stderr.txt').write_bytes(cause.stderr or b'')
   raise
 def ready(self):
  super().ready();rc,held=self.command(self.lock+['held',self.serial],10)
  assert rc==0 and held.strip()==a.holder,'exact holder drift'
board=Board('5cd1e3dd00000000000000000923012c',a.hdc,'bash '+q(str(repo/'scripts/lab/board_note.sh')),a.holder.split()[0],a.out/'commands');board.boot=a.boot
read=lambda c:board.shell(c)[1]
def pathguard(path):
 return 'walk='+q(path)+'; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done\n'
def fg(path,digest,meta,label):
 return pathguard(path)+f'test -f {q(path)}\ntest "$(sha256sum {q(path)} | cut -d\' \' -f1)" = {q(digest)}\ntest "$(stat -c %a:%u:%g {q(path)})" = {q(meta)}\ntest "$(ls -Zd {q(path)} | cut -d\' \' -f1)" = {q(label)}\n'
def shell(c):return board.shell('( set -eu;\n'+c+'\n)')[1]
board.ready()
if a.recovery_no_parent:
 wid=str(json.loads(a.apply_plan.read_text())['wid'])
else:
 wm=read("hidumper -s WindowManagerService -a '-a'");(a.out/'wms.txt').write_text(wm)
 rows=[l.split() for l in wm.splitlines() if l.split() and l.split()[0]=='imehost0'];assert len(rows)==1
 wid=rows[0][3];assert wid.isdigit()
 assert len(rows[0])>=8 and rows[0][2]==str(ad['host']['pid']),'WMS host PID binding'
actual=read('sha256sum '+RT+'/run.sh').split()[0]
board.receive(RT+'/run.sh',a.out/'current.run.sh')
current_bytes=(a.out/'current.run.sh').read_bytes();assert sha(current_bytes)==actual,'run changed during byte capture'
assert read('sha256sum '+RT+'/run.sh').split()[0]==actual,'run changed after capture'
def normalize_wid(data):
 matches=list(re.finditer(rb'^export WL_PARENT_ID=([0-9]+)\n',data,re.M))
 assert len(matches)==1 and 0<int(matches[0][1])<2147483648,'single numeric WID line'
 m=matches[0];return data[:m.start()]+b'export WL_PARENT_ID=29\n'+data[m.end():],int(m[1])
normalized,current_wid=normalize_wid(current_bytes)
(a.out/'run-normalization.json').write_text(json.dumps({'original_reference_wid':29,'current_wid':current_wid,'actual_sha256':actual,'normalized_sha256':sha(normalized),'only_allowed_difference':'one exact WL_PARENT_ID numeric value'},indent=2)+'\n')
if not a.recovery_no_parent:
 assert str(current_wid)==wid,'current raw WID/live WMS'
 assert read('set -eu; envraw=$(strings /proc/'+a.parent+'/environ); printf "%s\\n" "$envraw" | sed -n "s/^WL_PARENT_ID=//p"').strip()==wid,'parent environment/WID'

meta=read('stat -c %a:%u:%g '+RT+'/run.sh').strip();assert meta=='755:20011300:20011300',meta
label=read('ls -Zd '+RT+'/run.sh').split()[0];dlabel=read('ls -Zd '+RT+'/libandroid_native_network_compat.so').split()[0]
assert label==dlabel=='u:object_r:appdat:s0',(label,dlabel)
base=repo/'benchmark/2026-10-19-toutiao-video-playback'
before=(here/'run5cd.before.reference.sh').read_bytes();after=(here/'run5cd.after.wid29.reference.sh').read_bytes()
params=json.loads((here/'parameters.json').read_text())
assert sha(before)==params['run_derivation']['before_sha256']=='5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79'
assert sha(after)==params['run_derivation']['after_wid29_reference_sha256']
assert ad['cfg_sha256']==CSHA
if a.mode!='rollback':
 assert wid=='29','fresh WID differs from exact admitted baseline; re-review required'
 assert read('set -eu; envraw=$(strings /proc/'+a.parent+'/environ); printf "%s\\n" "$envraw" | sed -n "s/^WL_PARENT_ID=//p"').strip()==wid,'parent environment/WID'

before_template,after_template=before,after
for data in [before,after]:assert data.count(b'export WL_PARENT_ID=29\n')==1
mactual=read('sha256sum '+RT+'/'+MEDIA).split()[0]
mmeta=read('stat -c %a:%u:%g '+RT+'/'+MEDIA).strip();assert mmeta=='644:20011300:20011300'
mlabel=read('ls -Zd '+RT+'/'+MEDIA).split()[0];assert mlabel=='u:object_r:appdat:s0'
pactual=read('sha256sum '+RT+'/'+PLAYER).split()[0]
pmeta=read('stat -c %a:%u:%g '+RT+'/'+PLAYER).strip();assert pmeta==PLAYER_METADATA,'player metadata drift'
plabel=read('ls -Zd '+RT+'/'+PLAYER).split()[0];assert plabel==PLAYER_LABEL,'player label drift'
bactual=read('sha256sum '+RT+'/'+BRIDGE).split()[0]
bmeta=read('stat -c %a:%u:%g '+RT+'/'+BRIDGE).strip();assert bmeta==ad['bridge_metadata'],'bridge metadata drift'
blabel=read('ls -Zd '+RT+'/'+BRIDGE).split()[0];assert blabel==ad['bridge_label'],'bridge label drift'
expected=sha(before)
apply_plan=None; dso_present=False
if a.mode=='rollback':
 assert a.apply_plan is not None,'bound original apply plan required'
 apply_plan=json.loads(a.apply_plan.read_text())
 assert apply_plan['executor_sha256']==sha_file(Path(__file__)) and apply_plan['holder']==a.holder and apply_plan['start']==a.start,'same execution window/source'
 assert apply_plan['compat_before_absent'] is True
 assert apply_plan['bridge_path']==BRIDGE and apply_plan['bridge_before_sha']==BBEFORE and apply_plan['bridge_after_sha']==BAFTER
 assert apply_plan['bridge_candidate_sha256']==sha_file(here/'bridge-candidate.json')
 assert (bmeta,blabel)==(apply_plan['bridge_metadata'],apply_plan['bridge_label'])
 assert bactual in (BBEFORE,BAFTER),'foreign bridge bytes' 
 assert apply_plan['media_before_sha']==MBEFORE and apply_plan['media_after_sha']==MAFTER
 assert apply_plan['player_path']==PLAYER and apply_plan['player_before_sha']==PBEFORE and apply_plan['player_after_sha']==PAFTER
 assert (pmeta,plabel)==(apply_plan['player_metadata'],apply_plan['player_label'])
 assert pactual in (PBEFORE,PAFTER),'foreign player bytes'
 assert (mmeta,mlabel)==(apply_plan['media_metadata'],apply_plan['media_label'])
 assert mactual in (MBEFORE,MAFTER),'foreign media bytes'
 assert apply_plan['mode']=='apply' and apply_plan['runtime']==RT and apply_plan['dso_sha']==DSHA and apply_plan['cfg_sha']==CSHA
 assert re.fullmatch('[0-9a-f-]{36}',apply_plan['boot'])
 origin_wid=str(apply_plan['wid']);assert origin_wid.isdigit(),'invalid original WID'
 assert origin_wid=='29' and apply_plan['serial']=='5cd1e3dd00000000000000000923012c' and apply_plan['uid']==20011300
 origin_before=before_template;origin_after=after_template
 assert apply_plan['before_sha']==sha(origin_before) and apply_plan['after_sha']==sha(origin_after),'original WID/template pins differ'
 assert sha(normalized) in (sha(origin_before),sha(origin_after)),(actual,'foreign run.sh beyond admitted WID value')
 assert (meta,label,dlabel)==(apply_plan['run_metadata'],apply_plan['run_label'],apply_plan['dso_label'])
 expected=actual
 dso_present=read(f'if [ -e {RT}/{DSO} ]; then echo yes; else echo no; fi').strip()=='yes'
else:
 assert actual==expected,(actual,expected,wid)
 assert mactual==MBEFORE,'media before drift'
 assert pactual==PBEFORE,'player before drift'
 assert bactual==BBEFORE,'bridge before drift'
physical_guard=f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(a.boot)}\ntest "$(sha256sum {CFG} | cut -d\' \' -f1)" = {CSHA}\n'
if a.recovery_no_parent:parent_guard=physical_guard
else:
 parent_guard=f'''test "$(cat /proc/sys/kernel/random/boot_id)" = {q(a.boot)}
 row=$(cat /proc/{a.parent}/stat); rest=${{row##*) }}; set -- $rest; test "${{20}}" = {q(a.birth)}; test "$1" != Z; test "$1" != X; test "$2" = 1
 u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/{a.parent}/status); set -- $u; test "$1:$2:$3:$4" = 0:0:0:0
 test "$(sed -n 's/^TracerPid:[[:space:]]*//p' /proc/{a.parent}/status)" = 0
 test "$(readlink /proc/{a.parent}/ns/mnt)" = {q(ad['parent_mnt'])}
 test "$(readlink /proc/{a.parent}/ns/mnt)" != "$(readlink /proc/1/ns/mnt)"
 
 test "$(sha256sum /proc/{a.parent}/exe | cut -d' ' -f1)" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c
 test "$(stat -L -c %d:%i {RT}/run.sh)" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/run.sh)"
 test "$(sha256sum {CFG} | cut -d' ' -f1)" = {CSHA}
 '''
for control,digest in readonly['controls'].items():
 assert control.startswith('/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/') and re.fullmatch('[0-9a-f]{64}',digest)
 parent_guard+=pathguard(control)+f'test "$(sha256sum {q(control)} | cut -d\' \' -f1)" = {digest}\n'
network_guard=fg(RT+'/libandroid_native_network_compat.so','f6c354d1513071533fddcc91749f44e57a626177a584fb1bb9f48bf6446ef01e','644:20011300:20011300',dlabel)
if not a.recovery_no_parent:network_guard+=f'test "$(stat -L -c %d:%i {RT}/libandroid_native_network_compat.so)" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/libandroid_native_network_compat.so)"\n'
parent_guard+=network_guard
pre=parent_guard+fg(RT+'/run.sh',expected,meta,label)+fg(RT+'/'+MEDIA,mactual,mmeta,mlabel)
if not a.recovery_no_parent:pre+=f'test "$(stat -L -c %d:%i {RT}/{MEDIA})" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/{MEDIA})"\n'
pre+=fg(RT+'/'+PLAYER,pactual,pmeta,plabel)
if not a.recovery_no_parent:pre+=f'test "$(stat -L -c %d:%i {RT}/{PLAYER})" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/{PLAYER})"\n'
pre+=fg(RT+'/'+BRIDGE,bactual,bmeta,blabel)
if not a.recovery_no_parent:
 private_bridge=f'/proc/{a.parent}/root/data/local/tmp/asx/{BRIDGE}'
 # /proc/PID/root is the intentional, identity-bound namespace link.
 pre+=fg(private_bridge,bactual,bmeta,blabel)[len(pathguard(private_bridge)):]
 pre+=f'test "$(stat -L -c %d:%i {RT}/{BRIDGE})" = "$(stat -L -c %d:%i {private_bridge})"\n'
pre+=fg(RT+'/'+DSO,DSHA,'644:20011300:20011300',dlabel) if dso_present else pathguard(RT+'/'+DSO)+f'test ! -e {RT}/{DSO}\n'
if a.mode=='rollback':
 backup=RT+'/run.sh.t18-5cd-before-'+apply_plan['boot'][:8]
 media_backup=RT+'/'+MEDIA+'.t18-5cd-before-'+apply_plan['boot'][:8]
 player_backup=RT+'/'+PLAYER+'.t18-5cd-before-'+apply_plan['boot'][:8]
 bridge_backup=RT+'/'+BRIDGE+'.t18-5cd-before-'+apply_plan['boot'][:8]
 for target,back,digest,fmeta,flabel,current in [('run.sh',backup,apply_plan['before_sha'],meta,label,actual),(MEDIA,media_backup,MBEFORE,mmeta,mlabel,mactual),(PLAYER,player_backup,PBEFORE,pmeta,plabel,pactual),(BRIDGE,bridge_backup,BBEFORE,bmeta,blabel,bactual)]:
  present=read('if [ -e '+q(back)+' ]; then echo yes; else echo no; fi').strip()=='yes'
  if present:pre+=fg(back,digest,fmeta,flabel)
  else:assert current==digest,'missing backup for changed target'


host=ad['host'];assert host['uid']==20011300 and str(host['pid']).isdigit() and str(host['birth']).isdigit()
assert re.fullmatch(r'mnt:\[[0-9]+\]',ad['parent_mnt'])
hostguard=f"r=$(cat /proc/{host['pid']}/stat); z=${{r##*) }}; set -- $z; test \"${{20}}\" = {host['birth']}; test \"$1\" != Z; u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/{host['pid']}/status); set -- $u; test \"$1:$2:$3:$4\" = 20011300:20011300:20011300:20011300\n"
hostguard+=f'cmdraw=$(strings /proc/{host["pid"]}/cmdline); printf "%s\\n" "$cmdraw" | grep -Fx org.westlake.imehost >/dev/null\n'
if not a.recovery_no_parent:pre+=hostguard
for provider in ad['providers']:
 assert provider['path'] in ('/system/lib64/libOpenSLES.so',RT+'/liblog.so') and re.fullmatch('[0-9a-f]{64}',provider['sha256'])
 pre+=f"test \"$(sha256sum {provider['path']} | cut -d' ' -f1)\" = {provider['sha256']}\n"
assert {v['path'] for v in ad['providers']}=={'/system/lib64/libOpenSLES.so',RT+'/liblog.so'}
shell(pre)
plan={'mode':a.mode,'compat_before_absent':True,'serial':board.serial,'uid':20011300,'holder':a.holder,'start':a.start,'admission_sha256':sha_file(a.admission),'executor_sha256':sha_file(Path(__file__)),'boot':a.boot,'parent':a.parent,'parent_birth':a.birth,'physical_only':a.recovery_no_parent,'wid':wid,'before_sha':sha(before),'after_sha':sha(after),'run_metadata':meta,'run_label':label,'dso_label':dlabel,'dso_sha':DSHA,'cfg_sha':CSHA,'runtime':RT,'media_before_sha':MBEFORE,'media_after_sha':MAFTER,'media_metadata':mmeta,'media_label':mlabel,'player_path':PLAYER,'player_before_sha':PBEFORE,'player_after_sha':PAFTER,'player_metadata':pmeta,'player_label':plabel,'player_input_rel':PLAYER_INPUT_REL}
plan.update(bridge_path=BRIDGE,bridge_before_sha=BBEFORE,bridge_after_sha=BAFTER,bridge_metadata=bmeta,bridge_label=blabel,bridge_candidate_sha256=sha_file(here/'bridge-candidate.json'))
if apply_plan is not None:plan['origin_apply_plan_sha256']=sha(a.apply_plan.read_bytes());plan['origin_apply_boot']=apply_plan['boot'];plan['origin_apply_wid']=origin_wid
(a.out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');(a.out/'before.run.sh').write_bytes(before);(a.out/'after.run.sh').write_bytes(after)
if a.mode=='preflight':print(json.dumps(plan));sys.exit()
stage='/data/local/tmp/t18-5cd-'+a.mode+'-'+a.boot[:8]+'-'+sha(str(a.out).encode())[:8];shell(parent_guard+pathguard(stage)+f'test ! -e {stage}; mkdir {stage}; chmod 700 {stage}\n')
new=before if a.mode=='rollback' else after;newfile=a.out/('before.run.sh' if a.mode=='rollback' else 'after.run.sh')
board.send(newfile,stage+'/run.sh');shell(f'test "$(sha256sum {stage}/run.sh | cut -d\' \' -f1)" = {sha(new)}\n')
if a.mode=='apply':
 dso=a.inputs/DSO;assert sha(dso.read_bytes())==DSHA
 board.send(dso,stage+'/'+DSO);shell(f'test "$(sha256sum {stage}/{DSO} | cut -d\' \' -f1)" = {DSHA}\n')
if a.mode=='apply':
 media=a.inputs/'libmffmpeg.so';assert sha(media.read_bytes())==MAFTER
 board.send(media,stage+'/libmffmpeg.so');shell(f'test "$(sha256sum {stage}/libmffmpeg.so | cut -d\' \' -f1)" = {MAFTER}\n')
if a.mode=='apply':
 player=a.inputs/'libttmplayer.so';assert sha(player.read_bytes())==PAFTER
 board.send(player,stage+'/libttmplayer.so');shell(f'test "$(sha256sum {stage}/libttmplayer.so | cut -d\' \' -f1)" = {PAFTER}\n')
if a.mode=='apply':
 bridge=a.inputs/BRIDGE;assert sha(bridge.read_bytes())==BAFTER
 board.send(bridge,stage+'/'+BRIDGE);shell(f'test "$(sha256sum {stage}/{BRIDGE} | cut -d\' \' -f1)" = {BAFTER}\n')
def swap(name,source,digest,fmeta,flabel,preimage):
 dst=RT+'/'+name;tmp=dst+'.ttvideo-'+a.boot[:8]+'-'+sha(str(a.out).encode())[:8]+'.tmp';mode,uid,gid=fmeta.split(':')
 before_guard=fg(dst,preimage,fmeta,flabel) if preimage is not None else pathguard(dst)+f'test ! -e {q(dst)}\n'
 return pathguard(tmp)+f'test ! -e {q(tmp)}\ncp {q(source)} {q(tmp)}\nchown {uid}:{gid} {q(tmp)}\nchmod {mode} {q(tmp)}\nchcon {q(flabel)} {q(tmp)}\n'+fg(tmp,digest,fmeta,flabel)+before_guard+f'mv {q(tmp)} {q(dst)}\n'+fg(dst,digest,fmeta,flabel)
script=pre
if a.mode=='apply':
 backup=RT+'/run.sh.t18-5cd-before-'+a.boot[:8]
 script+=pathguard(backup)+f'test ! -e {q(backup)}\ncp -p {RT}/run.sh {q(backup)}\n'+fg(backup,expected,meta,label)
if a.mode=='apply':
 media_backup=RT+'/'+MEDIA+'.t18-5cd-before-'+a.boot[:8]
 script+=pathguard(media_backup)+f'test ! -e {q(media_backup)}\ncp -p {RT}/{MEDIA} {q(media_backup)}\n'+fg(media_backup,MBEFORE,mmeta,mlabel)
if a.mode=='apply':
 player_backup=RT+'/'+PLAYER+'.t18-5cd-before-'+a.boot[:8]
 script+=pathguard(player_backup)+f'test ! -e {q(player_backup)}\ncp -p {RT}/{PLAYER} {q(player_backup)}\n'+fg(player_backup,PBEFORE,pmeta,plabel)
if a.mode=='apply':
 bridge_backup=RT+'/'+BRIDGE+'.t18-5cd-before-'+a.boot[:8]
 script+=pathguard(bridge_backup)+f'test ! -e {q(bridge_backup)}\ncp -p {RT}/{BRIDGE} {q(bridge_backup)}\n'+fg(bridge_backup,BBEFORE,bmeta,blabel)
# All four original backups are complete and verified before the first target swap.
if a.mode!='rollback' or bactual!=BBEFORE:script+=swap(BRIDGE,bridge_backup if a.mode=='rollback' else stage+'/'+BRIDGE,BBEFORE if a.mode=='rollback' else BAFTER,bmeta,blabel,bactual)
if a.mode!='rollback' or mactual!=MBEFORE:script+=swap(MEDIA,media_backup if a.mode=='rollback' else stage+'/libmffmpeg.so',MBEFORE if a.mode=='rollback' else MAFTER,mmeta,mlabel,mactual)
if a.mode!='rollback' or pactual!=PBEFORE:script+=swap(PLAYER,player_backup if a.mode=='rollback' else stage+'/libttmplayer.so',PBEFORE if a.mode=='rollback' else PAFTER,pmeta,plabel,pactual)
if a.mode=='apply':script+=swap(DSO,stage+'/'+DSO,DSHA,'644:20011300:20011300',dlabel,None)
script+=fg(RT+'/run.sh',expected,meta,label)
if a.mode!='rollback' or actual!=sha(before):script+=swap('run.sh',stage+'/run.sh',sha(new),meta,label,expected)
if a.mode=='rollback' and dso_present:script+=fg(RT+'/'+DSO,DSHA,'644:20011300:20011300',dlabel)+f'rm {RT}/{DSO}\ntest ! -e {RT}/{DSO}\n'
completion='PHYSICAL_FILES_RESTORED_REQUIRES_FRESH_BOOT' if a.mode=='rollback' else 'VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED'
script+=parent_guard+'echo '+completion+'\n'
(a.out/'swap.sh').write_text(script);result=shell(script);assert completion in result
(a.out/'result.json').write_text(json.dumps(dict(plan,status=completion,backup=backup,media_backup=media_backup,player_backup=player_backup,bridge_backup=bridge_backup),indent=2)+'\n');print(result)
