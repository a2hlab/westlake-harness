#!/usr/bin/env python3
"""Package frozen existing T20 inputs and evidence; no build or device operations."""
import argparse,hashlib,json,os,shlex,subprocess,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
CANDIDATE='5cc23582d8cd8f28b24f89dc9bcf439de2177c0be33bb4783dd1baad3ab32eca'
PAIR='610053541b996e41377aae1270f42eed52610b60e17e5e948c2f297a78aa2155'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates fresh local archive. Upload is a separate recorded operation.');return
 home=Path.home();raw=home/'.local/share/westlake/t20-provider-link';owner=ROOT.parent/'westlake-harness-video-plan';rel=Path('benchmark/2026-10-20-t20-provider-link-slice');src=owner/rel;peerrepo=ROOT.parent/'westlake-harness-api-progress-peer';peerrel=Path('benchmark/2026-10-20-t20-pair-peer');peer=peerrepo/peerrel;mainrepo=ROOT.parent/'westlake-harness'
 prod=json.loads((raw/'production-04/receipt.json').read_text());result=json.loads((src/'results.json').read_text());assert result['candidate']==dict(sha256=CANDIDATE,bytes=70184) and result['source_pins']['shim/pair.c']==PAIR
 for n,d in result['source_pins'].items():assert sha(src/n)==d,n
 inp=json.loads((src/'input-pins.json').read_text());rawpins=json.loads((src/'private-raw-index.json').read_text());assert len(inp)==104 and len(rawpins)==635
 # The raw executed argv/receipt supplies actual roots, not guessed SDK or VM versions.
 inputsroot=next(Path(n).parents[2] for n in prod['inputs'] if n.endswith('/out-ability38/webview-gles-order/build.json'))
 sdk=next(Path(n).parents[2] for n in prod['inputs'] if n.endswith('/llvm/bin/clang-15'))
 roots={'$T20_RAW':raw,'$MAIN':mainrepo,'$WORKTREE':owner,'$INPUTS':inputsroot,'$SDK':sdk,'$HOME':home,'$PEER_RAW':home/'.local/share/westlake/t20-pair-peer'}
 def resolve(n):
  key,rest=n.split('/',1);assert key in roots,key;return roots[key]/rest
 def clean(s):
  for k,p in sorted(roots.items(),key=lambda x:-len(str(x[1]))):s=s.replace(str(p),k)
  return s.replace(str(peerrepo),'$WORKSPACES/westlake-harness-api-progress-peer')
 out=HERE/'.private/archive-03';out.mkdir(parents=True,exist_ok=False);pub=HERE/'packet';pub.mkdir(exist_ok=False);selected={};checks=[]
 def add(n,p,pin=None):
  assert not n.startswith('/') and '..' not in Path(n).parts
  actual=dict(sha256=sha(p),bytes=p.stat().st_size)
  if pin is not None:assert actual==pin,(n,actual,pin)
  assert n not in selected or selected[n]==p;selected[n]=p;return actual
 for n,pin in inp.items():checks.append(dict(path=n,**add('input-bundle/'+n[1:],resolve(n),pin)))
 for n,pin in rawpins.items():add('raw/'+n[1:],resolve(n),pin)
 extras=[]
 for p in sorted(raw.rglob('*')):
  if p.is_file() and '$T20_RAW/'+str(p.relative_to(raw)) not in rawpins:
   n='raw-extra/T20_RAW/'+str(p.relative_to(raw));extras.append(dict(path=n,**add(n,p)))
 sourcefiles=[]
 for n in subprocess.check_output(['git','-C',str(mainrepo),'ls-tree','-r','--name-only','4b17ff7861fa1c16b5874594db11e97d68ef73f9','--',str(rel)],text=True).splitlines():
  assert subprocess.check_output(['git','-C',str(mainrepo),'show','4b17ff7861fa1c16b5874594db11e97d68ef73f9:'+n])==(owner/n).read_bytes(),n
 for p in sorted(src.rglob('*')):
  if not p.is_file() or any(x in p.parts for x in ['.private','__pycache__']):continue
  n='source-snapshot/'+str(p.relative_to(owner));sourcefiles.append(dict(path=n,**add(n,p)))
 commit='6d37c756cb698708d86f7e9d7ecf3b9ec5a779ea';peerfiles=subprocess.check_output(['git','-C',str(peerrepo),'ls-tree','-r','--name-only',commit,'--',str(peerrel)],text=True).splitlines()
 for n in peerfiles:
  data=subprocess.check_output(['git','-C',str(peerrepo),'show',commit+':'+n]);snapshot=out/'peer-source'/n;snapshot.parent.mkdir(parents=True,exist_ok=True);snapshot.write_bytes(data);add('peer-source/'+n,snapshot)
 peer=out/'peer-source'/peerrel
 old_runner=subprocess.check_output(['git','-C',str(peerrepo),'show','1315b21a66:'+str(peerrel/'test_pair.py')]);assert old_runner==(peer/'replay_pair.py').read_bytes()
 pr=json.loads((peer/'results.json').read_text());assert pr['pins']['pair.c']==PAIR and pr['status']=='SCOPED_STATIC_AND_HOST_ACCEPT' and len(pr['cases'])==10 and all(v==0 for v in pr['cases'].values())
 pri=json.loads((peer/'private-raw-index.json').read_text());prroot=resolve(pri['root'])
 for n,pin in pri['files'].items():add('peer-raw/r3/'+n,prroot/n,pin)
 # Include old peer failures separately; do not erase the original -6 counterexample.
 for p in sorted(prroot.parent.rglob('*')):
  if p.is_file() and not p.is_relative_to(prroot):add('peer-raw/earlier/'+str(p.relative_to(prroot.parent)),p)
 commandchecks=[]
 for generation in ['production-03','production-04']:
  d=raw/generation;r=json.loads((d/'receipt.json').read_text());assert len(r['inputs'])==104 and len(r['commands'])==16
  for n,pin in r['inputs'].items():assert dict(sha256=sha(Path(n)),bytes=Path(n).stat().st_size)==pin,n
  for n,pin in r['artifacts'].items():assert dict(sha256=sha(d/n),bytes=(d/n).stat().st_size)==pin,n
  assert r['artifacts']['candidate.so']==result['candidate'] and r['artifacts']['baseline.so']==result['baseline']
  for c in r['commands']:
   prefix=d/'raw'/c['name'];files=[Path(str(prefix)+'.'+x) for x in ['argv.json','stdout','stderr','rc']];assert all(f.is_file() for f in files);assert int(files[-1].read_text())==c['rc']==0
   commandchecks.append(dict(generation=generation,name=c['name'],rc=0,files=[dict(path=clean(str(p)),sha256=sha(p),bytes=p.stat().st_size) for p in files]))
 assert (raw/'production-03/candidate.so').read_bytes()==(raw/'production-04/candidate.so').read_bytes()
 dump(pub/'input-bundle-index.json',checks);dump(pub/'extra-raw-index.json',extras);dump(pub/'source-snapshot-index.json',sourcefiles);dump(pub/'successful-commands.json',commandchecks)
 for name,p in [('author-results.json',src/'results.json'),('peer-results.json',peer/'results.json')]:
  (pub/name).write_text(clean(p.read_text()))
 verification=dict(token='t20-production-archive-ready',status='FROZEN_INPUTS_LOCAL_VERIFIED_NOT_DEVICE_ADMISSION',candidate=result['candidate'],baseline=result['baseline'],pair_sha256=PAIR,production03_04_identical=True,successful_build_command_groups=32,inputs_verified=104,frozen_raw_files_verified=len(rawpins),dispatch_raw_count=470,extra_raw_files=len(extras),peer_commit=commit,peer_runner_rename_bytes_equal=True,main_source_commit='4b17ff7861fa1c16b5874594db11e97d68ef73f9',peer_cases=pr['cases'],peer_status=pr['status'],original_logs_preserved=True,original85_historical_execution_logs='UNKNOWN_NOT_FOUND; new exact-baseline relink logs are not historical',whole_platform_source_rebuild=False,builds_by_lane=0,device_calls=0)
 dump(pub/'results.json',verification)
 add('review-source/package.py',Path(__file__))
 for p in sorted(pub.iterdir()):add('public-packet/'+p.name,p)
 members=[dict(path=n,sha256=sha(p),bytes=p.stat().st_size) for n,p in sorted(selected.items())];dump(out/'members.json',dict(files=members));add('archive/members.json',out/'members.json');index={r['path']:r for r in members};index['archive/members.json']=dict(sha256=sha(out/'members.json'),bytes=(out/'members.json').stat().st_size)
 tar=out/'production.tar.gz'
 with tarfile.open(tar,'w:gz') as t:
  for n,p in sorted(selected.items()):t.add(p.resolve(),arcname=n,recursive=False)
 with tarfile.open(tar,'r:gz') as t:
  ms=t.getmembers();assert len(ms)==len(selected) and {m.name for m in ms}==set(selected)
  for m in ms:assert m.isfile() and m.size==index[m.name]['bytes'] and hashlib.sha256(t.extractfile(m).read()).hexdigest()==index[m.name]['sha256']
 assert all(sha(p)==index[n]['sha256'] for n,p in selected.items()),'input changed while packaging'
 remote='toutiao-t20-paired-shim-production-20261020';old=json.loads((ROOT/'benchmark/2026-10-20-t18-full-log-supplement/.private/archive-01/remote-commands.private.json').read_text());rr=os.environ.get('HW248_ARTIFACT_ROOT',old[2][-1].split()[1].rsplit('/',2)[0]);assert rr.startswith('/');rd=rr.rstrip('/')+'/'+remote
 commands=[['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','test ! -e '+shlex.quote(rd)+' && mkdir -p '+shlex.quote(rd)],['scp','-o','BatchMode=yes','-o','ConnectTimeout=10',str(tar),'hw248:'+rd+'/production.tar.gz'],['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','sha256sum '+shlex.quote(rd+'/production.tar.gz')+' && stat -c %s '+shlex.quote(rd+'/production.tar.gz')]]
 dump(out/'remote-commands.private.json',commands)
 receipt=dict(token='t20-production-archive-ready',status='LOCAL_VERIFIED_REMOTE_PENDING',archive_sha256=sha(tar),bytes=tar.stat().st_size,member_count=len(selected),local_member_sha_verified=True,remote='HW248_ARTIFACT_ROOT/'+remote+'/production.tar.gz',remote_verified=False,commands=[],inputs=104,frozen_raw_files=len(rawpins),extra_raw_files=len(extras),members_index_sha256=sha(out/'members.json'))
 dump(out/'receipt.json',receipt);dump(pub/'archive-receipt.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
