#!/usr/bin/env python3
"""Archive one completed T16 window with both recovery attempts; no device access."""
import argparse,hashlib,json,os,shlex,subprocess,tarfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
REMOTE='toutiao-t16-5cd-r8-20261020'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--close',required=True);ap.add_argument('--upload',action='store_true');ap.add_argument('--remote-root',default=os.environ.get('HW248_ARTIFACT_ROOT'));args=ap.parse_args()
 close=Path(args.close).expanduser().resolve();closed=json.loads(close.read_text());assert closed['unlocked'] is True and closed['elapsed_seconds']<1800 and (close.parent/'unlock.rc').read_text().strip()=='0'
 assert (close.parent/'unlocked-readback.rc').read_text().strip()=='1' and not (close.parent/'unlocked-readback.stdout').read_bytes().strip()
 out=Path(args.out).resolve();assert not str(out).startswith(('/tmp/','/private/tmp/'));out.mkdir(parents=True,exist_ok=False)
 bases={f'BASE{day}':Path.home()/f'.local/share/westlake/toutiao-resume-202610{day}' for day in [19,20]};base=bases['BASE20']
 selected={};allow=json.loads((HERE/'final/raw-archive-allowlist.json').read_text())
 for name in allow['directories']:
  directory=base/name;assert directory.is_dir()
  for p in sorted(directory.rglob('*')):
   if p.is_file():selected['BASE20/'+str(p.relative_to(base))]=p
 for name in allow['files']:
  p=base/name;assert p.is_file();selected['BASE20/'+name]=p
 for name in ['build_final.py','prepare_archive.py','finalize_packet.py']:
  selected['review-source/'+name]=HERE/name
 for d,prefix in [(HERE/'candidate-checkpoint-01','candidate-checkpoint-01'),(HERE/'.private/producer-snapshots','producer-snapshots')]:
  for p in sorted(d.rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:selected[prefix+'/'+str(p.relative_to(d))]=p
 selected['review-source/raw-archive-allowlist.json']=HERE/'final/raw-archive-allowlist.json'
 members=[{'path':n,'bytes':p.stat().st_size,'sha256':sha(p)} for n,p in sorted(selected.items())]
 (out/'members.json').write_text(json.dumps({'files':members},indent=2)+'\n')
 selected['archive/members.json']=out/'members.json'
 indexed={r['path']:r for r in members};indexed['archive/members.json']={'sha256':sha(out/'members.json'),'bytes':(out/'members.json').stat().st_size}
 tarpath=out/'window.tar.gz'
 with tarfile.open(tarpath,'w:gz') as t:
  for n,p in sorted(selected.items()):t.add(p.resolve(),arcname=n,recursive=False)
 with tarfile.open(tarpath,'r:gz') as t:
  ms=t.getmembers();assert len(ms)==len(selected) and {m.name for m in ms}==set(selected)
  for m in ms:
   assert m.isfile();assert m.size==indexed[m.name]['bytes'];assert hashlib.sha256(t.extractfile(m).read()).hexdigest()==indexed[m.name]['sha256']
 assert all(sha(p)==indexed[n]['sha256'] for n,p in selected.items()),'input changed while archiving'
 receipt={'token':'t16-window-evidence','archive_sha256':sha(tarpath),'bytes':tarpath.stat().st_size,'member_count':len(selected),'local_member_sha_verified':True,'remote':'HW248_ARTIFACT_ROOT/'+REMOTE+'/window.tar.gz','remote_verified':False,'commands':[],'scope':'raw evidence; no playback or observer success'}
 remote_root=args.remote_root
 if not remote_root:
  old=json.loads((bases['BASE19']/'video-r10-window-archive/receipt.json').read_text());remote_root=str(Path(old['remote']).parent.parent)
 assert remote_root.startswith('/')
 rd=remote_root.rstrip('/')+'/'+REMOTE
 commands=[['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','test ! -e '+shlex.quote(rd)+' && mkdir -p '+shlex.quote(rd)],['scp','-o','BatchMode=yes','-o','ConnectTimeout=10',str(tarpath),'hw248:'+rd+'/window.tar.gz'],['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','sha256sum '+shlex.quote(rd+'/window.tar.gz')+' && stat -c %s '+shlex.quote(rd+'/window.tar.gz')]]
 (out/'remote-commands.private.json').write_text(json.dumps(commands,indent=2)+'\n')
 def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 save()
 if args.upload:
  for i,cmd in enumerate(commands):
   stem=f'remote-{i}';(out/(stem+'.command.json')).write_text(json.dumps(cmd,indent=2)+'\n');start=time.time()
   with (out/(stem+'.stdout')).open('wb') as so,(out/(stem+'.stderr')).open('wb') as se:
    try:rc=subprocess.run(cmd,stdout=so,stderr=se,timeout=180).returncode
    except subprocess.TimeoutExpired:rc=124
    except OSError as e:se.write(str(e).encode());rc=127
   (out/(stem+'.rc')).write_text(str(rc)+'\n')
   receipt['commands'].append({'name':stem,'rc':rc,'seconds':time.time()-start,'files':[{'name':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.glob(stem+'.*'))]});save()
   if rc:receipt['upload_status']='STOPPED_AT_FIRST_ERROR';save();print(json.dumps(receipt));return 2
  lines=(out/'remote-2.stdout').read_text().splitlines();assert len(lines)==2 and lines[0].split()[0]==receipt['archive_sha256'] and int(lines[1])==receipt['bytes'];receipt['remote_verified']=True;receipt['upload_status']='VERIFIED';save()
 print(json.dumps(receipt));return 0
if __name__=='__main__':raise SystemExit(main())
