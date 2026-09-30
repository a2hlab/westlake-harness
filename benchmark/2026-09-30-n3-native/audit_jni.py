#!/usr/bin/env python3
import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
src=(P/'src/oh_egl_impl.cpp').read_text()
macros=dict(re.findall(r'^#define\s+(\w+)\s+"([^"]*)"',src,re.M))
entries=[]
for name,expr in re.findall(r'\{\s*"([^"]+)"\s*,(.*?),\s*\(void\*\)',src):
 tokens=re.findall(r'"[^"]*"|\w+',expr)
 entries.append((name,''.join(t[1:-1] if t.startswith('"') else macros[t] for t in tokens)))
d=json.loads((P/'evidence/egl-dex-methods.json').read_text());declared={(m['method'],m['signature']) for m in d['methods']}
jar=Path(d['jar']);assert hashlib.sha256(jar.read_bytes()).hexdigest()==d['jar_sha256']
assert len(entries)==28 and set(entries)==declared
registration='::register_com_google_android_gles_jni_EGLImpl(env)'
assert registration in (P/'src/AndroidRuntime.cpp').read_text()
assert registration not in (P/'../2026-09-30-n2-native/src/AndroidRuntime.cpp').read_text()
bad={(n,'()J' if n=='_eglGetDisplay' else sig) for n,sig in entries}
assert bad != declared and set(entries[1:])!=declared
(P/'egl-signatures.json').write_text(json.dumps({'source_sha256':hashlib.sha256(src.encode()).hexdigest(),'jar':str(jar),'jar_sha256':d['jar_sha256'],'count':len(entries),'entries':entries,'missing':[],'negative_wrong_signature_or_missing_entry':'rejected','negative_n2_registration':'rejected'},indent=2)+'\n')
print('PASS 28 EGLImpl natives, exact DEX signatures, old registration/mutated signature negatives')
