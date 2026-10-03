"""Record production readelf results without changing arguments, result or gate."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path

def install(root):
 original=subprocess.run
 root=Path(root);root.mkdir(parents=True,exist_ok=True)
 counter=[0]
 def captured(*args,**kwargs):
  argv=args[0] if args else kwargs.get('args',[])
  relevant=isinstance(argv,(list,tuple)) and argv and Path(str(argv[0])).name in ('llvm-readelf','readelf') and '-d' in argv
  if not relevant:return original(*args,**kwargs)
  counter[0]+=1;number=counter[0];start=time.monotonic()
  try:result=original(*args,**kwargs)
  except BaseException as error:
   (root/f'{number:04d}-exception.json').write_text(json.dumps({'argv':list(map(str,argv)),'exception':repr(error),'seconds':time.monotonic()-start},indent=2)+'\n');raise
  def data(value):return value if isinstance(value,bytes) else (value or '').encode()
  stdout=data(result.stdout);stderr=data(result.stderr)
  (root/f'{number:04d}-stdout.txt').write_bytes(stdout);(root/f'{number:04d}-stderr.txt').write_bytes(stderr)
  elf=Path(str(argv[-1]));tool=shutil.which(str(argv[0]));row={'argv':list(map(str,argv)),'returncode':result.returncode,'seconds':time.monotonic()-start,'stdout_bytes':len(stdout),'stderr_bytes':len(stderr),'stdout_sha256':hashlib.sha256(stdout).hexdigest(),'elf_bytes':elf.stat().st_size,'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest(),'tool':tool,'tool_sha256':hashlib.sha256(Path(tool).read_bytes()).hexdigest() if tool else None,'LC_ALL':kwargs.get('env',os.environ).get('LC_ALL'),'dynamic_header_present':b'Dynamic section at offset' in stdout or b'Dynamic section contains' in stdout}
  (root/f'{number:04d}.json').write_text(json.dumps(row,indent=2)+'\n');return result
 subprocess.run=captured
