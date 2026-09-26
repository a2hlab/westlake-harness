"""VM-only: retain A1 ART; replace sigchain and append audited crash42 object."""
import pathlib,json,hashlib,subprocess
w=pathlib.Path.home()/'a2hlab/ws';o=w/'out-isolated48-recorder';o.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
base='ae2cb1829ffa9eca08e1a0fe816edfc33bbe0e1ca3e2f43aaa99e522924a8937'
assert sha(w/'out-operator48/libart.so')==base
cmd=json.loads((w/'out-operator48/commands.json').read_text())[-1]
assert str(w/'out-operator48/libart.so') in cmd
report=json.loads((w/'out/art/runtime/artifacts.json').read_text())
objs=[p for p in cmd if p.endswith('.o')];assert len(objs)==454
for p in objs:
 if '/out-operator48/' in p:assert sha(p)=='d170bf7d7d99a8d0fdaef88b7293a7b8f87682e57883c725b465a619d1bfe60f'
 else:assert sha(p)==report['objects'][str(pathlib.Path(p).relative_to(w/'out/art/objects'))],p
reproduced=o/'baseline-relinked.so';cmd[cmd.index('-o')+1]=str(reproduced)
subprocess.run(cmd,check=True);assert sha(reproduced)==base
sig=w/'out-crash42/recorder/art/sigchain.o';rec=w/'out-crash42/recorder/crash_snapshot.o'
cmd[cmd.index(str(w/'out/art/objects/sigchain/sigchain.o'))]=str(sig)
cmd.insert(cmd.index('-Wl,--no-as-needed'),str(rec));cmd[cmd.index('-o')+1]=str(o/'libart.so')
subprocess.run(cmd,check=True)
r=dict(baseline_sha256=base,reproduced_sha256=sha(reproduced),candidate_sha256=sha(o/'libart.so'),sigchain_sha256=sha(sig),recorder_sha256=sha(rec),objects_checked=454,command=cmd)
(o/'relink.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='command'},indent=2))
