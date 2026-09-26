import gzip, hashlib, json, pathlib, subprocess, sys
root=pathlib.Path(__file__).resolve().parent
manifest=json.loads((root/'evidence/manifest.json').read_text())
repo=pathlib.Path(subprocess.check_output(['git','-C',str(root),'rev-parse','--show-toplevel'],text=True).strip())
for entry in manifest:
    p=root/'evidence'/entry['path']; data=p.read_bytes()
    assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256'],p
    raw=gzip.decompress(data) if entry['gzip'] else data
    assert len(raw)==entry['raw_bytes'] and hashlib.sha256(raw).hexdigest()==entry['raw_sha256'],p
    if '--git' in sys.argv:
        assert subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+str(p.relative_to(repo))])==data,p
print('PASS',len(manifest),'evidence files; raw hashes'+('; HEAD blobs' if '--git' in sys.argv else ''))
