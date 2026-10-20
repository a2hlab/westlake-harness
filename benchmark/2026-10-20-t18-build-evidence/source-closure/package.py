#!/usr/bin/env python3
"""Preserve the historical source/object closure separately; no builds or network actions."""
import argparse,hashlib,json,os,shlex,tarfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates a fresh independent supplement.');return
 home=Path.home();build=home/'.local/share/westlake/t18-production';argv=json.loads((build/'production-02/baseline-compile.argv.json').read_text());ws=Path(next(x.split('=',1)[1] for x in argv if x.startswith('--sysroot='))).parents[3]
 peer=ROOT.parent/'westlake-harness-outer-v2-review';mainrepo=ROOT.parent/'westlake-harness';snaprel='sources/api-implementations/bridge-d4fa-source-snapshot';snapshot=peer/snaprel/'snapshot.json';snapbytes=snapshot.read_bytes();snap=json.loads(snapbytes)
 private=HERE/'.private/archive-02';private.mkdir(parents=True,exist_ok=False);out=HERE/'packet-final';out.mkdir(exist_ok=False);selected={};roles={}
 def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
 def add(n,p,role):
  assert p.is_file(),n;assert not n.startswith('/') and '..' not in Path(n).parts,n
  if n in selected:assert selected[n].resolve()==p.resolve(),n
  selected[n]=p;roles.setdefault(n,set()).add(role)
 def addws(p,role):
  p=Path(os.path.normpath(p))
  assert p.is_relative_to(ws),str(p.name)
  add('ORB_WS/'+str(p.relative_to(ws)),p,role)
 def mapped(s):
  if s.startswith('$ORB_WS/'):return ws/s[8:]
  if s.startswith('/'):
   for marker in ['/source-closure/verify/','/a2hlab/ws/']:
    if marker in s:return ws/s.split(marker,1)[1]
   if Path(s).is_relative_to(ws):return Path(s)
   raise ValueError('unrecognized historical path for '+Path(s).name)
  return ws/s
 def tree(p,role):
  assert p.is_dir()
  for f in sorted(p.rglob('*')):
   if f.is_file():addws(f,role)
 artpath=ws/'out-touch21/fd/bridge15/artifacts.json';art=json.loads(artpath.read_text());source_rows=[]
 for kind in ['sources','headers']:
  for rel,pin in art[kind].items():
   dest='westlake-touch21/'+rel[len('westlake/'):] if rel.startswith('westlake/') else 'out-touch21/fd/bridge15/'+rel if rel.startswith('compat/') else rel
   p=ws/dest;assert sha(p)==pin,rel;addws(p,'touch21_'+kind);source_rows.append(dict(role=kind,recorded_path=rel,archive_path='ORB_WS/'+os.path.normpath(dest),sha256=pin,bytes=p.stat().st_size))
 assert len(art['sources'])==50 and len(art['headers'])==900
 tree(ws/'out-touch21/fd/bridge15/objects','touch21_objects');tree(ws/'out-touch21/fd/bridge15/compat','touch21_compat')
 for rel in ['out-touch21/fd/bridge15/artifacts.json','out-touch21/fd/bridge15/source-adapter_bridge.cpp','out-touch21/build-fd.sh','out-touch21/build-fd.log','out-touch21/fd/bridge15.log']:addws(ws/rel,'original_build_record')
 fdir=ws/'out-focus34/incremental';tree(fdir/'objects','focus34_objects_dependency_files_and_keys')
 for p in sorted(fdir.iterdir()):
  if p.is_file() and (p.suffix=='.log' or p.name in ['build.json','build-history.jsonl']):addws(p,'focus34_original_build_record')
 for p in sorted((fdir/'objects').glob('*.d')):
  deps=shlex.split(p.read_text().replace('\\\n',' '))[1:]
  for s in deps:addws(mapped(s),'focus34_actual_dependency')
 addws(ws/'westlake-focus34/native/input_transport_boundary.h','focus34_explicit_boundary_header')
 # Keep the authoritative original key report and exact matching object/key/dep triples.
 keys=[]
 for row in snap['focus34_object_dependency_keys']:
  p=fdir/'objects'/row['object_name'];assert sha(p)==row['object_sha256'];assert (p.parent/(p.name+'.key')).read_text().strip()==row['key_recorded']==row['key_recomputed'] and row['key_match']
  keys.append(dict(**row,dependency_file_sha256=sha(p.parent/(p.name+'.d')),key_file_sha256=sha(p.parent/(p.name+'.key')),verification='Original .key/object bytes match snapshot report; key recomputation was performed by evolution, not rerun as a build by this archive lane.'))
 assert len(keys)==9
 ability=[];links=[]
 for name in ['native-policy','native-stack']:
  d=ws/'out-ability38'/name;tree(d,'ability38_records_objects_logs')
  j=json.loads((d/'artifacts.json').read_text());objects=[]
  for old,pin in j['reused_objects'].items():
   p=mapped(old);assert sha(p)==pin;addws(p,'ability38_reused_object');objects.append(dict(path='ORB_WS/'+str(p.relative_to(ws)),sha256=pin))
  for c in j['commands']:
   cmd=c['command']
   if '-c' in cmd:
    p=mapped(cmd[cmd.index('-c')+1]);assert sha(p)==j['source_sha256'];addws(p,'ability38_exact_source')
   if c['label']=='link-bridge':
    destination=cmd[cmd.index('-o')+1]
    for s in cmd:
     if not s.startswith('/') or s==destination:continue
     p=mapped(s)
     if p.is_file():addws(p,'ability38_explicit_link_input');links.append(dict(stage=name,path='ORB_WS/'+str(p.relative_to(ws)),sha256=sha(p),bytes=p.stat().st_size))
  ability.append(dict(stage=name,reused_count=len(objects),objects=objects))
 for d in ['relink','repro','patched']:tree(ws/'out-mc46'/d,'mc46_existing_artifacts')
 for rel in ['westlake-mc46/framework/core/jni/oh_mediacodec_shim.cpp','westlake-mc46/framework/core/jni/oh_audiotrack_shim.cpp','westlake-mc46/LICENSE']:addws(ws/rel,'mc46_actual_source_or_license')
 for p in sorted((ws/'out-mc46').glob('*/*.d')):
  for s in shlex.split(p.read_text().replace('\\\n',' '))[1:]:addws(mapped(s),'mc46_recorded_dependency')
 p=ROOT.parent/'westlake-harness-triage46/benchmark/2026-09-26-toutiao-crash-triage/scripts/build_bridge_mc.py';add('TRIAGE46/benchmark/2026-09-26-toutiao-crash-triage/scripts/build_bridge_mc.py',p,'historical_recipe_original_bytes')
 pinfile=mainrepo/'benchmark/2026-10-20-d4fa-bridge-closure/input-pins.json';pins=json.loads(pinfile.read_text())
 for r in pins['files']:
  p=mapped(r['path']);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'];addws(p,'main_explicit_pin')
 add('review-inputs/d4fa-input-pins.json',pinfile,'original_index')
 snapshot_rows=[]
 for row in snap['files']:
  p=peer/row['path'];assert p.is_file() and sha(p)==row['sha256'] and p.stat().st_size==row['bytes'];canonical=p.resolve().relative_to(peer.resolve());add('source-snapshot/'+str(canonical),p,'small_source_license_recipe_snapshot');snapshot_rows.append(dict(path=str(canonical),sha256=row['sha256'],bytes=row['bytes']))
 assert len(snapshot_rows)==138 and snapshot.read_bytes()==snapbytes
 frozen_snapshot=private/'snapshot.original.json';frozen_snapshot.write_bytes(snapbytes);add('source-snapshot/'+snaprel+'/snapshot.json',frozen_snapshot,'snapshot_index_at_packaging')
 dump(out/'source-header-index.json',dict(sources=50,headers=900,files=source_rows))
 dump(out/'focus34-keys.json',dict(objects=keys,scope='9 final objects keyed; all 12 object/dep/key triples retained from directory without assigning final status to the other 3.'))
 dump(out/'ability38-inputs.json',dict(stages=ability,explicit_link_inputs=links))
 dump(out/'small-source-snapshot.json',dict(snapshot_path=snaprel+'/snapshot.json',snapshot_sha256=hashlib.sha256(snapbytes).hexdigest(),files=snapshot_rows,main_base_source_present=sum(bool(r['main_matches']) for r in snap['base_source_coverage']),main_base_missing=sum(not bool(r['main_matches']) for r in snap['base_source_coverage'])))
 counts={stage:sum(r['stage']==stage for r in links) for stage in ['native-policy','native-stack']}
 dump(out/'results.json',dict(token='t18-source-closure-supplement',status='LOCAL_PACKAGE_PREPARATION',first_archive_unchanged='c6d4f34f8af201d12bb8e53000fe58eec6043d5f6197e36bfe608691e943305b',base_sources=50,base_headers=900,final_focus34_objects=9,all_focus34_object_dep_key_triples=len(list((fdir/'objects').glob('*.key'))),small_source_snapshot_entries=138,ability38_reused_objects={r['stage']:r['reused_count'] for r in ability},ability38_explicit_file_arguments=counts,mc46_final_original_stdout_stderr_rc='UNKNOWN_NOT_FOUND',historical_logs_recreated=False,builds_run=0,device_calls=0,runtime_acceptance='NOT_CLAIMED'))
 add('archive-review/package.py',Path(__file__).resolve(),'packaging_source')
 for p in sorted(out.iterdir()):add('archive-review/'+p.name,p,'public_review')
 members=[dict(path=n,sha256=sha(p),bytes=p.stat().st_size,mode=oct(p.stat().st_mode&0o777),roles=sorted(roles[n])) for n,p in sorted(selected.items())];dump(private/'members.json',dict(files=members));add('archive/members.json',private/'members.json','archive_index')
 index={r['path']:r for r in members};index['archive/members.json']=dict(sha256=sha(private/'members.json'),bytes=(private/'members.json').stat().st_size)
 tarpath=private/'window.tar.gz'
 with tarfile.open(tarpath,'w:gz') as t:
  for n,p in sorted(selected.items()):t.add(p.resolve(),arcname=n,recursive=False)
 with tarfile.open(tarpath,'r:gz') as t:
  ms=t.getmembers();assert len(ms)==len(selected)
  for m in ms:assert m.isfile() and m.size==index[m.name]['bytes'] and hashlib.sha256(t.extractfile(m).read()).hexdigest()==index[m.name]['sha256']
 assert all(sha(p)==index[n]['sha256'] for n,p in selected.items()),'source changed during packaging'
 old=json.loads((home/'.local/share/westlake/toutiao-resume-20261019/video-r10-window-archive/receipt.json').read_text());rd=os.environ.get('HW248_ARTIFACT_ROOT',str(Path(old['remote']).parent.parent)).rstrip('/')+'/toutiao-t18-d4fa-source-closure-20261020'
 commands=[['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','test ! -e '+shlex.quote(rd)+' && mkdir -p '+shlex.quote(rd)],['scp','-o','BatchMode=yes','-o','ConnectTimeout=10',str(tarpath),'hw248:'+rd+'/window.tar.gz'],['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','sha256sum '+shlex.quote(rd+'/window.tar.gz')+' && stat -c %s '+shlex.quote(rd+'/window.tar.gz')]]
 dump(private/'remote-commands.private.json',commands)
 receipt=dict(token='t18-source-closure-supplement',status='LOCAL_VERIFIED_REMOTE_PENDING',archive_sha256=sha(tarpath),bytes=tarpath.stat().st_size,member_count=len(selected),members_index_sha256=sha(private/'members.json'),local_member_sha_verified=True,remote='HW248_ARTIFACT_ROOT/toutiao-t18-d4fa-source-closure-20261020/window.tar.gz',remote_verified=False,commands=[],first_archive_unchanged='c6d4f34f8af201d12bb8e53000fe58eec6043d5f6197e36bfe608691e943305b',mc46_original_final_logs='UNKNOWN_NOT_FOUND')
 dump(private/'receipt.json',receipt);dump(out/'archive-receipt.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
