from pathlib import Path
import datetime,hashlib,json,shlex,subprocess,tarfile
D=Path(__file__).resolve().parent
W=Path.cwd().parent
archive=D/'g34-dfx-provenance-originals.tar.gz'
table_path=Path.cwd()/'benchmark/2026-10-21-commercial-game/locale-runtime-window/dfx-provenance/match-table.json'
table=json.loads(table_path.read_text())
sources=[]
for row in table['rows']:
 item=row.get('local_copy',row.get('local_identical_bytes'))
 source=Path(item['path'].replace('$HOME',str(Path.home())))
 assert source.stat().st_size==item['bytes'] and hashlib.sha256(source.read_bytes()).hexdigest()==item['sha256']
 sources.append((source,'elf/'+item['sha256']+'/'+source.name))
sources += [(D.parent/'outer-review/g34-admission-peer-01/dfx-provenance-01','independent-review'),(table_path,'match-table.json')]

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
  assert path.exists();tf.add(path,arcname=name)
h=hashlib.sha256(archive.read_bytes()).hexdigest();size=archive.stat().st_size
rel='westlake-artifacts/2026-10-22-g34-dfx-provenance-'+h[:12]
run('mkdir',['ssh','hw248','mkdir -p -- '+shlex.quote(rel)])
run('upload',['scp',str(archive),'hw248:'+rel+'/'+archive.name])
remote=run('verify',['ssh','hw248','sha256sum -- '+shlex.quote(rel+'/'+archive.name)])
assert remote.split()[0]==h
receipt={'status':'remote_sha256_verified','archive_sha256':h,'bytes':size,'remote':'hw248:$HW248_HOME/'+rel+'/'+archive.name,'local_originals_preserved':True,'verified_at':now(),'contents':[name for _,name in sources], 'excludes':['APK','unproven source/build logs','fault-time mapped-inode evidence'], 'result':'Eight exact locally saved ELF copies and independent metadata/revision reviews; device binding and source/build gaps remain explicit'}
(D/'archive-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
