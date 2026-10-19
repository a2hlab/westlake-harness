#!/usr/bin/env python3
"""Narrow r10 source and build-receipt validation. Never invokes build or device tools."""
import argparse, hashlib, json, os, re, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'AGENTS.md').is_file())
B = Path('benchmark/2026-10-19-toutiao-video-playback')
OLD = '3becb0f688e9dba9f5626a8453756848dd51e2f5347c4688672de0fbe3384e8e'
NEW = '419aa6ea6c41792c3d886ab312855c3c677dbe92430dadfe2c253fd851de990e'
PINS = {
 'candidate-r8/ttplayer_log_mirror.c': OLD,
 'candidate/src/opensles_android_compat.c': 'cf45ad430a08cbe090f030357a346be7a0bac49f48c06196a11c7818de3f9351',
 'static/selected-change/link_only_stub.c':'fa47585b8fb702e8da05c52d732c9c964b5ec50a34edfa6815dea7f962898e13',
 'candidate-r8/deploy-inputs/libttmplayer.so':'0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471',
 'candidate-r3/deploy-inputs/libmffmpeg.so':'d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4',
 'candidate-r9/run.sh':'b5625757fcd812a64106a43897525b685216c7f61af5e9312969998c9485ee8a',
}
INPUTS = {
 'src/opensles_android_compat.c':PINS['candidate/src/opensles_android_compat.c'],
 'src/ttplayer_log_mirror.c':NEW,
 'src/link_only_stub.c':PINS['static/selected-change/link_only_stub.c'],
 'inputs/original-compat.so':'9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f',
 'inputs/liblog.so':'d8ad176b41b820a4868b74394188429ad2dc69025661d320d0986dd713048ca4',
 'inputs/original-toolchain-manifest.json':'ec28a440500411b265789399b609b728e0f4ef29ba386a570edac3d9556e5138',
}
STAGES = ['00-frozen','01-inputs','01a-reused','02-recipe-tools','03-image','04-tools','05-liblog-abi','10-anchor','20-link','21-strip','30-old-abi','31-new-abi','32-relocations','33-abi-compare','34-inputs-after','40-output-sha']

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(ok, reason):
    if not ok: raise ValueError(reason)

def source(root):
    checked=[]
    for name, expected in PINS.items():
        p=root/B/name
        require(p.is_file() and sha(p)==expected, 'source/input drift: '+name)
        checked.append({'path':str(B/name),'sha256':expected})
    old=(root/B/'candidate-r8/ttplayer_log_mirror.c').read_bytes()
    actual=(HERE/'ttplayer_log_mirror.c').read_bytes()
    require(actual==old.replace(b'MIRROR_ATTEMPTS = 256',b'MIRROR_ATTEMPTS = 4096') and sha(HERE/'ttplayer_log_mirror.c')==NEW,'not exact single-constant successor')
    recipe=(HERE/'build_candidate.sh').read_text()
    for token in [NEW,'$(dirname "$SELF")/ttplayer_log_mirror.c','--unwindlib=none','--why-extract','-l:liblog.so','check_frozen.py','01a-reused']:
        require(token in recipe,'missing recipe invariant: '+token)
    return {'status':'SOURCE_PASS_NOT_BUILT','inputs':checked,'new_source_sha256':NEW,'recipe_sha256':sha(HERE/'build_candidate.sh'),'runtime_binding':'UNKNOWN','playback':'NOT_PASSED'}

def files_receipt(out):
    receipt=json.loads((out/'build-receipt.json').read_text())
    require(receipt['status']=='BUILT_OFFLINE_NOT_ADMITTED','not completed offline build')
    rows=receipt['files']; require(isinstance(rows,list) and rows,'empty inventory')
    seen=set()
    for row in rows:
        n=row['path']; r=Path(n)
        require(not r.is_absolute() and '..' not in r.parts and n not in seen,'unsafe/duplicate file')
        p=out/r; require(p.resolve().is_relative_to(out.resolve()) and p.is_file(),'missing/escaped file: '+n)
        require(p.stat().st_size==row['size'] and sha(p)==row['sha256'],'file drift: '+n);seen.add(n)
    needed=set(INPUTS)|{'recipe.sh','artifacts/libopensles_android_compat.so','abi-comparison.json'}
    for stage in STAGES:
        needed.update('raw/'+stage+'.'+suffix for suffix in ['command','stdout','stderr','rc'])
    require(needed<=seen,'missing required raw/input files: '+str(sorted(needed-seen)))
    for stage in STAGES:
        require((out/('raw/'+stage+'.rc')).read_text().strip()=='0','nonzero execution: '+stage)
    return receipt

def elf_abi(path):
    text=path.read_text();require('AArch64' in text and 'ELF64' in text,'wrong ELF ABI')
    needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',text); sy={}
    for line in text.splitlines():
        f=line.split()
        if len(f)==8 and f[0].rstrip(':').isdigit():sy[f[7]]={'size':int(f[2]),'type':f[3],'bind':f[4],'vis':f[5],'ndx':f[6]}
    return text,needed,sy

def pinned_file(path, expected, label):
    require(path.is_file() and sha(path)==expected, 'build input drift: '+label)

def accept(out,root):
    source(root);files_receipt(out)
    for n,h in INPUTS.items(): pinned_file(out/n,h,n)
    require(sha(out/'recipe.sh')==sha(HERE/'build_candidate.sh'),'recipe drift')
    tools=(out/'raw/04-tools.stdout').read_text()
    for tool in ['clang-15','lld','llvm-strip','llvm-readelf','libc.so']:
        require(re.search(re.escape(tool)+r': OK',tools) is not None,'missing successful tool identity: '+tool)
    require('libdl.a' in tools,'missing actual libdl.a identity')
    require((out/'raw/03-image.stdout').read_text().strip()=='sha256:12ffb9324ca4df6427cbf6a6da0ac8ce575599291e933724275fce704520db63','image drift')
    _,on,osym=elf_abi(out/'raw/30-old-abi.stdout');_,nn,ns=elf_abi(out/'raw/31-new-abi.stdout')
    exports=lambda sy:{n:s for n,s in sy.items() if s['ndx']!='UND' and s['bind'] in ('GLOBAL','WEAK')}
    oe,ne=exports(osym),exports(ns);unique='__wl_ttlog_00000659'
    require(set(ne)==set(oe)|{unique},'unexpected exported ABI')
    for n in oe:
        for k in ['type','bind','vis']:
            require(oe[n][k]==ne[n][k],'old export changed: '+n)
        if oe[n]['type']=='OBJECT':require(oe[n]['size']==ne[n]['size'],'old OBJECT size')
    require(sorted(nn)==sorted(on+['liblog.so']),'dependencies drift')
    require(ns[unique]['type']=='FUNC' and ns[unique]['bind']=='GLOBAL','unique function missing')
    require(ns['__android_log_vprint']['ndx']=='UND' and '__android_log_print' not in ns,'backend dependency drift')
    rows=[x for x in (out/'raw/32-relocations.stdout').read_text().splitlines() if '__android_log_vprint' in x]
    require(len(rows)==1 and 'R_AARCH64_JUMP_SLOT' in rows[0],'vprint relocation drift')
    return {'status':'OFFLINE_BUILD_RECEIPT_VALID_HUMAN_REVIEW_PENDING','compat_sha256':sha(out/'artifacts/libopensles_android_compat.so'),'runtime_provider':'UNKNOWN','playback':'NOT_PASSED'}

def selftest():
    rejected=[]
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)
        for case in ['missing-receipt','empty-inventory','missing-raw','drifted-file','nonzero-rc']:
            if (p/'build-receipt.json').exists():(p/'build-receipt.json').unlink()
            if case!='missing-receipt':
                names=set(INPUTS)|{'recipe.sh','artifacts/libopensles_android_compat.so','abi-comparison.json'}
                for s in STAGES:names.update('raw/'+s+'.'+x for x in ['command','stdout','stderr','rc'])
                rows=[]
                for n in names:
                    f=p/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('0\n' if n.endswith('.rc') else 'SYNTHETIC_NEGATIVE_TEST\n')
                    rows.append({'path':n,'size':f.stat().st_size,'sha256':sha(f)})
                if case=='empty-inventory':rows=[]
                if case=='missing-raw':rows=[r for r in rows if r['path']!='raw/20-link.stderr']
                if case=='nonzero-rc':
                    f=p/'raw/20-link.rc';f.write_text('1\n')
                    for row in rows:
                        if row['path']=='raw/20-link.rc':row.update(size=f.stat().st_size,sha256=sha(f))
                (p/'build-receipt.json').write_text(json.dumps({'status':'BUILT_OFFLINE_NOT_ADMITTED','files':rows}))
                if case=='drifted-file':(p/'src/ttplayer_log_mirror.c').write_text('foreign')
            try:files_receipt(p)
            except (ValueError,FileNotFoundError):rejected.append(case)
            else:raise AssertionError('accepted '+case)
    with tempfile.TemporaryDirectory() as td:
        f=Path(td)/'foreign-input';f.write_text('SYNTHETIC_UPDATED_INVENTORY_BUT_FOREIGN_BYTES')
        for n in ['src/ttplayer_log_mirror.c','inputs/original-toolchain-manifest.json']:
            try:pinned_file(f,INPUTS[n],n)
            except ValueError:rejected.append('explicit-pin-drift:'+n)
            else:raise AssertionError('accepted foreign pinned input')
    return {'status':'NEGATIVE_RECEIPT_CHECKS_PASS','cases':rejected,'synthetic_tests_only':True,'production_build':'NOT_BUILT'}

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['source','receipt-tests','accept-build']);p.add_argument('--inputs-root',type=Path,default=Path(os.environ.get('R10_INPUTS_ROOT',ROOT)));p.add_argument('--build',type=Path);a=p.parse_args()
    if a.mode=='source':r=source(a.inputs_root)
    elif a.mode=='receipt-tests':r=selftest()
    else:
        require(a.build is not None,'--build required');r=accept(a.build,a.inputs_root)
    print(json.dumps(r,indent=2))
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,FileNotFoundError) as e:raise SystemExit('R10_REFUSE: '+str(e))
