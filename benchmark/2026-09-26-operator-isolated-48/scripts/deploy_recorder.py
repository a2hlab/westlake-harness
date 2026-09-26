from boardrefined48 import *
from deploymentrefined48 import EXPECTED
assert not dev('pidof '+PKG).strip(),'stop app first'
c=json.loads((R.parent/'refined48/config.json').read_text());rt=c['runtime']
out=R/'deployment';out.mkdir(exist_ok=True)
oldart='ae2cb1829ffa9eca08e1a0fe816edfc33bbe0e1ca3e2f43aaa99e522924a8937';oldrun='17781b81e25db11125883474d932a63743dd56f59ebba3e53eb39c80582b0548'
for name,digest in [('libart.so',oldart),('run.sh',oldrun)]:
 assert dev('sha256sum '+rt+'/'+name).split()[0]==digest
 recv(rt+'/'+name,out/('original-'+name))
 assert sha(out/('original-'+name))==digest
 backup='/data/local/tmp/operator45-crashes/isolated48-original'
 dev('mkdir -p '+backup+'; cp -p '+rt+'/'+name+' '+backup+'/'+name+'.'+digest)
 assert dev('sha256sum '+backup+'/'+name+'.'+digest).split()[0]==digest
run=(out/'original-run.sh').read_text();line='export WESTLAKE_OH_JIT_FILE_CACHE_DIR=/data/data/com.ss.android.article.news/code_cache/art-volatile'
assert run.count(line)==1
run=run.replace(line,'unset WESTLAKE_OH_JIT_FILE_CACHE_DIR\nexport WESTLAKE_CRASH42_DIR=/data/local/tmp/asx/private-tmp/crash42')
(out/'run.sh').write_text(run)
art=pathlib.Path.home()/'a2hlab/ws/out-isolated48-recorder/libart.so'
assert sha(art)=='cdd3e268ce3fd8d449a9a767fb0ad7012d01ca1c60e2f72188736899b09fda94'
for name,p in [('libart.so',art),('run.sh',out/'run.sh')]:
 before=dev('ls -lZ '+rt+'/'+name);label=re.search(r'u:object_r:[^\s]+',before)[0]
 send(p,rt+'/'+name+'.iso48');dev('chmod '+('755' if name=='run.sh' else '644')+' '+rt+'/'+name+'.iso48; chcon '+label+' '+rt+'/'+name+'.iso48; mv '+rt+'/'+name+'.iso48 '+rt+'/'+name)
 assert dev('sha256sum '+rt+'/'+name).split()[0]==sha(p)
dev('mkdir -p '+rt+'/private-tmp/crash42; chown 20010053:20010053 '+rt+'/private-tmp/crash42; chmod 700 '+rt+'/private-tmp/crash42; chcon u:object_r:appdat:s0 '+rt+'/private-tmp/crash42')
r=dict(original_art=oldart,recorder_art=sha(art),original_run=oldrun,isolated_run=sha(out/'run.sh'),jit_file_cache=False,recorder_dir='/data/local/tmp/asx/private-tmp/crash42')
(out/'deployment.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
(out/'relink.json').write_bytes((art.parent/'relink.json').read_bytes())
