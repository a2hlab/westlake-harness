import sys,os,json,shlex,hashlib,subprocess,time
from pathlib import Path
repo=Path.cwd();base=Path.home()/'.local/share/westlake/toutiao-resume-20261020'
sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
sys.path.insert(0,str(repo/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13'));from core import stat_fields,EXE_SHA,SERVER_SHA,validate
mode,boot=sys.argv[1:3];out=base/('r13-early-server-'+mode);out.mkdir(exist_ok=False)
board=b.Board('61b0657200000000000000000324012c','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','bash '+shlex.quote(str(repo/'scripts/lab/board_note.sh')),'outer(codex)',out/'commands');board.boot=boot;board.ready()
remote='/data/local/tmp/r13-lldb-'+boot[:8]+'-window3';server=remote+'/lldb-server'
def sh(c):return board.shell('( set -eu; '+c+'; echo R13_OK )')[1]
def read(c):return board.shell(c)[1]
def hcmd(args):
 rc,t=board.command(board.hdc+args);assert rc==0,(args,t);return t
if mode=='stage':
 src=Path.home()/'Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/lib64/clang/12.0.8/lib/linux/aarch64/lldb-server';assert hashlib.sha256(src.read_bytes()).hexdigest()==SERVER_SHA
 sh('test ! -e '+remote+'; mkdir '+remote+'; chmod 700 '+remote)
 board.send(src,server);sh('test "$(sha256sum '+server+' | cut -d\' \' -f1)" = '+SERVER_SHA+'; chmod 700 '+server)
 (out/'help.txt').write_text(read(server+' gdbserver --help'))
 print(remote)
elif mode=='attach':
 parent,pbirth,child,cbirth=map(int,sys.argv[3:7]);a=json.loads((base/'r13-admission-template.json').read_text());a['identity']={'boot':boot,'parent':parent,'parent_birth':pbirth,'child':child,'child_birth':cbirth,'uid':20011206,'parent_uid':0,'parent_exe_sha256':EXE_SHA,'child_exe_sha256':EXE_SHA}
 for pid,birth in [(parent,pbirth),(child,cbirth)]:
  assert stat_fields(read('cat /proc/%d/stat'%pid))['birth']==birth
  assert read('sha256sum /proc/%d/exe'%pid).split()[0]==EXE_SHA
 status=read('cat /proc/%d/status'%child);assert '\nTracerPid:\t0\n' in status
 for role,m in a['modules'].items():
  p='/proc/%d/root%s'%(child,m['remote_path']);assert read('sha256sum '+p).split()[0]==m['sha256'];m['device'],m['inode']=map(int,read('stat -L -c %d:%i '+p).strip().split(':'))
 assert read('sha256sum '+server).split()[0]==SERVER_SHA
 forwards=hcmd(['-t',board.serial,'fport','ls']);(out/'forwards-before.txt').write_text(forwards);assert '5039' not in forwards
 tcp=read('cat /proc/net/tcp');tcp6=read('cat /proc/net/tcp6');assert not any(len(f)>3 and f[1].endswith(':13AF') and f[3]=='0A' for l in (tcp+'\n'+tcp6).splitlines() if (f:=l.split()));(out/'tcp-before.txt').write_text(tcp+'\n'+tcp6)
 hcmd(['-t',board.serial,'fport','tcp:5039','tcp:5039']);fw=hcmd(['-t',board.serial,'fport','ls']);assert len([l for l in fw.splitlines() if '5039' in l])==1 and fw.count('tcp:5039')==2
 guard='r=$(cat /proc/%d/stat); z=${r##*) }; set -- $z; test "${20}" = %d; test "$(cat /proc/sys/kernel/random/boot_id)" = %s; '%(child,cbirth,boot)
 sh(guard+'( '+server+' gdbserver 127.0.0.1:5039 --attach '+str(child)+' >'+remote+'/server.stdout 2>'+remote+'/server.stderr < /dev/null & echo $! >'+remote+'/launch.pid )')
 time.sleep(2)
 status=read('cat /proc/%d/status'%child);(out/'child-status.txt').write_text(status);tracer=int(next(x.split(':')[1].strip() for x in status.splitlines() if x.startswith('TracerPid:')));assert tracer>0
 s=stat_fields(read('cat /proc/%d/stat'%tracer));st=read('cat /proc/%d/status'%tracer);uid=int(next(x.split(':')[1].split()[0] for x in st.splitlines() if x.startswith('Uid:')))
 assert read('sha256sum /proc/%d/exe'%tracer).split()[0]==SERVER_SHA
 cmd=read('od -An -v -tx1 /proc/%d/cmdline'%tracer);(out/'server-cmdline-hex.txt').write_text(cmd);assert bytes.fromhex(cmd)==b'\0'.join(x.encode() for x in [server,'gdbserver','127.0.0.1:5039','--attach',str(child)])+b'\0'
 assert int(read('cat '+remote+'/launch.pid').strip())==tracer
 tcp=read('cat /proc/net/tcp');fds=read('ls -l /proc/%d/fd'%tracer);(out/'server-tcp.txt').write_text(tcp);(out/'server-fds.txt').write_text(fds);rows=[l.split() for l in tcp.splitlines() if '0100007F:13AF' in l and ' 0A ' in l];assert len(rows)==1 and 'socket:['+rows[0][9]+']' in fds
 a['server']={'pid':tracer,'birth':s['birth'],'uid':uid,'sha256':SERVER_SHA};a['holder']=subprocess.check_output(['bash',str(repo/'scripts/lab/board_note.sh'),'held',board.serial],text=True).strip();a['created_at']=time.time();a['expires_at']=a['created_at']+600;a['execution_enabled']=True;validate(a)
 (base/'r13-early-admission.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps({'server':a['server'],'identity':a['identity']}))
else:raise ValueError(mode)
