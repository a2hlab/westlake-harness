#!/usr/bin/env python3
"""Verify the prior archive, pin actual build inputs, and package only the new closure."""
import argparse,hashlib,json,shlex,subprocess,tarfile,io
from pathlib import Path,PurePosixPath
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--main',type=Path,required=True);ap.add_argument('--old',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
a.out.mkdir(parents=True,exist_ok=False);home=Path.home();rawroot=home/'.local/share/westlake';members={};deps=[]
def alias(p):return str(p).replace(str(home),'$HOME')
def add(p,name):
 p=Path(p);b=p.read_bytes();h=hashlib.sha256(b).hexdigest();assert name not in members;members[name]={'sha256':h,'bytes':len(b),'source':alias(p),'data':b}
def blob(b,name):
 assert name not in members;members[name]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'source':'generated metadata','data':b}
oldarchive=a.old/'production.tar.gz';oldsha='57441330fa9751085cd2f199e917a2717d14d94247d761d4509cdd1d07688b20';assert sha(oldarchive)==oldsha
index=json.loads((a.old/'members.json').read_text());oldrows={x['path']:x for x in index['files']};bycontent={};seen=set();inputmanifest=None
with tarfile.open(oldarchive,'r:gz') as t:
 for m in t:
  if not m.isfile():continue
  b=t.extractfile(m).read();h=hashlib.sha256(b).hexdigest()
  if m.name=='archive/members.json':
   assert b==(a.old/'members.json').read_bytes();continue
  row=oldrows[m.name];assert (h,len(b))==(row['sha256'],row['bytes']);seen.add(m.name);bycontent.setdefault((h,len(b)),[]).append(m.name)
  if m.name=='raw/T20_RAW/repro-inputs/index.json':inputmanifest=json.loads(b)
assert seen==set(oldrows) and inputmanifest is not None
blob(json.dumps({'archive_sha256':oldsha,'members':len(seen),'all_members_rehashed':True,'input_manifest_member':'raw/T20_RAW/repro-inputs/index.json','input_manifest':inputmanifest},indent=2).encode()+b'\n','previous-archive/verification.json')
add(a.old/'members.json','previous-archive/members.json')
receipt=rawroot/'t23-egl-build/production-02/receipt.json';production=json.loads(receipt.read_text())
for path,expected in production['inputs'].items():
 p=Path(path);assert p.stat().st_size==expected['bytes'] and sha(p)==expected['sha256'];key=(expected['sha256'],expected['bytes']);row={'input':alias(p),**expected}
 if key in bycontent:row.update({'location':'prior_archive','archive_sha256':oldsha,'member':bycontent[key][0]})
 else:
  member='new-inputs/sha256/'+expected['sha256'];row.update({'location':'this_archive','member':member})
  if member not in members:add(p,member)
 deps.append(row)
blob(json.dumps({'production_receipt_sha256':sha(receipt),'all_actual_inputs_verified':True,'dependencies':deps},indent=2).encode()+b'\n','dependency-resolution.json')
for name,root in [('production-01',rawroot/'t23-egl-build/production-01'),('production-02',rawroot/'t23-egl-build/production-02'),('host',rawroot/'t23-egl-host'),('consumer-relocations',rawroot/'t23-consumer-relocations'),('surface-exports',rawroot/'t22-egl-reuse-static')]:
 for p in sorted(root.rglob('*')):
  if p.is_file():add(p,'raw/'+name+'/'+str(p.relative_to(root)))
for rel in ['benchmark/2026-10-20-t23-egl-import','specs/toutiao-video-playback/t23-egl-import.spec.md','tools/spec-checks/tests/toutiao_t23_egl_import.rs']:
 files=subprocess.check_output(['git','ls-tree','-r','--name-only','4efff3066','--',rel],cwd=a.repo,text=True).splitlines()
 for f in files:blob(subprocess.check_output(['git','show','4efff3066:'+f],cwd=a.repo),'source/'+f)
for rel in ['scripts/lab/abi_diff.py','scripts/lab/check_frozen.py','knowledge/frozen/frozen.json','benchmark/2026-10-20-t23-egl-blueprint-peer/blueprint.json','sources/api-implementations/source-build-native691/westlake/framework/webview-shim/webview_bionic_shim.c','sources/api-implementations/source-build-native691/westlake/native/hwui/oh_surface_texture.cpp','benchmark/2026-10-01-r77-first-blocker-scoring/README.md']:
 add(a.main/rel,'reference/'+rel)
for p in [a.main.parent/'westlake-inputs/seal-artifacts-20261012/sha256/a11c9154ca16dd7acf5e3ea99727ae37c25b1b4494a9133816bc58c553c128e2',rawroot/'toutiao-resume-20261020/provider-surface-readonly/libsurface.z.so']:
 h=sha(p);key=(h,p.stat().st_size)
 if key not in bycontent:add(p,'analysis-inputs/sha256/'+h)
blob((subprocess.check_output(['git','rev-parse','4efff3066'],cwd=a.repo,text=True).strip()+'\n').encode(),'source-commit.txt')
add(Path(__file__),'archiver/pack.py')
archive=a.out/'production.tar.gz'
with tarfile.open(archive,'w:gz') as t:
 for name,row in sorted(members.items()):
  info=tarfile.TarInfo(name);info.size=row['bytes'];info.mode=0o644;info.mtime=0;t.addfile(info,io.BytesIO(row['data']))
verified=set()
with tarfile.open(archive,'r:gz') as t:
 for m in t:
  assert m.isfile();b=t.extractfile(m).read();r=members[m.name];assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];verified.add(m.name)
assert verified==set(members)
public={'files':[{'path':name,**{k:v for k,v in row.items() if k!='data'}} for name,row in sorted(members.items())]};(a.out/'members.json').write_text(json.dumps(public,indent=2)+'\n')
(a.out/'dependency-resolution.json').write_text(json.dumps({'dependencies':deps},indent=2)+'\n')
r={'status':'LOCAL_VERIFIED_REMOTE_PENDING','archive_sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(members),'all_members_rehashed':True,'prior_archive_sha256':oldsha,'prior_members_rehashed':len(seen),'production02_inputs':len(deps),'prior_dependencies':sum(d['location']=='prior_archive' for d in deps),'new_dependencies':sum(d['location']=='this_archive' for d in deps),'members_index_sha256':sha(a.out/'members.json'),'dependency_resolution_sha256':sha(a.out/'dependency-resolution.json'),'remote_verified':False}
oldcmd=json.loads((a.old/'remote-commands.private.json').read_text());priorremote=oldcmd[1][-1];host,remotefile=priorremote.split(':',1);remotedir=str(PurePosixPath(remotefile).parent.parent/'toutiao-t23-egl-import-production-20261020');target=remotedir+'/production.tar.gz'
cmds=[['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',host,'mkdir -p '+shlex.quote(remotedir)],['scp','-o','BatchMode=yes','-o','ConnectTimeout=10',str(archive),host+':'+target],['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',host,'sha256sum '+shlex.quote(target)+' && stat -c %s '+shlex.quote(target)]]
(a.out/'remote-commands.private.json').write_text(json.dumps(cmds,indent=2)+'\n');(a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
