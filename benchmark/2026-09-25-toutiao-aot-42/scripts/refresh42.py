"""Recollect completed-trial stderr and late fault reports; never touch live processes."""
from board42 import *
for r in sorted(R.iterdir()):
 if not (r/'result.json').exists():continue
 d=json.loads((r/'device-report.json').read_text());pid=d['child']
 # PID may have been reused: no mutation; archived log filename is unique within owned runtime.
 log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr'
 recv(log,r/'child.stderr')
 digest=dev('sha256sum '+log).split()[0]
 assert digest==hashlib.sha256((r/'child.stderr').read_bytes()).hexdigest()
 (r/'stderr-sha256.txt').write_text(digest+'\n')
 paths=dev(f'find /data/log/faultlog -type f -name "*-{pid}-*"')
 (r/'late-fault-paths.txt').write_text(paths)
 for path in paths.splitlines():
  if path.startswith('/'):recv(path,r/pathlib.Path(path).name)
 print(r.name,flush=True)
