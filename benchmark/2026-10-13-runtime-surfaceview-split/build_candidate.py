"""One fresh cold container build; original tool/recipe inputs retained; zero board access."""
import hashlib,importlib.util,json,os,shlex,subprocess,tarfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2]))).resolve()
IMAGE='sha256:12ffb9324ca4df6427cbf6a6da0ac8ce575599291e933724275fce704520db63'
CLANG='b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913'
SOURCE='c208788a90ee19ad891af5cbe6fb8d7b29f339467ece084255d168dab45d1aef'
PREPARE='5631a7f543d59edf1ea8e859731c726ae0b97f029be022e304a098162d8ea459'
INPUT_ARCHIVE='ba5906c6903dccc35dc07ecd6bbbeea9742fd4d366ab9cb64bd48fa7551c9c88'
INPUT_INVENTORY='68924eaf25b164ed19faa5412325a0d0487026cfa7401fa62642203e549d400e'
BASE='18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def pin(p):
    p=Path(p).resolve();return {'path':'$WORKSPACES/'+str(p.relative_to(WS)) if p.is_relative_to(WS) else str(p),'sha256':sha(p),'bytes':p.stat().st_size}
def load(p,name):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def require(ok,why):
    if not ok:raise ValueError(why)
def run():
    attempt=HERE/'.artifacts'/('cold-'+str(time.time_ns()));attempt.mkdir(parents=True)
    receipt={'schema':'runtime-surfaceview-cold-build/v1','status':'BUILDING','device_calls':0,'execution_enabled':False,'started_epoch':time.time(),'steps':[]}
    def step(argv,name,env=None):
        start=time.time();r=subprocess.run([str(x) for x in argv],capture_output=True,env=env)
        out=attempt/(name+'.stdout.txt');err=attempt/(name+'.stderr.txt');out.write_bytes(r.stdout);err.write_bytes(r.stderr)
        receipt['steps'].append({'argv':[str(x) for x in argv],'rc':r.returncode,'started_epoch':start,'finished_epoch':time.time(),'stdout':pin(out),'stderr':pin(err)})
        require(r.returncode==0,name+' rc='+str(r.returncode)+' '+r.stderr.decode(errors='replace')[-1800:]);return r.stdout
    source=HERE/'source/android_graphics_compat_shim.cpp'
    root=WS/'westlake-inputs/generations/t2c-runtime-reproduction-20261010';inventory=root/'input-inventory.json';archive=root/'runtime187-inputs.tar.gz'
    def closure():
        require(sha(inventory)==INPUT_INVENTORY,'original source inventory SHA drift');rows=json.loads(inventory.read_text())['files'];bad=[]
        for r in rows:
            p=Path(r['path'].replace('$WORKSPACES',str(WS)))
            if not p.is_file() or sha(p)!=r['sha256']:bad.append(r['path'])
        require(not bad,'source closure drift: '+repr(bad[:15]));return {'files':len(rows),'inventory':pin(inventory),'all_match':True}
    try:
        require(sha(source)==SOURCE,'candidate TU drift')
        receipt['source']=pin(source);receipt['source_patch']=pin(HERE/'source-over-947.patch')
        require(sha(archive)==INPUT_ARCHIVE,'original complete source archive drift');receipt['original_source_archive']=pin(archive)
        receipt['closure_before']=closure()
        require(step(['docker','image','inspect','a2hlab-build:24.04','--format','{{.Id}}'],'image').decode().strip()==IMAGE,'container identity drift');receipt['container_image']=IMAGE
        prep=WS/'westlake-harness/benchmark/2026-10-10-adapter-buildchain/prepare_runtime_cold.py';require(sha(prep)==PREPARE,'cold prepare identity drift');receipt['prepare']=pin(prep)
        cold=attempt/'cold';load(prep,'original_cold_prepare').prepare(WS,cold)
        recipe=cold/'recipe.sh';text=recipe.read_text();original=str(WS/'westlake-harness-t3/benchmark/2026-10-02-m1-session-slots/runtime/src/android_graphics_compat_shim.cpp');require(text.count(original)==1,'geometry TU anchor count')
        recipe.write_text(text.replace(original,str(source)))
        receipt['strict_link_flags']=['-Wl,-z,defs','-Wl,--no-allow-shlib-undefined','-Wl,--no-undefined']
        for flag in receipt['strict_link_flags']:require(flag in recipe.read_text(),'missing strict link flag '+flag)
        compiler=WS/'westlake-harness-bms-deploy/bms/src/.work/b68-generation/.work/product-tls-generation/frozen/toolchain/bin/clang-15';require(sha(compiler)==CLANG,'clang identity drift');receipt['clang']=pin(compiler)
        receipt['scripts']={p.name:pin(p) for p in sorted(cold.glob('*.sh'))};receipt['preparation']=pin(cold/'preparation.json')
        env=os.environ.copy();env.update(WORKSPACES=str(WS),DOCKBUILD_IMAGE=IMAGE,DOCKBUILD_MOUNTS=':'.join(str(WS/n) for n in ['westlake-harness-bms-deploy','westlake-harness-t3','westlake-harness-t0']))
        log=attempt/'build.log';argv=[str(WS/'westlake-inputs/tools/dockbuild.sh'),'run','--','bash',str(cold/'run.sh')]
        command='set -o pipefail; '+shlex.join(argv)+' 2>&1 | tee '+shlex.quote(str(log));step(['/bin/bash','-c',command],'container-build',env)
        receipt['build_log']=pin(log);candidate=cold/'runtime-out/liboh_android_runtime.so';baseline=root/'r1/runtime-out/liboh_android_runtime.so';require(sha(baseline)==BASE,'baseline ELF drift');receipt['candidate']=pin(candidate);receipt['baseline']=pin(baseline)
        gate_path=WS/'westlake-harness-bms/benchmark/2026-10-10-boat-runtime-port-spec/build_link_gate.py';receipt['ABI_tool']=pin(gate_path);gate=load(gate_path,'original_runtime_abi_gate');receipt['ABI']=gate.verify(candidate,baseline)
        require(receipt['ABI']['exports_before']==receipt['ABI']['exports_after']==787 and not receipt['ABI']['added'],'exact787 ABI required')
        before,after=gate.symbols(baseline),gate.symbols(candidate);drift=[]
        for name,row in before.items():
            if row['index'] and row['bind'] in (1,2) and any(row[k]!=after[name][k] for k in ['bind','type','visibility']):drift.append(name)
        require(not drift,'export binding/type/visibility drift');receipt['ABI']['attribute_drift']=drift
        receipt['closure_after']=closure();require(sha(source)==SOURCE,'compiled source drifted during build')
        layer=attempt/'candidate-source-recipe.tar.gz'
        with tarfile.open(layer,'w:gz') as tar:
            for f in [source,HERE/'source-over-947.patch',HERE/'build_candidate.py',*sorted(cold.glob('*.sh')),cold/'preparation.json']:
                tar.add(f,arcname=str(f.relative_to(HERE)),recursive=False)
        receipt['candidate_source_recipe_archive']=pin(layer)
        receipt['status']='BUILT_ABI_PASS_NOT_RUNTIME_OR_UI_ACCEPTED';return receipt
    except Exception as e:
        receipt['status']='BUILD_FAILED';receipt['error']=str(e);raise
    finally:
        receipt['finished_epoch']=time.time();(attempt/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');(HERE/'evidence/build-location.json').write_text(json.dumps(pin(attempt/'receipt.json'),indent=2)+'\n');print('BUILD_RECEIPT='+str(attempt/'receipt.json')+' STATUS='+receipt['status'],flush=True)
if __name__=='__main__':run()
