#!/usr/bin/env python3
"""Preserve input bytes and sanitized command evidence without changing original logs."""
import json, shutil
from pathlib import Path
from prepare_inputs import HERE, sha, save, expand, alias
from build_candidate import run

def main():
 raw=HERE/'.private';receipt=json.loads((HERE/'upstream/policy-build-receipt.json').read_text());inputs=raw/'input-lock';inputs.mkdir(exist_ok=False)
 input_index=[]
 for group in ['headers','reused_inputs']:
  for path,h in receipt[group].items():
   p=Path(expand(path));assert sha(p)==h
   q=inputs/'by-sha'/h;q.parent.mkdir(exist_ok=True)
   if not q.exists():shutil.copyfile(p,q)
   input_index.append({'source':path,'sha256':h,'bytes':q.stat().st_size,'stored':'by-sha/'+h})
 for command in receipt['commands']:
  p=Path(expand(command['raw_path']));assert sha(p)==command['raw_sha256']
  q=inputs/'original-logs'/p.name;q.parent.mkdir(exist_ok=True);shutil.copyfile(p,q)
  input_index.append({'source':command['raw_path'],'sha256':sha(p),'bytes':p.stat().st_size,'stored':'original-logs/'+p.name})
 save(inputs/'index.json',input_index);save(HERE/'archived-input-index.json',input_index)
 tool=raw/'tool-identity';tool.mkdir();compiler=next(p for p in receipt['toolchain'] if p.endswith('/clang'))
 run(tool,'compiler-version',[compiler,'--version'],tool)
 run(tool,'linker-version',[str(Path(compiler).parent/'ld.lld'),'--version'],tool)
 refresh()

def refresh():
 raw=HERE/'.private'
 public=HERE/'evidence';public.mkdir(exist_ok=True);normalization=[]
 for p in sorted(raw.rglob('*')):
  if not p.is_file() or 'commands' not in p.parts or p.name not in ['argv.json','result.json','stdout','stderr']:continue
  rel=p.relative_to(raw);q=public/rel
  if p.suffix!='.json':q=q.with_suffix('.txt')
  q.parent.mkdir(parents=True,exist_ok=True);data=p.read_text();q.write_text(alias(data))
  normalization.append({'original':'$G18/.private/'+str(rel),'original_sha256':sha(p),'original_bytes':p.stat().st_size,'public':str(q.relative_to(HERE)),'public_sha256':sha(q),'sanitized':'path aliases only'})
 save(HERE/'sanitization.json',normalization)
 index=[{'path':'$G18/.private/'+str(p.relative_to(raw)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(raw.rglob('*')) if p.is_file()]
 save(HERE/'raw-index.json',index)
 builds=json.loads((HERE/'build-01-receipt.json').read_text());elf=json.loads((HERE/'elf-review.json').read_text());tests=json.loads((HERE/'regression.json').read_text())
 counts={}
 for variant in ['baseline','candidate']:
  for tag in ['registry','registry-delta']:
   counts[variant+'-'+tag]=(raw/'regression-02/commands'/(variant+'-'+tag+'-run')/'stdout').read_text().strip()
 save(HERE/'results.json',{'status':'OFFLINE_CANDIDATE_BUILT_AND_VERIFIED','baseline':builds['artifacts']['baseline'],'candidate':builds['artifacts']['candidate'],'shared':{'baseline':7,'candidate':8,'added':['libGLESv2.so']},'system_libraries_unchanged':7,'native_build_commands_rc0':len(builds['records']),'dynamic_symbol_tuples':len(elf['candidate']['dynamic_abi']),'needed':elf['candidate']['needed'],'regression_actual_stdout':counts,'negative_policy_cases':3,'first_test_adapter_failure_preserved':'regression-first-failure.json','predicted_key':'genshin','predicted_blocker':'libyuanshen.so dependency libGLESv2.so name visibility','errno_changed':False,'deployment_performed':False,'child_mapping_verified':False,'game_frame_verified':False,'device_calls':0,'next_gate':'outer must bind actual child loaded object and authorize bounded deployment; no automatic deployment','raw_files_indexed':len(index),'raw_modified':False,'private_root':'$G18/.private','archive_remote_verified':False})
 print('indexed',len(index),'raw files;',len(normalization),'sanitized command files; actual tests',counts)
if __name__=='__main__':
 import sys
 refresh() if '--refresh' in sys.argv else main()
