from boardrefined48 import *

SHIM='85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a'
CORE='c9969638b0175b7077332e1b7a65f4354392def62b5f6e1049ca763b9677148e'
REAL='c91fc2ee0f47c87da4723fd59eb8420ed616b409076310f28f3420771a1fab6b'
OLD_STUB='6e6b9aaad14c6b8e5762c062a3689f96e4c74b8b84b32665cb42b2b9a661a9a9'
STUB='1021a0582e360ceafb49aa1162ee5d024104a73504ba0801927aaaa8bf2e706f'
EXPECTED={
 'libandroid.so':CORE,
 'libart.so':'ae2cb1829ffa9eca08e1a0fe816edfc33bbe0e1ca3e2f43aaa99e522924a8937',
 'webview-t-lib/libwebview_bionic_shim.so':SHIM,
 'liboh_adapter_bridge.so':'d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b',
 'lib/arm64-v8a/libnpth.so':'8b8d559c50130a997b5fbf3383e8ebf6291ebe54ab2b5ed5fbc8e1ac73fe36af',
 'lib/arm64-v8a/libmetasec_ml.so':STUB,
 'run.sh':'17781b81e25db11125883474d932a63743dd56f59ebba3e53eb39c80582b0548',
}

def verify_components(runtime,output):
 actual={path:dev('sha256sum '+runtime+'/'+path).split()[0] for path in EXPECTED}
 output.write_text(json.dumps({'expected':EXPECTED,'actual':actual},indent=2)+'\n')
 assert actual==EXPECTED,'candidate drift: see '+str(output)

def deploy_stub(runtime,r):
 artifact=pathlib.Path.home()/'a2hlab/ws/out-operator-refined48/libmetasec_ml.so'
 assert sha(artifact)==STUB
 target=runtime+'/lib/arm64-v8a/libmetasec_ml.so'
 previous=dev('sha256sum '+target).split()[0]
 assert previous in (REAL,OLD_STUB,STUB),previous
 backup='/data/local/tmp/operator45-crashes/refined48-original'
 before=dev('ls -lZ '+target)
 label=re.search(r'u:object_r:[^\s]+',before)
 assert label,before
 if previous!=STUB:
  dev('mkdir -p '+backup+'; cp -p '+target+' '+backup+'/libmetasec_ml.'+previous+'.so')
  assert dev('sha256sum '+backup+'/libmetasec_ml.'+previous+'.so').split()[0]==previous
  send(artifact,target+'.c48')
  dev('chmod 644 '+target+'.c48; chcon '+label[0]+' '+target+'.c48; mv '+target+'.c48 '+target)
 assert dev('sha256sum '+target).split()[0]==STUB
 after=dev('ls -lZ '+target)
 assert label[0] in after,after
 (r/'metasec-stub-deployment.json').write_text(json.dumps({'source':str(artifact),'source_commit':'bfc09a1dcd8bae34d3274e68b8b7db8fa8167fed','before_sha256':previous,'after_sha256':STUB,'backup':backup,'before_stat':before,'after_stat':after},indent=2)+'\n')
