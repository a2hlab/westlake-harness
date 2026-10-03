"""Fresh real production PATH exercise; no device access, isolated reports."""
from pathlib import Path
import os,subprocess,sys,re
H=Path(__file__).resolve().parent;W=H.parents[4];M=W/'westlake-harness'
surface=sys.argv[1];env=dict(os.environ,WORKSPACES=str(W),MAC_HOME=str(Path.home()),LAB_HOME=re.search(r'hw248:([^\s,]+?)/aosp-14\.0\.0_r1-art',(W/'westlake-inputs/aosp-14.0.0_r1-src/SOURCE.txt').read_text()).group(1))
if surface=='mac':
 ndk=Path.home()/'Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/bin'
 dex=sorted((Path.home()/'Library/Android/sdk/build-tools').glob('*/dexdump'))[-1].parent
 env['PATH']=os.pathsep.join(map(str,[W/'westlake-inputs/venv/bin',ndk,dex,W/'westlake-inputs/toolshim']))+os.pathsep+env['PATH']
 command=[sys.executable,H/'gate_master.py','--surface','mac']
else:
 command=['orb','-m','a2hlab','env','WORKSPACES='+str(W),'MAC_HOME='+str(Path.home()),'LAB_HOME='+env['LAB_HOME'],'PATH='+str(M/'benchmark/2026-10-01-u7-executor/.vm-tools')+':/usr/local/bin:/usr/bin:/bin','TMPDIR='+str(M/'benchmark/2026-10-01-u7-executor/.vm-tmp'),'python3',H/'gate_master.py','--surface','vm']
with (H/('production-'+surface+'.txt')).open('w') as out:p=subprocess.run(list(map(str,command)),env=env,stdout=out,stderr=subprocess.STDOUT)
print(surface,'rc='+str(p.returncode),flush=True);raise SystemExit(p.returncode)
