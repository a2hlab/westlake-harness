"""Exact textual derivation of the archived R8 CAS executor; no device operations."""
import hashlib,argparse,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=BASE.parents[1]);args=ap.parse_args()
rel='benchmark/2026-10-19-toutiao-video-playback/candidate-r8/deployment/video_guarded_window_r8.py'
DONOR=args.repo/rel
assert hashlib.sha256(DONOR.read_bytes()).hexdigest()==json.loads((BASE/'reused-source-pins.json').read_text())[rel]
s=DONOR.read_text()
def change(old,new,count=1):
 global s
 assert s.count(old)==count,(old[:100],s.count(old),count)
 s=s.replace(old,new)
change('"""DISABLED r8 draft; exact artifacts and independent admission are pending."""','"""5cd R8 CAS derivation. Preview default; separate exact-source admission required."""')
change('import argparse,hashlib,json,re,shlex,sys','import argparse,hashlib,json,re,shlex,sys,time,datetime,subprocess')
s=s.replace('20011206','20011300')
change("EXECUTION_REVIEW='APPROVED'","EXECUTION_REVIEW='PENDING_5CD'")
a=s.index('if (EXECUTION_REVIEW');z=s.index('assert re.fullmatch',a)
s=s[:a]+s[z:]
change("p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','apply','rollback']);p.add_argument('--boot',required=True);p.add_argument('--parent',required=True);p.add_argument('--birth',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--apply-plan',type=Path);a=p.parse_args()",'''p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','apply','rollback'])
for key in ('boot','parent','birth','hdc','holder'):p.add_argument('--'+key)
for key in ('out','apply-plan','repo','inputs','admission'):p.add_argument('--'+key,type=Path)
p.add_argument('--start',type=float);p.add_argument('--execute',action='store_true');a=p.parse_args()
if not a.execute:
 print(json.dumps({'execute':False,'device_calls':0,'mode':a.mode,'serial':'5cd1e3dd00000000000000000923012c'}));sys.exit()
assert all([a.boot,a.parent,a.birth,a.hdc,a.holder,a.out,a.repo,a.inputs,a.admission,a.start]),'explicit inputs'
assert a.out.is_absolute() and not str(a.out).startswith(('/tmp/','/private/tmp/')),'persistent output'
sha_file=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
here=Path(__file__).resolve().parent
ad=json.loads(a.admission.read_text())
assert ad['approved_by']=='outer(codex)' and ad['serial']=='5cd1e3dd00000000000000000923012c' and ad['uid']==20011300
assert ad['executor_sha256']==sha_file(Path(__file__)) and ad['parameters_sha256']==sha_file(here/'parameters.json')
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
 for name,digest in [('libopensles_android_compat.so',DSHA),('libmffmpeg.so','d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4'),('libttmplayer.so',PAFTER)]:
  assert sha_file(a.inputs/name)==digest,name
 check=subprocess.run([sys.executable,str(a.repo/'scripts/lab/check_frozen.py')],cwd=a.repo,capture_output=True)
 assert check.returncode==0,'check_frozen failed: '+check.stderr.decode('utf-8','replace')
''')
change('repo=Path.cwd();','repo=a.repo;')
change("CSHA='91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e'","CSHA='19d0201b59a6edac821feffa5f51ca8e9a08d6ba87d5bc9fd15b4e4d00775152'")
change("board=b.Board('61b0657200000000000000000324012c','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+q(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',a.out/'commands');board.boot=a.boot",'''class Board(b.Board):
 def command(self,argv,timeout=60):
  remaining=deadline-time.monotonic()-(0 if a.mode=='rollback' else 600)
  assert remaining>0,'deadline/recovery reserve'
  return super().command(argv,min(timeout,remaining))
 def ready(self):
  super().ready();rc,held=self.command(self.lock+['held',self.serial],10)
  assert rc==0 and held.strip()==a.holder,'exact holder drift'
board=Board('5cd1e3dd00000000000000000923012c',a.hdc,'bash '+q(str(repo/'scripts/lab/board_note.sh')),a.holder.split()[0],a.out/'commands');board.boot=a.boot''')
change("before=(base/'static/selected-change/run.sh.d3518cef.orig').read_bytes();after=(base/'candidate-r3/deploy-inputs/run.sh').read_bytes()\nassert sha(before)=='d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4' and sha(after)=='79275cf9f9a72be72beb551b978ee5f2faaed84129980aa5c79d2f51acd040d5'",'''before=(here/'run5cd.before.reference.sh').read_bytes();after=(here/'run5cd.after.wid29.reference.sh').read_bytes()
params=json.loads((here/'parameters.json').read_text())
assert sha(before)==params['run_derivation']['before_sha256']=='5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79'
assert sha(after)==params['run_derivation']['after_wid29_reference_sha256']
assert ad['cfg_sha256']==CSHA
if a.mode!='rollback':
 assert wid=='29','fresh WID differs from exact admitted baseline; re-review required'
 assert read('tr "\\\\000" "\\\\n" < /proc/'+a.parent+'/environ | sed -n "s/^WL_PARENT_ID=//p"').strip()==wid,'parent environment/WID'
''')
change("for data in [before,after]:assert data.count(b'export WL_PARENT_ID=33\\n')==1\nbefore=before.replace(b'export WL_PARENT_ID=33\\n',f'export WL_PARENT_ID={wid}\\n'.encode());after=after.replace(b'export WL_PARENT_ID=33\\n',f'export WL_PARENT_ID={wid}\\n'.encode())","for data in [before,after]:assert data.count(b'export WL_PARENT_ID=29\\n')==1")
change("origin_before=before_template.replace(b'export WL_PARENT_ID=33\\n',f'export WL_PARENT_ID={origin_wid}\\n'.encode())\n origin_after=after_template.replace(b'export WL_PARENT_ID=33\\n',f'export WL_PARENT_ID={origin_wid}\\n'.encode())","assert origin_wid=='29' and apply_plan['serial']=='5cd1e3dd00000000000000000923012c' and apply_plan['uid']==20011300\n origin_before=before_template;origin_after=after_template")
change("assert actual in (sha(before),sha(after),sha(origin_before),sha(origin_after)),(actual,'foreign run.sh')","assert actual in (sha(origin_before),sha(origin_after)),(actual,'foreign run.sh')")
# Bind parent state, UID and namespace before any path mutation; admission carries fresh host identity.
change("row=$(cat /proc/{a.parent}/stat); rest=${{row##*) }}; set -- $rest; test \"${{20}}\" = {q(a.birth)}",'''row=$(cat /proc/{a.parent}/stat); rest=${{row##*) }}; set -- $rest; test "${{20}}" = {q(a.birth)}; test "$1" != Z; test "$1" != X; test "$2" = 1
u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/{a.parent}/status); set -- $u; test "$1:$2:$3:$4" = 0:0:0:0
test "$(sed -n 's/^TracerPid:[[:space:]]*//p' /proc/{a.parent}/status)" = 0
test "$(readlink /proc/{a.parent}/ns/mnt)" = {q(ad['parent_mnt'])}
test "$(readlink /proc/{a.parent}/ns/mnt)" != "$(readlink /proc/1/ns/mnt)"
''')
# Original-profile facts supplied as an exact admission, not defaults inferred from61b.
change("shell(pre)\nplan=",'''host=ad['host'];assert host['uid']==20011300 and str(host['pid']).isdigit() and str(host['birth']).isdigit()
assert re.fullmatch(r'mnt:\\[[0-9]+\\]',ad['parent_mnt'])
hostguard=f"r=$(cat /proc/{host['pid']}/stat); z=${{r##*) }}; set -- $z; test \\\"${{20}}\\\" = {host['birth']}; test \\\"$1\\\" != Z; u=$(sed -n 's/^Uid:[[:space:]]*//p' /proc/{host['pid']}/status); set -- $u; test \\\"$1:$2:$3:$4\\\" = 20011300:20011300:20011300:20011300\\n"
pre+=hostguard
for provider in ad['providers']:
 assert provider['path'] in ('/system/lib64/libOpenSLES.so','/system/lib64/liblog.so') and re.fullmatch('[0-9a-f]{64}',provider['sha256'])
 pre+=f"test \\\"$(sha256sum {provider['path']} | cut -d' ' -f1)\\\" = {provider['sha256']}\\n"
assert {v['path'] for v in ad['providers']}=={'/system/lib64/libOpenSLES.so','/system/lib64/liblog.so'}
shell(pre)
plan=''')
change("'mode':a.mode,'boot':a.boot", "'mode':a.mode,'serial':board.serial,'uid':20011300,'holder':a.holder,'start':a.start,'admission_sha256':sha_file(a.admission),'executor_sha256':sha_file(Path(__file__)),'boot':a.boot")
change("dso=base/'candidate-r8/deploy-inputs'/DSO;","dso=a.inputs/DSO;")
change("media=base/'candidate-r3/deploy-inputs/libmffmpeg.so';","media=a.inputs/'libmffmpeg.so';")
change("player=repo/PLAYER_INPUT_REL;","player=a.inputs/'libttmplayer.so';")
# New backup namespace avoids an old R8 same-boot backup collision.
s=s.replace('.ttvideo-before-', '.t16-5cd-before-').replace("stage='/data/local/tmp/ttvideo-'","stage='/data/local/tmp/t16-5cd-'")
# In partial apply with no swaps, absent backups must not prevent no-op recovery. Validate every present backup;
# any after-image still requires its original backup. Then use original source only for actual after-images.
old="pre+=fg(backup,apply_plan['before_sha'],meta,label)\n media_backup=RT+'/'+MEDIA+'.t16-5cd-before-'+apply_plan['boot'][:8]\n pre+=fg(media_backup,MBEFORE,mmeta,mlabel)\n player_backup=RT+'/'+PLAYER+'.t16-5cd-before-'+apply_plan['boot'][:8]\n pre+=fg(player_backup,PBEFORE,pmeta,plabel)"
new="""media_backup=RT+'/'+MEDIA+'.t16-5cd-before-'+apply_plan['boot'][:8]
 player_backup=RT+'/'+PLAYER+'.t16-5cd-before-'+apply_plan['boot'][:8]
 for target,back,digest,fmeta,flabel,current in [('run.sh',backup,apply_plan['before_sha'],meta,label,actual),(MEDIA,media_backup,MBEFORE,mmeta,mlabel,mactual),(PLAYER,player_backup,PBEFORE,pmeta,plabel,pactual)]:
  present=read('if [ -e '+q(back)+' ]; then echo yes; else echo no; fi').strip()=='yes'
  if present:pre+=fg(back,digest,fmeta,flabel)
  else:assert current==digest,'missing backup for changed target'
"""
change(old,new)
change("script+=swap(MEDIA,media_backup if a.mode=='rollback' else stage+'/libmffmpeg.so',MBEFORE if a.mode=='rollback' else MAFTER,mmeta,mlabel,mactual)","if a.mode!='rollback' or mactual!=MBEFORE:script+=swap(MEDIA,media_backup if a.mode=='rollback' else stage+'/libmffmpeg.so',MBEFORE if a.mode=='rollback' else MAFTER,mmeta,mlabel,mactual)")
change("script+=swap(PLAYER,player_backup if a.mode=='rollback' else stage+'/libttmplayer.so',PBEFORE if a.mode=='rollback' else PAFTER,pmeta,plabel,pactual)","if a.mode!='rollback' or pactual!=PBEFORE:script+=swap(PLAYER,player_backup if a.mode=='rollback' else stage+'/libttmplayer.so',PBEFORE if a.mode=='rollback' else PAFTER,pmeta,plabel,pactual)")
change("script+=fg(RT+'/run.sh',expected,meta,label)+swap('run.sh',stage+'/run.sh',sha(new),meta,label,expected)","script+=fg(RT+'/run.sh',expected,meta,label)\nif a.mode!='rollback' or actual!=sha(before):script+=swap('run.sh',stage+'/run.sh',sha(new),meta,label,expected)")
# Stage still runs only after all read-only gates. Save check_frozen raw host execution receipt.
change("a.out.mkdir(parents=True,exist_ok=False)","a.out.mkdir(parents=True,exist_ok=False)\nif a.mode=='apply':\n (a.out/'frozen.stdout.txt').write_bytes(check.stdout);(a.out/'frozen.stderr.txt').write_bytes(check.stderr);(a.out/'frozen.rc.txt').write_text(str(check.returncode)+'\\n')")
# Authorized physical-only recovery; no-parent never enables apply.
change("p.add_argument('--start',type=float);p.add_argument('--execute',action='store_true');a=p.parse_args()","p.add_argument('--start',type=float);p.add_argument('--execute',action='store_true');p.add_argument('--recovery-no-parent',action='store_true');a=p.parse_args()\nassert not a.recovery_no_parent or a.mode=='rollback','recovery flag is rollback-only'")
change("assert all([a.boot,a.parent,a.birth,a.hdc,a.holder,a.out,a.repo,a.inputs,a.admission,a.start]),'explicit inputs'","assert all([a.boot,a.hdc,a.holder,a.out,a.repo,a.inputs,a.admission,a.start]),'explicit inputs'\nassert a.recovery_no_parent or (a.parent and a.birth),'live parent required except physical recovery'")
change("assert re.fullmatch('[0-9a-f-]{36}',a.boot) and a.parent.isdigit() and a.birth.isdigit()","assert re.fullmatch('[0-9a-f-]{36}',a.boot)\nassert a.recovery_no_parent or (a.parent.isdigit() and a.birth.isdigit())")
change('wm=read("hidumper -s WindowManagerService -a \'-a\'");(a.out/\'wms.txt\').write_text(wm)\nrows=[l.split() for l in wm.splitlines() if l.split() and l.split()[0]==\'imehost0\'];assert len(rows)==1\nwid=rows[0][3];assert wid.isdigit()\n','if a.recovery_no_parent:\n wid=str(json.loads(a.apply_plan.read_text())[\'wid\'])\nelse:\n wm=read("hidumper -s WindowManagerService -a \'-a\'");(a.out/\'wms.txt\').write_text(wm)\n rows=[l.split() for l in wm.splitlines() if l.split() and l.split()[0]==\'imehost0\'];assert len(rows)==1\n wid=rows[0][3];assert wid.isdigit()\n')
change("assert apply_plan['media_before_sha']==MBEFORE and apply_plan['media_after_sha']==MAFTER","assert apply_plan['executor_sha256']==sha_file(Path(__file__)) and apply_plan['holder']==a.holder and apply_plan['start']==a.start,'same execution window/source'\n assert apply_plan['compat_before_absent'] is True\n assert apply_plan['media_before_sha']==MBEFORE and apply_plan['media_after_sha']==MAFTER")
change('parent_guard=f\'\'\'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(a.boot)}\nrow=$(cat /proc/{a.parent}/stat); rest=${{row##*) }}; set -- $rest; test "${{20}}" = {q(a.birth)}; test "$1" != Z; test "$1" != X; test "$2" = 1\nu=$(sed -n \'s/^Uid:[[:space:]]*//p\' /proc/{a.parent}/status); set -- $u; test "$1:$2:$3:$4" = 0:0:0:0\ntest "$(sed -n \'s/^TracerPid:[[:space:]]*//p\' /proc/{a.parent}/status)" = 0\ntest "$(readlink /proc/{a.parent}/ns/mnt)" = {q(ad[\'parent_mnt\'])}\ntest "$(readlink /proc/{a.parent}/ns/mnt)" != "$(readlink /proc/1/ns/mnt)"\n\ntest "$(sha256sum /proc/{a.parent}/exe | cut -d\' \' -f1)" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c\ntest "$(stat -L -c %d:%i {RT}/run.sh)" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/run.sh)"\ntest "$(sha256sum {CFG} | cut -d\' \' -f1)" = {CSHA}\n\'\'\'\n','physical_guard=f\'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(a.boot)}\\ntest "$(sha256sum {CFG} | cut -d\\\' \\\' -f1)" = {CSHA}\\n\'\nif a.recovery_no_parent:parent_guard=physical_guard\nelse:\n parent_guard=f\'\'\'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(a.boot)}\n row=$(cat /proc/{a.parent}/stat); rest=${{row##*) }}; set -- $rest; test "${{20}}" = {q(a.birth)}; test "$1" != Z; test "$1" != X; test "$2" = 1\n u=$(sed -n \'s/^Uid:[[:space:]]*//p\' /proc/{a.parent}/status); set -- $u; test "$1:$2:$3:$4" = 0:0:0:0\n test "$(sed -n \'s/^TracerPid:[[:space:]]*//p\' /proc/{a.parent}/status)" = 0\n test "$(readlink /proc/{a.parent}/ns/mnt)" = {q(ad[\'parent_mnt\'])}\n test "$(readlink /proc/{a.parent}/ns/mnt)" != "$(readlink /proc/1/ns/mnt)"\n \n test "$(sha256sum /proc/{a.parent}/exe | cut -d\' \' -f1)" = a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c\n test "$(stat -L -c %d:%i {RT}/run.sh)" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/run.sh)"\n test "$(sha256sum {CFG} | cut -d\' \' -f1)" = {CSHA}\n \'\'\'\n')
change('pre+=f\'test "$(stat -L -c %d:%i {RT}/{MEDIA})" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/{MEDIA})"\\n\'','if not a.recovery_no_parent:pre+=f\'test "$(stat -L -c %d:%i {RT}/{MEDIA})" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/{MEDIA})"\\n\'')
change('pre+=f\'test "$(stat -L -c %d:%i {RT}/{PLAYER})" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/{PLAYER})"\\n\'','if not a.recovery_no_parent:pre+=f\'test "$(stat -L -c %d:%i {RT}/{PLAYER})" = "$(stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/{PLAYER})"\\n\'')
change('pre+=hostguard','if not a.recovery_no_parent:pre+=hostguard')
change("('/system/lib64/libOpenSLES.so','/system/lib64/liblog.so')","('/system/lib64/libOpenSLES.so',RT+'/liblog.so')")
change("{'/system/lib64/libOpenSLES.so','/system/lib64/liblog.so'}","{'/system/lib64/libOpenSLES.so',RT+'/liblog.so'}")
change("'mode':a.mode,'serial':board.serial","'mode':a.mode,'compat_before_absent':True,'serial':board.serial")
change("'parent':a.parent,'parent_birth':a.birth","'parent':a.parent,'parent_birth':a.birth,'physical_only':a.recovery_no_parent")
change("script+=parent_guard+'echo VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED\\n'","completion='PHYSICAL_FILES_RESTORED_REQUIRES_FRESH_BOOT' if a.mode=='rollback' else 'VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED'\nscript+=parent_guard+'echo '+completion+'\\n'")
change("assert 'VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED' in result",'assert completion in result')
change("status='PLACED_REQUIRES_FRESH_BOOT'",'status=completion')
# Authorized single-WID-line equivalence after actual startup-source proof.
change("actual=read('sha256sum '+RT+'/run.sh').split()[0]",'actual=read(\'sha256sum \'+RT+\'/run.sh\').split()[0]\nboard.receive(RT+\'/run.sh\',a.out/\'current.run.sh\')\ncurrent_bytes=(a.out/\'current.run.sh\').read_bytes();assert sha(current_bytes)==actual,\'run changed during byte capture\'\nassert read(\'sha256sum \'+RT+\'/run.sh\').split()[0]==actual,\'run changed after capture\'\ndef normalize_wid(data):\n matches=list(re.finditer(rb\'^export WL_PARENT_ID=([0-9]+)\\n\',data,re.M))\n assert len(matches)==1 and 0<int(matches[0][1])<2147483648,\'single numeric WID line\'\n m=matches[0];return data[:m.start()]+b\'export WL_PARENT_ID=29\\n\'+data[m.end():],int(m[1])\nnormalized,current_wid=normalize_wid(current_bytes)\n(a.out/\'run-normalization.json\').write_text(json.dumps({\'original_reference_wid\':29,\'current_wid\':current_wid,\'actual_sha256\':actual,\'normalized_sha256\':sha(normalized),\'only_allowed_difference\':\'one exact WL_PARENT_ID numeric value\'},indent=2)+\'\\n\')\nif not a.recovery_no_parent:\n assert str(current_wid)==wid,\'current raw WID/live WMS\'\n assert read(\'tr "\\\\000" "\\\\n" < /proc/\'+a.parent+\'/environ | sed -n "s/^WL_PARENT_ID=//p"\').strip()==wid,\'parent environment/WID\'\n')
change("assert actual in (sha(origin_before),sha(origin_after)),(actual,'foreign run.sh')","assert sha(normalized) in (sha(origin_before),sha(origin_after)),(actual,'foreign run.sh beyond admitted WID value')")
# Bind the freshly supplied profile and preserve partial transport receipts.
change("assert ad['executor_sha256']==sha_file(Path(__file__)) and ad['parameters_sha256']==sha_file(here/'parameters.json')","assert ad['executor_sha256']==sha_file(Path(__file__)) and ad['parameters_sha256']==sha_file(here/'parameters.json')\nassert ad['source_pins_sha256']==sha_file(here/'executor-source-pins.json') and ad['readonly_inputs_sha256']==sha_file(here/'readonly-inputs.json')\nreadonly=json.loads((here/'readonly-inputs.json').read_text())\nassert ad['providers']==readonly['providers']")
change('capture_output=True)\n assert check.returncode','capture_output=True,timeout=min(60,deadline-time.monotonic()-600))\n assert check.returncode')
change('return super().command(argv,min(timeout,remaining))',"try:return super().command(argv,min(timeout,remaining))\n  except b.BatchStop as e:\n   cause=e.__cause__\n   if hasattr(cause,'stdout'):\n    stem=self.out/f'command-{self.index:05d}'\n    stem.with_suffix('.stdout.txt').write_bytes(cause.stdout or b'');stem.with_suffix('.stderr.txt').write_bytes(cause.stderr or b'')\n   raise")
change("assert re.fullmatch(r'u:object_r:[A-Za-z0-9_]+:s0',label) and re.fullmatch(r'u:object_r:[A-Za-z0-9_]+:s0',dlabel),(label,dlabel)","assert label==dlabel=='u:object_r:appdat:s0',(label,dlabel)")
change("pre=parent_guard+fg(RT+'/run.sh',expected,meta,label)",'for control,digest in readonly[\'controls\'].items():\n assert control.startswith(\'/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/\') and re.fullmatch(\'[0-9a-f]{64}\',digest)\n parent_guard+=pathguard(control)+f\'test "$(sha256sum {q(control)} | cut -d\\\' \\\' -f1)" = {digest}\\n\'\npre=parent_guard+fg(RT+\'/run.sh\',expected,meta,label)')
change('wid=rows[0][3];assert wid.isdigit()',"wid=rows[0][3];assert wid.isdigit()\n assert len(rows[0])>=8 and rows[0][2]==str(ad['host']['pid']),'WMS host PID binding'")
change('if not a.recovery_no_parent:pre+=hostguard','hostguard+=f"tr \'\\\\000\' \'\\\\n\' < /proc/{host[\'pid\']}/cmdline | grep -Fx org.westlake.imehost >/dev/null\\n"\nif not a.recovery_no_parent:pre+=hostguard')
# Actual OH environment lacks tr; strings is verified by the outer read.
change(' assert read(\'tr "\\\\000" "\\\\n" < /proc/\'+a.parent+\'/environ | sed -n "s/^WL_PARENT_ID=//p"\').strip()==wid,\'parent environment/WID\'',' assert read(\'set -eu; envraw=$(strings /proc/\'+a.parent+\'/environ); printf "%s\\\\n" "$envraw" | sed -n "s/^WL_PARENT_ID=//p"\').strip()==wid,\'parent environment/WID\'',count=2)
change('hostguard+=f"tr \'\\\\000\' \'\\\\n\' < /proc/{host[\'pid\']}/cmdline | grep -Fx org.westlake.imehost >/dev/null\\n"','hostguard+=f\'cmdraw=$(strings /proc/{host["pid"]}/cmdline); printf "%s\\\\n" "$cmdraw" | grep -Fx org.westlake.imehost >/dev/null\\n\'')
(BASE/'executor.py').write_text(s)
print(hashlib.sha256(s.encode()).hexdigest())
