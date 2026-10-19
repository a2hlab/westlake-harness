#!/usr/bin/env python3
"""Archive exact R15 local evidence; optional new remote upload, no device calls."""
import argparse,hashlib,json,os,shlex,subprocess,tarfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
LANE=HERE.parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/check_frozen.py').is_file())
REMOTE_NAME='toutiao-window-r15-offline-20261020'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def need(x,s):
 if not x:raise RuntimeError(s)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--outer-root',default=str(Path.home()/'.local/share/westlake/toutiao-resume-20261020/r15-outer-independent'));p.add_argument('--remote-root',default=os.environ.get('HW248_ARTIFACT_ROOT'));p.add_argument('--upload',action='store_true');a=p.parse_args()
 out=Path(a.out).expanduser().resolve();need(not str(out).startswith(('/tmp/','/private/tmp/')),'persistent OUT required');need(not out.is_relative_to(LANE/'.private'),'output cannot be inside archived input');out.mkdir(parents=True,exist_ok=False)
 outer=Path(a.outer_root).expanduser().resolve();need(outer.is_dir(),'outer originals missing')
 items={}
 def add(src,name):
  need(src.is_file(),'missing input: '+name);need(name not in items,'duplicate member')
  items[name]={'source':src.resolve(),'sha256':sha(src),'bytes':src.stat().st_size,'file_symlink_materialized':src.is_symlink()}
 indexed=json.loads((LANE/'evidence/private-raw-index.json').read_text())['files']
 need(len(indexed)==1149,'expected frozen 1149-entry input index')
 indexed_paths=set()
 for r in indexed:
  rel=r['path'].removeprefix('$T4_REPO/');src=REPO/rel;need(src.is_relative_to(LANE/'.private'),'index escaped private input');need(sha(src)==r['sha256'] and src.stat().st_size==r['bytes'],'frozen raw input drift')
  indexed_paths.add(src.resolve())
 actual={x.resolve() for x in (LANE/'.private').rglob('*') if x.is_file()}
 need(actual==indexed_paths,'private directory membership differs from frozen index')
 for src in sorted(actual):add(src,'lane-private/'+str(src.relative_to(LANE/'.private')))
 outerfiles=sorted(x for x in outer.rglob('*') if x.is_file())
 for src in outerfiles:add(src,'outer-independent/'+str(src.relative_to(outer)))
 for rel,h in json.loads((outer/'source-pins.json').read_text()).items():need(sha(REPO/rel)==h,'outer source differs from current accepted source')
 frozen=json.loads((LANE/'manifest.json').read_text())
 for r in frozen['files']:need(sha(REPO/r['path'])==r['sha256'],'frozen delivery drift')
 source_paths=(LANE/'landing-paths.txt').read_text().splitlines()
 for rel in source_paths:add(REPO/rel,'source-snapshot/'+rel)
 for rel in ['specs/toutiao-video-playback/project.spec.md','benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline/window_module.c','benchmark/2026-10-19-toutiao-video-playback/candidate-r14-offline/window_module.h']:
  add(REPO/rel,'source-snapshot/'+rel)
 add(Path(__file__).resolve(),'archive/prepare_archive.py')
 manifest={'schema':'r15-private-archive-members-v1','groups':{'lane-private':len(actual),'outer-independent':len(outerfiles),'source-snapshot':len(source_paths)+3,'archive-script':1},'files':[{'path':n,'sha256':v['sha256'],'bytes':v['bytes'],'file_symlink_materialized':v['file_symlink_materialized']} for n,v in sorted(items.items())]}
 (out/'members.json').write_text(json.dumps(manifest,indent=2)+'\n');add(out/'members.json','archive/members.json')
 archive=out/'window.tar.gz'
 with tarfile.open(archive,'w:gz') as tar:
  for n,v in sorted(items.items()):tar.add(v['source'],arcname=n,recursive=False)
 with tarfile.open(archive,'r:gz') as tar:
  members=tar.getmembers();need(len(members)==len(items) and {x.name for x in members}==set(items),'archive membership mismatch')
  for m in members:
   need(m.isfile(),'non-regular member');f=tar.extractfile(m);need(f is not None,'missing archive member data');need(hashlib.sha256(f.read()).hexdigest()==items[m.name]['sha256'] and m.size==items[m.name]['bytes'],'archived bytes mismatch')
 need(all(sha(v['source'])==v['sha256'] for v in items.values()),'input changed while packing')
 receipt={'token':'r15-archive-ready','archive_sha256':sha(archive),'bytes':archive.stat().st_size,'member_count':len(items),'groups':manifest['groups'],'local_member_sha_verified':True,'remote':'HW248_ARTIFACT_ROOT/'+REMOTE_NAME+'/window.tar.gz','remote_verified':False,'commands':[],'frozen_delivery_unchanged':True,'scope':'OFFLINE_ADAPTER_ONLY_NOT_DEPLOYABLE'}
 def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 remote_root=a.remote_root
 if not remote_root:
  prior=Path.home()/'.local/share/westlake/toutiao-resume-20261019/video-r10-window-archive/receipt.json'
  if prior.is_file():remote_root=str(Path(json.loads(prior.read_text())['remote']).parent.parent)
 if remote_root and remote_root.startswith('/'):
  remote=remote_root.rstrip('/')+'/'+REMOTE_NAME
  cmds=[['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','test ! -e '+shlex.quote(remote)+' && mkdir -p '+shlex.quote(remote)],['scp','-o','BatchMode=yes','-o','ConnectTimeout=10',str(archive),'hw248:'+remote+'/window.tar.gz'],['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','sha256sum '+shlex.quote(remote+'/window.tar.gz')+' && stat -c %s '+shlex.quote(remote+'/window.tar.gz')]]
  (out/'remote-commands.private.json').write_text(json.dumps(cmds,indent=2)+'\n')
 else:cmds=[];receipt['remote_root_missing']=True
 save()
 if a.upload:
  need(cmds,'provide HW248_ARTIFACT_ROOT; no remote root inferred')
  for i,argv in enumerate(cmds):
   stem='remote-'+str(i);(out/(stem+'.command.json')).write_text(json.dumps(argv,indent=2)+'\n');start=time.time()
   with (out/(stem+'.stdout')).open('wb') as so,(out/(stem+'.stderr')).open('wb') as se:
    try:rc=subprocess.run(argv,stdout=so,stderr=se,timeout=180).returncode
    except subprocess.TimeoutExpired:rc=124
    except OSError as exc:se.write((str(exc)+'\n').encode());rc=127
   (out/(stem+'.rc')).write_text(str(rc)+'\n');receipt['commands'].append({'name':stem,'rc':rc,'seconds':time.time()-start,'files':{x.name:{'sha256':sha(x),'bytes':x.stat().st_size} for x in sorted(out.glob(stem+'.*'))}});save()
   if rc:receipt['upload_status']='STOPPED_AT_FIRST_ERROR';save();print(json.dumps(receipt));return 2
  lines=(out/'remote-2.stdout').read_text().splitlines();need(len(lines)==2 and lines[0].split()[0]==receipt['archive_sha256'] and int(lines[1])==receipt['bytes'],'remote hash/size mismatch');receipt['remote_verified']=True;receipt['upload_status']='VERIFIED';save()
 print(json.dumps(receipt));return 0
if __name__=='__main__':raise SystemExit(main())
