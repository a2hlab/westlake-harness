#!/usr/bin/env python3
"""Read-only evidence identity review; no REA/build/device execution."""
from pathlib import Path
import hashlib,json,subprocess
O=Path(__file__).resolve().parent;R=next(x for x in O.parents if (x/'scripts/lab/run_facts.py').is_file());V=R.parent/'westlake-harness-video';D=Path('benchmark/2026-10-19-toutiao-video-playback/static/evidence/r4-nextstate');C=Path.home()/'.claude/projects'/('-Users-'+Path.home().name+'-orca-workspaces-westlake-harness-video')/'7f25f2f3-9c80-48b3-9d33-751b56041b1e/tool-results'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
base='ce7484fad8c19fea02020c6980462f9c0b83f253';tip='0437f9880e4901b4301c984d6c8ad6bab64f05a7'
paths=subprocess.check_output(['git','-C',str(V),'diff','--name-only',base+'...'+tip],text=True).splitlines()
inputs=[];checks=[]
for path in paths:
 p=V/path;blob=subprocess.check_output(['git','-C',str(V),'show',tip+':'+path]);assert blob==p.read_bytes(),path
 inputs.append({'path':path,'sha256':h(p),'commit':tip})
 if p.name.startswith('raw.') and p.name.endswith('.rea.json'):
  d=json.loads(blob);eid=d['evidence_id'];matches=[]
  for source in C.glob('mcp-rea-*.txt'):
   text=source.read_text()
   if eid not in text:continue
   try:raw=json.loads(text)
   except ValueError:continue
   if isinstance(raw,dict) and raw.get('evidence_id')==eid:
    normalized=json.loads(text.replace(str(Path.home()),'$HOME'));assert normalized==d
    matches.append({'cache_filename':source.name,'original_sha256':h(source),'bytes':source.stat().st_size})
  assert len(matches)==1,(p.name,len(matches));assert d['subject']['digest']['sha256']=='a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395'
  checks.append({'public_file':path,'public_sha256':h(p),'evidence_id':eid,'original':matches[0],'only_home_sanitization_structural_equal':True})
write('source-pins.json',{'base':base,'tip':tip,'files':inputs,'private_cache_locator':'$HOME/.claude/projects/<video-worktree-encoded-key>/7f25f2f3-9c80-48b3-9d33-751b56041b1e/tool-results','raw_checks':checks,'scope':'Java files are decompiled/annotated extracts of the pinned commercial APK, not upstream authored source or new implementation.'})
a=json.loads((V/D/'rea-raw/raw.trace.DataLoaderHelper.proxyUrl.ov2.rea.json').read_text())
b=json.loads((V/D/'rea-raw/raw.trace.TTVideoEngine.proxyUrl.ov0.rea.json').read_text())
x=a['normalized_result'];y=b['normalized_result'];caller=x['references'][0]['direct_invokes'][0]['source_raw_method_id'];assert caller.split('proxyUrl',1)[1]!=y['dex_descriptor'];assert x['total']==1 and y['total']==0
write('overload-evidence.json',{'caller_trace_evidence_id':a['evidence_id'],'caller_raw_method_id':caller,'caller_dex_invoke':x['references'][0]['direct_invokes'][0],'zero_trace_evidence_id':b['evidence_id'],'zero_trace_descriptor':y['dex_descriptor'],'zero_trace_count':y['total'],'descriptors_equal':False,'conclusion':'Zero using-nodes belongs only to the five-argument method; it does not close the incoming chain of the six-argument method. Reflection/JNI/hotfix remain outside this static result.'})
apk=R.parent/'westlake-harness-rea-seal/.octos/rea-inputs/toutiao.apk';actual=Path.home()/'.local/share/westlake/toutiao-video-r2-gate-inputs/apk-lib/libttmplayer.so';wrong=R.parent.parent/'.local/share/westlake/toutiao-video-r2-gate-inputs/apk-lib/libttmplayer.so'
assert h(apk)=='a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395';assert h(actual)=='b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02';assert not wrong.exists()
write('checks.json',{'raw_originals_matched':len(checks),'tracked_changed_files_exact_tip':len(inputs),'apk_exact':True,'player_exact':True,'checkpoint_player_path_exists':False,'actual_player_path':'$HOME/.local/share/westlake/toutiao-video-r2-gate-inputs/apk-lib/libttmplayer.so','overload_mismatch_confirmed':True,'device_calls':0,'builds':0,'new_rea_calls':0,'old_tests_rerun':0})
print(json.dumps(json.loads((O/'checks.json').read_text()),indent=2))
