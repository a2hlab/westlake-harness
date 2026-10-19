#!/usr/bin/env python3
"""Pinned, device-free reuse of the original executor block checker.
Only subprocesses are Python executing the fail-closed UNAPPROVED entry/checker.
Never changes production EXECUTION_REVIEW or imports Board.
"""
import argparse, ast, difflib, hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path
P = 'benchmark/2026-10-19-toutiao-video-playback/'
B = 'benchmark/2026-10-19-toutiao-rea-methods/video-r4-executor-draft/successor-r6/'
PINS = {
 P+'candidate-r8/deployment/video_guarded_window_r8.py':'a325e2faf79e950443c0b8d19c03e46bf5a04e4953d247195e08a7f6621e81c0',
 P+'candidate-r8/deployment/read_binding.py':'bf25e9d01d949d5e6d7d0b2654c8cc5d266d6b33c11cecbd19a0186f59d87509',
 B+'video_guarded_window_r6.py':'b8e9c4b2296bebf91f2364e272f6047cfc494e7f70e719688b73fd0ae695a531',
 B+'check_offline.py':'02a0915da7fff1bd13df7e981ea18057bb1559f2b432e6144186a09eacb0cbe5',
}
sha=lambda data:hashlib.sha256(data).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--main',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 m=a.main.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 for rel,digest in PINS.items():assert sha((m/rel).read_bytes())==digest,rel
 source=(m/(P+'candidate-r8/deployment/video_guarded_window_r8.py')).read_text()
 base=(m/(B+'video_guarded_window_r6.py')).read_text()
 (out/'executor.diff').write_text(''.join(difflib.unified_diff(base.splitlines(True),source.splitlines(True),fromfile='successor-r6',tofile='candidate-r8')))
 # Stronger than a diff eyeball: after these exact pin/path/gate replacements,
 # every remaining byte must equal the reviewed ancestor.
 derived=base.replace('"""Reviewed four-file r4 executor successor; outer-held exact-identity window only."""','"""DISABLED r8 draft; exact artifacts and independent admission are pending."""')
 derived=derived.replace("PAFTER='5fba80506cd1a494de5fb6aee63930192d6d0539657cca51e99381ff8a052ee4'", "PAFTER='0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471'")
 derived=derived.replace("EXECUTION_REVIEW='APPROVED'", "EXECUTION_REVIEW='UNAPPROVED'\nDSHA='6e83e924aae709f0c90ba2a966910febb63471b7a9a6294c6dee585a73ff3b4b'")
 derived=derived.replace('candidate-r4/deploy-inputs/libttmplayer.so','candidate-r8/deploy-inputs/libttmplayer.so')
 derived=derived.replace("or not re.fullmatch(r'[0-9a-f]{64}',PAFTER)","or not re.fullmatch(r'[0-9a-f]{64}',PAFTER)\n    or not re.fullmatch(r'[0-9a-f]{64}',DSHA)")
 derived=derived.replace(";DSHA='9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f'",'')
 derived=derived.replace("dso=base/'candidate/deploy-inputs'/DSO","dso=base/'candidate-r8/deploy-inputs'/DSO")
 assert derived==source,'unexpected executor delta'
 checker=(m/(B+'check_offline.py')).read_text()
 # Reuse the original checker verbatim except its local source filename and
 # the synthetic apply-plan's DSO pin. Original real r3 fixture stays unchanged.
 adapted=checker.replace("D/'video_guarded_window_r6.py'","D/'video_guarded_window_r8.py'")
 needle='fixture=dict(original,player_path='
 assert adapted.count(needle)==1
 adapted=adapted.replace(needle,"fixture=dict(original,dso_sha=constants['DSHA'],player_path=")
 adapted=adapted.replace("'fixture_extension':'Only r4 player fields added in memory to real r3 plan; not a real r4 apply receipt.'", "'fixture_extension':'R8 player fields and compat SHA added in memory to original r3 fixture; synthetic r8 plan, not an actual r8 apply receipt.'")
 (out/'checker-adapter.diff').write_text(''.join(difflib.unified_diff(checker.splitlines(True),adapted.splitlines(True),fromfile='original-checker',tofile='r8-adapted-checker')))
 exact_cli=[]
 with tempfile.TemporaryDirectory(prefix='r8-executor-offline-') as td:
  t=Path(td);shutil.copytree(m/(B+'fixtures'),t/'fixtures')
  (t/'video_guarded_window_r8.py').write_text(source);(t/'check_offline.py').write_text(adapted)
  for mode in ['preflight','apply','rollback']:
   dest=t/(mode+'-must-not-exist')
   cp=subprocess.run([sys.executable,str(t/'video_guarded_window_r8.py'),mode,'--boot','00000000-0000-0000-0000-000000000000','--parent','1','--birth','1','--out',str(dest)],capture_output=True,timeout=10,cwd=t)
   assert cp.returncode==1 and b'UNAPPROVED_DRAFT' in cp.stderr and not dest.exists()
   (out/(mode+'-unapproved.stdout.txt')).write_bytes(cp.stdout);(out/(mode+'-unapproved.stderr.txt')).write_bytes(cp.stderr)
   exact_cli.append({'mode':mode,'rc':cp.returncode,'out_created':False})
  cp=subprocess.run([sys.executable,str(t/'check_offline.py')],capture_output=True,timeout=20,cwd=t)
  (out/'checker.stdout.txt').write_bytes(cp.stdout);(out/'checker.stderr.txt').write_bytes(cp.stderr)
  (out/'checker.rc.txt').write_text(str(cp.returncode)+'\n');assert cp.returncode==0,cp.stderr.decode()
  checks=json.loads((t/'offline-checks.json').read_text())
  for name in ['offline-checks.json','offline-apply.sh.txt','offline-rollback.sh.txt']:shutil.copyfile(t/name,out/name)
  # Prove isolation of the exact early gate with a trap on BMS import.
  tree=ast.parse(source);gate=next(n for n in tree.body if isinstance(n,ast.If) and 'EXECUTION_REVIEW' in ast.unparse(n.test))
  assert tree.body.index(gate)<next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Import) and any(x.name=='bms_batch' for x in n.names))
  # Test each sentinel independently; old checker has UNAPPROVED as default,
  # which alone masks the other invalid pin branches after this migration.
  const={}
  for n in tree.body:
   if isinstance(n,ast.Assign):
    try:v=ast.literal_eval(n.value)
    except (ValueError,TypeError):continue
    for target in n.targets:
     if isinstance(target,ast.Name):const[target.id]=v
  import re
  for field in ['EXECUTION_REVIEW','PAFTER','DSHA','PLAYER_INPUT_REL','PLAYER_METADATA','PLAYER_LABEL']:
   env=dict(const,re=re,sys=sys);env['EXECUTION_REVIEW']='APPROVED';env[field]='UNAPPROVED'
   try:exec(compile(ast.Module(body=[gate],type_ignores=[]),'isolated-gate','exec'),env)
   except SystemExit as e:assert 'UNAPPROVED_DRAFT' in str(e)
   else:raise AssertionError('sentinel accepted: '+field)
 # Reader is parsed, never imported: no Board, no device reads.
 reader=(m/(P+'candidate-r8/deployment/read_binding.py')).read_text();rt=ast.parse(reader)
 fn=next(n for n in rt.body if isinstance(n,ast.FunctionDef) and n.name=='main')
 slotnode=next(n for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='slots' for x in n.targets))
 slots=ast.literal_eval(slotnode.value)
 assert ('player_mirror_GOT','libttmplayer.so',0x471f88,8) in slots
 assert ('compat_vprint_GOT','libopensles_android_compat.so',0x3258,8) in slots
 start=reader.index("    values = {r['label']");end=reader.index("    result['identity_after_reads']",start)
 block='\n'.join(line[4:] for line in reader[start:end].splitlines())
 binding=[]
 for left in [True,False]:
  for right in [True,False]:
   env={'biases':{'libopensles_android_compat.so':(0x100000,''),'liblog.so':(0x200000,'')},'result':{'reads':[{'label':'player_mirror_GOT','value':hex(0x101aac if left else 0x100000)},{'label':'compat_vprint_GOT','value':hex(0x207450 if right else 0x200000)}]}}
   exec(block,env);r=env['result']['binding_checks'];assert r['player_mirror_GOT']['match']==left and r['compat_vprint_GOT']['match']==right
   binding.append({'mirror_match':left,'vprint_match':right,'recorded_exactly':True})
 result={'status':'ACCEPT_OFFLINE_DISABLED_EXECUTOR','device_calls':0,'source_pins':PINS,'delta':'Only exact candidate pins/paths/docstring and early DSHA gate extension; all remaining bytes equal r6.','known_rollback_states':32,'foreign_rejections':11,'independent_early_gate_cases':6,'exact_unapproved_cli':exact_cli,'original_checker_rc':cp.returncode,'reader_dual_binding_cases':binding,'reader_status':'READ_ONLY_COLLECTOR_ACCEPT; mismatches are recorded false, not a process exit failure. Outer must require both match=true and final identity_after_reads.','limitations':['Generated shell is checked, not executed. Remote filesystem/transport/permissions are not simulated.','32 states use a synthetic r8 extension of the historical r3 apply fixture; no real r8 transaction claimed.','Production executor remains UNAPPROVED. No approval bit or source was changed.','Actual runtime GOT values and playback remain unknown.']}
 (out/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
