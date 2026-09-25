from board25 import *
import tarfile,hashlib
m=json.loads((R/'reuse-seed.json').read_text());p=R/'reuse-seed.tar'
assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256']
with tarfile.open(p) as t:
 archived={f.name:hashlib.sha256(t.extractfile(f).read()).hexdigest() for f in t if f.isfile()}
raw=dev('cd '+m['runtime']+" && find app-data data webview-t-data -type f -exec sha256sum '{}' ';'",180)
board={l.split(None,1)[1]:l.split()[0] for l in raw.splitlines() if re.match(r'^[0-9a-f]{64} ',l)}
assert archived==board,(archived.keys()-board.keys(),board.keys()-archived.keys())
m['regular_files_verified']=len(board);m['regular_file_sha256']=board;m['excluded']='Unix-domain socket entries (tar cannot archive sockets); recreated by apps'
(R/'reuse-seed.json').write_text(json.dumps(m,indent=2));print('Verified',len(board),'seed regular files')
