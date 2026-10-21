#!/usr/bin/env python3
"""Offline exact-APK inventory. References and exports are not runtime binding."""
import argparse, hashlib, json, re, subprocess, time, zipfile
from pathlib import Path

EXPECTED='abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc'
HERE=Path(__file__).resolve().parent
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def run(out,tag,argv):
    p=out/tag;p.parent.mkdir(parents=True,exist_ok=True)
    put(p.with_suffix('.argv.json'),argv);p.with_suffix('.start').write_text(str(time.time()))
    with p.with_suffix('.stdout').open('wb') as o,p.with_suffix('.stderr').open('wb') as e:
        rc=subprocess.run(argv,stdout=o,stderr=e).returncode
    p.with_suffix('.rc').write_text(str(rc));p.with_suffix('.end').write_text(str(time.time()))
    if rc:raise RuntimeError((tag,rc))
    return p.with_suffix('.stdout')
def escape(s):
    return ''.join('_' if c in '/.' else '_1' if c=='_' else '_2' if c==';' else '_3' if c=='[' else c if c.isascii() and c.isalnum() else ''.join('_0'+c.encode('utf-16-be')[i:i+2].hex() for i in range(0,len(c.encode('utf-16-be')),2)) for c in s)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--apk',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    assert a.apk.stat().st_size==513290344 and sha(a.apk)==EXPECTED,'exact input mismatch'
    a.out.mkdir(parents=True,exist_ok=True)
    sdk=Path.home()/'Library/Android/sdk'
    readelf=sorted((sdk/'ndk').glob('*/toolchains/llvm/prebuilt/*/bin/llvm-readelf'))[-1]
    dexdump=sdk/'build-tools/37.0.0/dexdump'
    put(a.out/'tools.json',[{'path':str(p),'sha256':sha(p)} for p in [readelf,dexdump]])
    libs=[];dexes=[];decl=[];calls=[];classes=[];exportmap={}
    with zipfile.ZipFile(a.apk) as z:
        members=z.infolist();put(a.out/'zip-members.json',[{'name':i.filename,'bytes':i.file_size,'crc':i.CRC} for i in members])
        for i in members:
            n=i.filename
            if not (n.startswith('lib/') and n.endswith('.so') or re.fullmatch(r'classes\d*\.dex',n)):continue
            p=a.out/'members'/n;p.parent.mkdir(parents=True,exist_ok=True)
            with z.open(i) as r,p.open('wb') as w:
                for b in iter(lambda:r.read(1048576),b''):w.write(b)
            if n.endswith('.so'):
                raw=run(a.out/'raw',p.stem,[str(readelf),'-h','-d','--dyn-syms','--wide',str(p)])
                txt=raw.read_text();imports=[];exports=[]
                for line in txt.splitlines():
                    m=re.match(r'\s*\d+:\s+[0-9a-f]+\s+\d+\s+\S+\s+\S+\s+\S+\s+(\S+)\s+(\S+)',line)
                    if m:
                        ndx,sym=m.groups()
                        (imports if ndx=='UND' else exports).append(sym)
                for s in exports:exportmap.setdefault(s.split('@')[0],[]).append(n)
                needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',txt)
                row={'member':n,'bytes':i.file_size,'sha256':sha(p),'needed':needed,'imports':imports,'jni_exports':[s for s in exports if s.startswith('Java_') or s=='JNI_OnLoad'],'elf_class':re.search(r'Class:\s+(\S+)',txt)[1],'machine':re.search(r'Machine:\s+(.+)',txt)[1],'raw':'raw/'+raw.name}
                row['llvm_warnings']=raw.with_suffix('.stderr').read_text(errors='replace') != ''
                row['graphics_audio_imports']=[s for s in imports if re.match(r'(egl|gl[A-Z]|vk|ANativeWindow|AImage|AHardwareBuffer|AAudio|SL_IID|slCreate|OpenSL)',s)]
                libs.append(row);print('ELF',n,len(imports),flush=True)
            else:
                raw=run(a.out/'raw',p.stem,[str(dexdump),'-d',str(p)])
                dexes.append({'member':n,'sha256':sha(p),'bytes':i.file_size,'raw':'raw/'+raw.name})
                cls=name=sig=method='';recent=[]
                with raw.open(errors='replace') as f:
                    for lineno,line in enumerate(f,1):
                        m=re.search(r"Class descriptor\s+: 'L(.+);'",line)
                        if m:cls=m[1];classes.append({'dex':n,'class':cls})
                        m=re.search(r"name\s+: '([^']+)'",line)
                        if m:name=m[1]
                        m=re.search(r"type\s+: '(\([^']+)'",line)
                        if m:sig=m[1]
                        if re.search(r'access\s+:.*\bNATIVE\b',line):decl.append({'dex':n,'class':cls,'method':name,'signature':sig,'line':lineno})
                        m=re.search(r'\|\[[0-9a-f]+\] (.+)',line)
                        if m:method=m[1];recent=[]
                        if re.search(r'\|[0-9a-f]+:',line):
                            recent.append(line.strip());recent=recent[-9:]
                            if 'invoke-' in line and re.search(r'(Ljava/lang/(System|Runtime);\.(load|loadLibrary)|Landroid/(media/(AudioTrack|AudioRecord)|view/(Surface|SurfaceView|TextureView)|opengl/)|Lcom/unity3d/player/)',line):
                                calls.append({'dex':n,'caller':method,'line':lineno,'instruction':line.strip(),'preceding_instructions':recent[:-1] if re.search(r'\.(load|loadLibrary):',line) else []})
                print('DEX',n,flush=True)
    for d in decl:
        base='Java_'+escape(d['class'])+'_'+escape(d['method'])
        long=base+'__'+escape(d['signature'][1:d['signature'].index(')')])
        d['short_export_candidates']=exportmap.get(base,[]);d['long_export_candidates']=exportmap.get(long,[])
        d['binding_status']='EXPORTED_NAME_CANDIDATE_NOT_RUNTIME' if d['short_export_candidates'] or d['long_export_candidates'] else 'NO_EXPORTED_NAME_MATCH_DYNAMIC_REGISTRATION_UNKNOWN'
    put(HERE/'elf-inventory.json',{'apk_sha256':EXPECTED,'libraries':libs})
    put(HERE/'dex-inventory.json',{'apk_sha256':EXPECTED,'dexes':dexes,'class_count':len(classes),'native_declarations':decl,'calls':calls})
    put(a.out/'classes.json',classes)
    print('DONE',len(libs),len(dexes),len(decl),len(calls),flush=True)
if __name__=='__main__':main()
