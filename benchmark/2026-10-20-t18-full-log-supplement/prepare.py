#!/usr/bin/env python3
"""Package existing post-close read receipts only; never invoke a device or network."""
import argparse,hashlib,json,os,shlex,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
EXPECTED='eabb6fbe6836b388a22c18bf6386f0fe4d459b379e9972aded1111d48b558802'
REMOTE='toutiao-t18-postclose-full-log-20261020'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default; --write creates a fresh separate local archive and public packet.');return
 base=Path.home()/'.local/share/westlake/toutiao-resume-20261020';src=base/'t18-candidate-full-log-read'
 r=json.loads((src/'result.json').read_text());raw=src/'candidate-full.stderr'
 assert sha(raw)==r['sha256']==EXPECTED and raw.stat().st_size==r['bytes']==33438849
 assert r['readonly'] and r['source_boot']=='6b99680b-3d15-476a-a229-dc3591e34add' and r['read_boot']=='9e75bd0f-e7cd-4819-a8e1-00c6512d020b'
 for stem in ['before','receive','after']:assert (src/(stem+'.rc')).read_text().strip()=='0'
 for stem in ['before-held','after-held']:assert (src/(stem+'.rc')).read_text().strip()=='1' and not (src/(stem+'.stdout')).read_bytes().strip()
 assert (src/'before.stdout').read_bytes()==(src/'after.stdout').read_bytes()
 lines=(src/'after.stdout').read_text().splitlines();assert lines==['66352:188416:33438849',EXPECTED+'  '+r['source'],'READONLY_COMPLETE']
 for stem in ['before','after']:
  argv=json.loads((src/(stem+'.argv.json')).read_text());assert argv[1:4]==['-t','5cd1e3dd00000000000000000923012c','shell'] and r['read_boot'] in argv[-1] and 'sha256sum' in argv[-1]
 prior=ROOT/'benchmark/2026-10-20-t18-window-evidence'
 prior_manifest=(prior/'manifest.json').read_bytes();prior_pending=(prior/'archive/receipt.json').read_bytes()
 prior_tar=prior/'.private/archive-01/window.tar.gz';assert sha(prior_tar)=='3d27a564111b5898882c250354f2c9dc218cf0f35490cee13d6d9a0e04522d5e'
 out=HERE/'.private/archive-01';out.mkdir(parents=True,exist_ok=False);pub=HERE/'packet';pub.mkdir(exist_ok=False)
 def clean(s):return s.replace(str(base),'BASE20').replace(str(Path.home()),'$HOME')
 refs=[]
 for p in sorted(src.iterdir()):
  if not p.is_file():continue
  item=dict(path='BASE20/t18-candidate-full-log-read/'+p.name,sha256=sha(p),bytes=p.stat().st_size)
  if p!=raw:
   q=pub/(p.name+'.txt' if p.suffix in ['.stdout','.stderr'] else p.name);q.write_text(clean(p.read_text()));item.update(public_path=str(q.relative_to(ROOT)),public_sha256=sha(q),byte_exact=q.read_bytes()==p.read_bytes())
  refs.append(item)
 dump(pub/'source-index.json',refs)
 dump(pub/'verification.json',dict(status='POST_CLOSE_FIXED_LOG_READ_VERIFIED',input_sha256=EXPECTED,bytes=r['bytes'],read_boot=r['read_boot'],source_boot=r['source_boot'],before_after_stat_sha_equal=True,receive_rc=0,before_after_rc=[0,0],before_after_held_rc=[1,1],scope='Historical candidate file read after close; no playback or provider interpretation added',original_window_archive_unchanged=True,included_in_original_window_archive=False,device_calls_by_lane=0))
 selected={'BASE20/t18-candidate-full-log-read/'+p.name:p for p in sorted(src.iterdir()) if p.is_file()}
 selected['review-source/prepare.py']=Path(__file__)
 for p in sorted(pub.iterdir()):selected['public-packet/'+p.name]=p
 members=[dict(path=n,sha256=sha(p),bytes=p.stat().st_size) for n,p in sorted(selected.items())];dump(out/'members.json',dict(files=members));selected['archive/members.json']=out/'members.json'
 idx={m['path']:m for m in members};idx['archive/members.json']=dict(sha256=sha(out/'members.json'),bytes=(out/'members.json').stat().st_size)
 tar=out/'supplement.tar.gz'
 with tarfile.open(tar,'w:gz') as t:
  for n,p in sorted(selected.items()):t.add(p.resolve(),arcname=n,recursive=False)
 with tarfile.open(tar,'r:gz') as t:
  ms=t.getmembers();assert len(ms)==len(selected) and {m.name for m in ms}==set(selected)
  for m in ms:assert m.isfile() and m.size==idx[m.name]['bytes'] and hashlib.sha256(t.extractfile(m).read()).hexdigest()==idx[m.name]['sha256']
 assert all(sha(p)==idx[n]['sha256'] for n,p in selected.items()),'source drift during archive'
 assert (prior/'manifest.json').read_bytes()==prior_manifest and (prior/'archive/receipt.json').read_bytes()==prior_pending and sha(prior_tar)=='3d27a564111b5898882c250354f2c9dc218cf0f35490cee13d6d9a0e04522d5e'
 receipt=dict(token='t18-postclose-full-log-archive-ready',status='LOCAL_VERIFIED_REMOTE_PENDING',archive_sha256=sha(tar),bytes=tar.stat().st_size,member_count=len(selected),local_member_sha_verified=True,remote='HW248_ARTIFACT_ROOT/'+REMOTE+'/supplement.tar.gz',remote_verified=False,commands=[],original_window_archive='3d27a564111b5898882c250354f2c9dc218cf0f35490cee13d6d9a0e04522d5e',raw_log_sha256=EXPECTED,raw_log_bytes=r['bytes'])
 dump(out/'receipt.json',receipt);dump(pub/'archive-receipt.json',receipt)
 remote_root=os.environ.get('HW248_ARTIFACT_ROOT')
 if not remote_root:
  old=json.loads((prior/'.private/archive-01/remote-commands.private.json').read_text());remote_root=old[2][-1].split()[1].rsplit('/',2)[0]
 assert remote_root.startswith('/');rd=remote_root.rstrip('/')+'/'+REMOTE
 commands=[['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','test ! -e '+shlex.quote(rd)+' && mkdir -p '+shlex.quote(rd)],['scp','-o','BatchMode=yes','-o','ConnectTimeout=10',str(tar),'hw248:'+rd+'/supplement.tar.gz'],['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','sha256sum '+shlex.quote(rd+'/supplement.tar.gz')+' && stat -c %s '+shlex.quote(rd+'/supplement.tar.gz')]]
 dump(out/'remote-commands.private.json',commands)
 dump(pub/'members-index-reference.json',dict(path='$WORKSPACES/westlake-harness-t4/'+str((out/'members.json').relative_to(ROOT)),sha256=sha(out/'members.json'),bytes=(out/'members.json').stat().st_size))
 print(json.dumps(receipt))
if __name__=='__main__':main()
