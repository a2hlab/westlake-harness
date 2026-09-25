from boardclosure48 import *

SHIM='85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a'
CORE='c9969638b0175b7077332e1b7a65f4354392def62b5f6e1049ca763b9677148e'
OLD_CORE='14fe6c92f6f034b109e5ada98a79be25df9d36efedf1024fc393fa592c67e0ee'
EXPECTED={
 'libandroid.so':CORE,
 'libart.so':'ae2cb1829ffa9eca08e1a0fe816edfc33bbe0e1ca3e2f43aaa99e522924a8937',
 'webview-t-lib/libwebview_bionic_shim.so':SHIM,
 'liboh_adapter_bridge.so':'d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b',
 'lib/arm64-v8a/libnpth.so':'8b8d559c50130a997b5fbf3383e8ebf6291ebe54ab2b5ed5fbc8e1ac73fe36af',
 'lib/arm64-v8a/libmetasec_ml.so':'c91fc2ee0f47c87da4723fd59eb8420ed616b409076310f28f3420771a1fab6b',
 'run.sh':'17781b81e25db11125883474d932a63743dd56f59ebba3e53eb39c80582b0548',
}

def verify_components(runtime,output):
 actual={path:dev('sha256sum '+runtime+'/'+path).split()[0] for path in EXPECTED}
 output.write_text(json.dumps({'expected':EXPECTED,'actual':actual},indent=2)+'\n')
 assert actual==EXPECTED,'candidate drift: see '+str(output)

def deploy_core(runtime,r):
 artifact=pathlib.Path.home()/'a2hlab/ws/out-operator-closure48/libandroid.so'
 assert sha(artifact)==CORE
 target=runtime+'/libandroid.so'
 previous=dev('sha256sum '+target).split()[0]
 assert previous in (OLD_CORE,CORE),previous
 backup='/data/local/tmp/operator45-crashes/closure48-original'
 before=dev('ls -lZ '+target)
 label=re.search(r'u:object_r:[^\s]+',before)
 assert label,before
 if previous!=CORE:
  dev('mkdir -p '+backup+'; cp -p '+target+' '+backup+'/libandroid.'+previous+'.so')
  assert dev('sha256sum '+backup+'/libandroid.'+previous+'.so').split()[0]==previous
  send(artifact,target+'.c48')
  dev('chmod 644 '+target+'.c48; chcon '+label[0]+' '+target+'.c48; mv '+target+'.c48 '+target)
 assert dev('sha256sum '+target).split()[0]==CORE
 after=dev('ls -lZ '+target)
 assert label[0] in after,after
 (r/'core-libandroid-deployment.json').write_text(json.dumps({'source':str(artifact),'source_commit':'1d4af70b754cea71f3936095995f4034836cb9f9','before_sha256':previous,'after_sha256':CORE,'backup':backup,'before_stat':before,'after_stat':after},indent=2)+'\n')
