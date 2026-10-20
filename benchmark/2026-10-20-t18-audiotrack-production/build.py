#!/usr/bin/env python3
"""Replay the original bridge chain, preserving evidence; no device capability."""
import argparse, hashlib, importlib.util, json, os, shlex, struct, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
T18=HERE.parent/'2026-10-20-t18-audiotrack-size'
BASE='d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b'
OLD_AUDIO='bca071e610061c4eaa38ee7b81c6316997853851d533037b2be105da1350e5e3'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def command(argv,out,name):
    write(out/(name+'.argv.json'),argv)
    with (out/(name+'.stdout')).open('wb') as o,(out/(name+'.stderr')).open('wb') as e:
        try: rc=subprocess.run(argv,stdout=o,stderr=e,timeout=90,env=dict(os.environ,LC_ALL='C',TZ='UTC')).returncode
        except subprocess.TimeoutExpired:rc=124
    (out/(name+'.rc')).write_text(str(rc)+'\n')
    if rc:raise RuntimeError(name+': '+('TIMEOUT' if rc==124 else str(rc)))
def sections(data):
    if data[:6]!=b'\x7fELF\x02\x01':raise ValueError('requires ELF64 little endian')
    off=struct.unpack_from('<Q',data,40)[0]; n=struct.unpack_from('<H',data,60)[0]; idx=struct.unpack_from('<H',data,62)[0]
    hdr=[struct.unpack_from('<IIQQQQIIQQ',data,off+i*64) for i in range(n)]
    names=data[hdr[idx][4]:hdr[idx][4]+hdr[idx][5]]
    return [(names[s[0]:].split(b'\0')[0].decode(),s,data[s[4]:s[4]+s[5]]) for s in hdr]
def compare_owner(old,new):
    a=old.read_bytes();b=new.read_bytes();sa=sections(a);sb=sections(b)
    if len(sa)!=len(sb):raise ValueError('owner section count changed')
    changes=[];allowed=[]
    for (name,ha,ba),(name2,hb,bb) in zip(sa,sb):
        if name!=name2 or ha!=hb:raise ValueError('unmodified owner section header drift')
        if ba!=bb:
            if name!='.comment' or ha[2]&2:raise ValueError('unmodified owner code/data drift: '+name)
            changes.append(name);allowed+=list(range(ha[4],ha[4]+ha[5]))
    changed=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    if len(a)!=len(b) or not set(changed)<=set(allowed):raise ValueError('owner bytes outside permitted non-ALLOC comment differ')
    return {'old_sha256':sha(old),'new_sha256':sha(new),'changed_sections':changes,'changed_bytes':len(changed),'all_other_bytes_equal':True}
def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--sdk',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    inputs=a.inputs.resolve();sdk=a.sdk.resolve();out=a.out.absolute()
    def expand(s):return s.replace('$INPUTS',str(inputs)).replace('$SDK',str(sdk)).replace('$OUT',str(out))
    pins=json.loads((HERE/'input-pins.json').read_text());recipe=json.loads((HERE/'recipe.json').read_text())
    for name,rec in pins.items():
        f=Path(expand(name))
        if not f.is_file() or f.stat().st_size!=rec['bytes'] or sha(f)!=rec['sha256']:raise ValueError('input pin mismatch: '+name)
    if not a.execute:print(json.dumps({'status':'PREVIEW','input_count':len(pins),'device_calls':0}));return
    out.mkdir(parents=True,exist_ok=False)
    result={'status':'BUILD_INCOMPLETE_NOT_DEPLOYABLE','input_count':len(pins),'device_calls':0}
    try:
        command(['python3',str(REPO/'scripts/lab/check_frozen.py'),'--git',str(REPO)],out,'frozen')
        write(out/'input-pins.json',pins);write(out/'recipe.json',recipe)
        cc=[expand(s) for s in recipe['compile']];link=[expand(s) for s in recipe['link']]
        old_audio=Path(next(s for s in link if s.endswith('westlake_framework_core_jni_oh_audiotrack_shim.cpp.o')))
        if sha(old_audio)!=OLD_AUDIO:raise ValueError('wrong original AudioTrack object')
        link[link.index('-o')+1]=str(out/'baseline.so');command(link,out,'baseline-link')
        if sha(out/'baseline.so')!=BASE:raise ValueError('baseline bridge not exact d4fa')
        # -MD changes dependency recording only; includes system headers unlike original -MMD.
        cc[cc.index('-MMD')]='-MD'
        cc[cc.index('-o')+1]=str(out/'baseline-audio.o');cc[cc.index('-MF')+1]=str(out/'baseline-audio.d');command(cc,out,'baseline-compile')
        result['baseline_owner']=compare_owner(old_audio,out/'baseline-audio.o')
        write(out/'baseline-owner-diff.json',result['baseline_owner'])
        original=Path(cc[cc.index('-c')+1]);profile=T18/'source-profile/oh_audiotrack_shim.cpp'
        if original.read_bytes()!=profile.read_bytes():raise ValueError('original producing source differs from reviewed profile')
        module_spec=importlib.util.spec_from_file_location('t18_derive',T18/'derive.py');m=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(m)
        generated=m.derive();(out/'oh_audiotrack_shim.cpp').write_bytes(generated);(out/'audiotrack_effective_size.inc').write_bytes((T18/'audiotrack_effective_size.inc').read_bytes())
        cc[cc.index('-c')+1]=str(out/'oh_audiotrack_shim.cpp');cc[cc.index('-o')+1]=str(out/'candidate-audio.o');cc[cc.index('-MF')+1]=str(out/'candidate-audio.d');command(cc,out,'candidate-compile')
        idx=link.index(str(old_audio));link[idx]=str(out/'candidate-audio.o');link[link.index('-o')+1]=str(out/'candidate.so');command(link,out,'candidate-link')
        readelf=sdk/'llvm/bin/llvm-readelf'
        for stage in ['baseline','candidate']:
            command([str(readelf),'-h','-d','--dyn-syms','--wide',str(out/(stage+'.so'))],out,stage+'-elf')
        deps={}
        for name in ['baseline-audio.d','candidate-audio.d']:
            data=(out/name).read_text().replace('\\\n',' ')
            for s in shlex.split(data.split(': ',1)[1]):deps[s]={'sha256':sha(s),'bytes':Path(s).stat().st_size}
        write(out/'all-includes.json',deps)
        # Post-check every pre-pinned original input; retained maps show the one new object.
        for name,rec in pins.items():
            if sha(expand(name))!=rec['sha256']:raise ValueError('input changed during build: '+name)
        result.update(status='BUILT_PENDING_ABI_AND_INDEPENDENT_REVIEW',baseline_sha256=sha(out/'baseline.so'),candidate_sha256=sha(out/'candidate.so'),candidate_audio_sha256=sha(out/'candidate-audio.o'),include_count=len(deps),getter_sha256=sha(out/'audiotrack_effective_size.inc'))
    except Exception as ex:
        result['error']=str(ex);write(out/'result.json',result);raise
    write(out/'result.json',result);print(json.dumps(result))
if __name__=='__main__':main()
