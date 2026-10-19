# Portable archival derivative, NOT the byte-exact executed original. See archive-recipe-provenance.json.
"""Archive the closed r5 raw window, preserving exact commands and local receipts."""
from pathlib import Path
import hashlib,json,subprocess,tarfile,shlex,os
base=Path.home()/'.local/share/westlake/toutiao-resume-20261019'
assert json.loads((base/'video-r5-window-close.json').read_text())['lock_released'] is True
out=base/'video-r5-window-archive';out.mkdir(exist_ok=False)
files=sorted([p for p in base.glob('video-r5-*') if p!=out]+[base/n for n in ['video_guarded_window_r6.py','video_r5_control.py','live_tools.py','board_step.py','wait_boot_ready.py','archive_video_r5.py']])
archive=out/'window.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for p in files:tar.add(p,arcname=p.name)
h=hashlib.sha256(archive.read_bytes()).hexdigest();remote=os.environ['HW248_ARTIFACT_ROOT'].rstrip('/')+'/toutiao-video-r5-20261019'
cmds=[['ssh','-o','BatchMode=yes','hw248','test ! -e '+shlex.quote(remote)+' && mkdir -p '+shlex.quote(remote)],['scp',str(archive),'hw248:'+remote+'/window.tar.gz'],['ssh','-o','BatchMode=yes','hw248','sha256sum '+shlex.quote(remote+'/window.tar.gz')+'; stat -c %s '+shlex.quote(remote+'/window.tar.gz')]]
for i,cmd in enumerate(cmds):
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=180);(out/f'command-{i}.json').write_text(json.dumps({'argv':cmd,'rc':p.returncode},indent=2));(out/f'command-{i}.stdout').write_text(p.stdout);(out/f'command-{i}.stderr').write_text(p.stderr);assert p.returncode==0,(i,p.stderr)
assert p.stdout.splitlines()[0].split()[0]==h
assert int(p.stdout.splitlines()[1])==archive.stat().st_size
r={'archive_sha256':h,'bytes':archive.stat().st_size,'remote':remote+'/window.tar.gz','remote_verified':True,'members':[p.name for p in files]};(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
