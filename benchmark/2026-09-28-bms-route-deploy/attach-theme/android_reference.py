"""Mac controller: locked, original-APK Android reference; no user data clearing."""
from pathlib import Path
import subprocess,json,hashlib,time
r=Path(__file__).resolve().parent;o=r/'android-reference';o.mkdir(exist_ok=True)
adb='/Users/zhaoyue/Library/Android/sdk/platform-tools/adb';serial='N100CU025C18D000128'
lock='/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh'
def run(args,binary=False,allow_absent=False):
 held=subprocess.check_output([lock,'held',serial],text=True);assert held.split()[0]=='cx-t0'
 p=subprocess.run([adb,'-s',serial,*args],capture_output=True,timeout=150,check=False)
 if p.returncode and not (allow_absent and p.returncode==1 and not p.stdout.strip()):raise RuntimeError(p.stderr.decode())
 return p.stdout if binary else p.stdout.decode()
apk=Path('/Users/zhaoyue/.cache/b6-wikipedia-original.apk')
subprocess.run(['orb','-m','a2hlab','cp','/home/zhaoyue/a2hlab/app-inputs/wikipedia/wikipedia.apk',str(apk)],check=True)
sha=hashlib.sha256(apk.read_bytes()).hexdigest();assert sha=='eba82a0f77940d8a6be5bd2e53723675a59859a6c8a51be5e50bd034fc77101f'
prior=run(['shell','pm','path','org.wikipedia'],allow_absent=True);assert not prior.strip(),prior
(o/'install.txt').write_text(run(['install',str(apk)]))
path=run(['shell','pm','path','org.wikipedia']).strip().removeprefix('package:')
installed=run(['shell','sha256sum',path]);assert installed.split()[0]==sha
run(['shell','input','keyevent','KEYCODE_WAKEUP']);run(['shell','wm','dismiss-keyguard']);run(['shell','input','keyevent','KEYCODE_HOME']);time.sleep(1)
(o/'home.png').write_bytes(run(['exec-out','screencap','-p'],binary=True))
run(['shell','uiautomator','dump','/data/local/tmp/b6-reference-ui.xml'])
(o/'home.xml').write_text(run(['shell','cat','/data/local/tmp/b6-reference-ui.xml']))
(o/'record.json').write_text(json.dumps({'serial':serial,'sha256':sha,'installed_hash':installed,'apk':str(apk),'installed_path':path,'previously_installed':False,'desktop_clicked':False},indent=2)+'\n')
print('installed original APK; launcher captured')
