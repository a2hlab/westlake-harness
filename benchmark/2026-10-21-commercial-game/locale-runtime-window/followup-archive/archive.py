from pathlib import Path
import datetime,hashlib,json,shlex,subprocess,tarfile
D=Path(__file__).resolve().parent
W=Path.cwd().parent
archive=D/'g34-followup-originals.tar.gz'
sources=[(W/'westlake-harness-g10-env/benchmark/2026-10-21-commercial-game/runtime-loader-triage/g34-open-site-followup/.private','open-site-originals'),(D.parent/'g34-postclose-faultdirs-04','faultdirs-04')]+[(D.parent/'outer-review/g34-admission-peer-01'/n,'outer-review/'+n) for n in ['open-site-01','diagnostic-readiness-01']]

def now():return datetime.datetime.now().astimezone().isoformat()
def run(name,argv):
 r={'argv':argv,'started_at':now()}
 with (D/(name+'.stdout')).open('wb') as o,(D/(name+'.stderr')).open('wb') as e:
  p=subprocess.run(argv,stdout=o,stderr=e)
 r.update(rc=p.returncode,finished_at=now());(D/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n')
 if p.returncode:raise SystemExit(name+' failed; originals retained')
 return (D/(name+'.stdout')).read_text()
assert not archive.exists()
with tarfile.open(archive,'w:gz') as tf:
 for path,name in sources:
  assert path.is_dir();tf.add(path,arcname=name)
h=hashlib.sha256(archive.read_bytes()).hexdigest();size=archive.stat().st_size
rel='westlake-artifacts/2026-10-22-g34-followup-'+h[:12]
run('mkdir',['ssh','hw248','mkdir -p -- '+shlex.quote(rel)])
run('upload',['scp',str(archive),'hw248:'+rel+'/'+archive.name])
remote=run('verify',['ssh','hw248','sha256sum -- '+shlex.quote(rel+'/'+archive.name)])
assert remote.split()[0]==h
receipt={'status':'remote_sha256_verified','archive_sha256':h,'bytes':size,'remote':'hw248:$HW248_HOME/'+rel+'/'+archive.name,'local_originals_preserved':True,'verified_at':now(),'contents':[name for _,name in sources], 'excludes':['earlier G34 execution and full-buffer archives','runtime rollout copies and APK','game success or crash-cause evidence'], 'result':'bounded static open-site originals, read-only fault directory listings and independent reviews; PC and stack not recovered'}
(D/'archive-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
