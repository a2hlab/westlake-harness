from pathlib import Path
import subprocess,shlex,json,os
out=Path(__file__).resolve().parent/'board-consumer-scan';out.mkdir(exist_ok=True)
hdc=os.environ['B6_HDC']  # Run in VM with the shared hdc_mac.sh path
serial='5ea34a4500000000000000001123012c'
prefix=[hdc,'-t',serial]
def read(cmd):
 r=subprocess.run(prefix+['shell',cmd],capture_output=True,text=True,timeout=180);assert r.returncode==0,(r.returncode,r.stderr);return r.stdout
symbols=['_ZN3art11ClassLinker11ResolveTypeENS_3dex9TypeIndexEPNS_9ArtMethodE','_ZN3art11ClassLinker20DumpBootObjectFieldsEPKc','_ZN3art6mirror8DexCache15GetResolvedTypeENS_3dex9TypeIndexE','_ZZN3art6mirror8DexCache15GetResolvedTypeENS_3dex9TypeIndexEE22logged_primclass_guard']
roots='/system/android/lib64 /system/lib64'
files=read('find '+roots+' -type f');(out/'all-files.txt').write_text(files)
control=read("if strings /system/android/lib64/libart.so | grep -F DumpBootObjectFields >/dev/null; then echo CONTROL_HIT; else echo CONTROL_MISS; fi")
assert 'CONTROL_HIT' in control,control
(out/'positive-control.txt').write_text(control)
pattern='|'.join(symbols+['libart[.]so'])
cmd='find -L '+roots+' -type f | while IFS= read -r f; do if strings "$f" | grep -E '+shlex.quote(pattern)+' >/dev/null; then echo "$f"; fi; done'
hits=read(cmd);(out/'symbol-or-libart-string-hits.txt').write_text(hits)
libart=''
for remote in sorted(set(hits.splitlines())):
 assert remote.startswith('/system/') and not any(c.isspace() for c in remote),remote
 d=out/'files'/remote.removeprefix('/');d.parent.mkdir(parents=True,exist_ok=True)
 r=subprocess.run(prefix+['file','recv',remote,str(d)],capture_output=True,text=True,timeout=180)
 assert r.returncode==0 and d.is_file(),(remote,r.stdout,r.stderr)
print(json.dumps({'files':len(files.splitlines()),'symbol_hits':hits.splitlines(),'scope':'positive-controlled strings scan; consumer UND analysis follows on host'}))
