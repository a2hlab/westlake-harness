#!/usr/bin/env python3
"""Extract pinned boot/runtime definitions and the actual fallback DEX bodies."""
import json,sys,re,subprocess,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'2026-09-29-static-wall-prediction'))
from scan_classes_v3 import jar_classes
from scan_jni import sha,DEXDUMP
from rules_feedback_v2 import boot_visibility
BASE=Path('/Users/zhaoyue/orca/workspaces')
BOOT=BASE/'westlake-generation-v3c-candidate/payload/android/framework'
RUNTIME=BASE/'vm-copies/r17j-20dcb71b/oh-adapter-runtime.jar'

def main():
    inputs=[];bc=set();rc=set()
    package=BOOT.parents[2]/'package.json'
    manifest=json.loads(package.read_text())
    assert sha(package)=='668e4f7c74bfe635c57ca7133e1373acb0c675959d5953a20708e70293d27107'
    for jar in sorted(BOOT.glob('*.jar'))+[RUNTIME]:
        if jar.name=='oh-adapter-runtime.jar' and jar!=RUNTIME:continue
        rows=jar_classes(jar);names={r['class'] for r in rows}
        if jar!=RUNTIME:assert manifest['files'][str(jar.relative_to(BOOT.parents[2]))]==sha(jar)
        (rc if jar==RUNTIME else bc).update(names)
        inputs.append(dict(path=str(jar),sha256=sha(jar),definitions=len(names),loader='runtime' if jar==RUNTIME else 'boot-candidate'))
    assert sha(RUNTIME)=='20dcb71bf9a91b21b660174ad3730f4fa62fbb59ed9f662d7be7808611b3591f'
    captures=[]
    wanted=('sun/security/jca/Providers','sun/security/util/ManifestEntryVerifier','sun/security/util/ManifestEntryVerifier$SunProviderHolder','java/util/ServiceLoader','java/util/jar/JarVerifier','java/util/jar/JarFile')
    # Keep complete relevant classes; source-line references remain original dexdump lines.
    jar=BOOT/'core-oj.jar'
    with zipfile.ZipFile(jar) as z,tempfile.TemporaryDirectory() as td:
        for entry in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
            p=Path(td)/entry;p.write_bytes(z.read(entry));proc=subprocess.Popen([str(DEXDUMP),'-d',str(p)],stdout=subprocess.PIPE,text=True,errors='replace')
            selected=False
            for n,line in enumerate(proc.stdout,1):
                if 'Class descriptor' in line:selected=any("'L"+c+";'" in line for c in wanted)
                if selected:captures.append({'jar':str(jar),'dex':entry,'line':n,'text':line.rstrip()})
            if proc.wait():raise RuntimeError('dexdump failed')
    (HERE/'evidence/boot-provider-dex.json').write_text(json.dumps(captures,indent=2)+'\n')
    (HERE/'evidence/boot-provider-dex.txt').write_text('\n'.join(f'{x["dex"]}:{x["line"]}: {x["text"]}' for x in captures)+'\n')
    result={'profile':'v3c 668e4f7c + r17j 20dcb71b','package_manifest_sha256':sha(package),'inputs':inputs,'visibility':boot_visibility(bc,rc),
            'scope':'Definition union; exact boot membership checked against recorded fingerprint/BCP. Presence is not initialization success.',
            'fallback_body':any('com.android.org.conscrypt.OpenSSLProvider' in x['text'] for x in captures),
            'jar_verification_resources':[]}
    with zipfile.ZipFile(RUNTIME) as z:
        result['jar_verification_resources']=[{'entry':n,'bytes':z.getinfo(n).file_size} for n in z.namelist() if n.upper().startswith('META-INF/') and (n.upper().endswith(('.SF','.RSA','.DSA','MANIFEST.MF')) or '/services/' in n)]
    (HERE/'profile.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['visibility'],len(captures))
if __name__=='__main__':main()
