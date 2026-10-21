#!/usr/bin/env python3
"""Explicit public evidence projection. Raw receipts and first-slice history are immutable."""
import argparse,hashlib,json,shutil
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[2];W=R.parent;HOME=Path.home();P=HOME/'.local/share/westlake/commercial-game-20261021'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sanitize(s):
 for a,b in sorted([(str(R),'$REPO'),(str(W/'westlake-harness-bms-deploy'),'$BMS_DEPLOY'),(str(W/'westlake-harness'),'$MAIN'),(str(W),'$WORKSPACES'),(str(HOME),'$HOME')],key=lambda x:-len(x[0])):s=s.replace(a,b)
 return s
def public(p,v):p.write_text(sanitize(json.dumps(v,indent=2))+'\n')
def main():
 a=argparse.ArgumentParser();a.add_argument('--write',action='store_true',required=True);a.parse_args();F=D/'final';F.mkdir(exist_ok=True)
 b=P/'g30-outer-baseline-01/build';o=P/'g30-outer-candidate-02';c1=D/'.private/candidate-01';c2=D/'.private/candidate-02';h=D/'.private/host-02';n=D/'.private/preservation-01'
 before=json.loads((o/'inputs-before.json').read_text())['inputs'];after=json.loads((o/'inputs-after.json').read_text())['inputs'];assert before==after and len(before)==55
 r1=json.loads((c1/'receipt.json').read_text());r2=json.loads((c2/'receipt.json').read_text());assert r1['inputs']==r2['inputs']==before
 closure=D/'.private/input-closure';closure.mkdir(exist_ok=True);entries=[]
 for s,v in before.items():
  p=Path(s);assert sha(p)==v['sha256'] and p.stat().st_size==v['bytes'];dst=closure/v['sha256']
  if not dst.exists():shutil.copyfile(p,dst)
  assert sha(dst)==v['sha256'];entries.append({'source':s,'copy':str(dst),**v})
 public(F/'input-closure.json',{'count':len(entries),'candidate02_before_after_equal':True,'files':entries,'limit':'55 declared source/header/tool/link/receipt inputs, not complete Linux OS dynamic dependency closure; tc/runtime did not exist'})
 peer=P/'outer-review/g30-peer-01/candidate-build-01/results.json';assert sha(peer)=='0bdb310a9ed14f1c20d7fba9dcacba60fdf940ac924f3c2e51075ec4fda197df'
 for name,p in [('baseline-receipt',b/'receipt.json'),('candidate01-receipt',c1/'receipt.json'),('candidate02-receipt',c2/'receipt.json'),('candidate02-bookends',o/'result.json'),('host-receipt',h/'receipt.json'),('preservation-receipt',n/'receipt.json'),('peer-review',peer)]:public(F/(name+'.json'),json.loads(p.read_text()))
 for name,p in [('host-output.txt',h/'run.stdout'),('preservation-baseline.txt',n/'baseline-run.stdout'),('preservation-candidate.txt',n/'candidate-run.stdout')]: (F/name).write_text(sanitize(p.read_text()))
 rawdirs=[b.parent,P/'g30-outer-candidate-01',o,D/'.private/launch-baseline-01',D/'.private/frozen-01',c1,c2,D/'.private/host-01',h,n,D/'.private/elf-review-01',D/'.private/final-validation-01']
 raw=[]
 for folder in rawdirs:
  for p in sorted(folder.rglob('*')):
   if p.is_file() and 'module-cache' not in p.parts:raw.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
 public(F/'raw-index.json',raw)
 public(F/'results.json',{'status':'OFFLINE_CANDIDATE_VERIFIED_NOT_DEPLOYED','expected_first_fatal_keys':['genshin'],'baseline_sha256':sha(b/'libwestlake_native_abi.so'),'candidate_sha256':sha(c2/'libwestlake_native_abi.so'),'candidate_bytes':(c2/'libwestlake_native_abi.so').stat().st_size,'candidate_reproductions':2,'input_bookends':55,'old_objects_identical':True,'locale_actual_TU':{'classifications':257,'integer_cases':90,'host':'Darwin; not OH execution'},'preservation_actual_TU':'baseline and candidate atfork/FD/errno/constructor host seams pass; old stdio object byte-identical','elf_review':'../evidence/elf-review.json','abi_counterexample_tests':9,'source':{'locale':sha(D/'sources/candidate/bionic_locale_compat.c'),'candidate_recipe':sha(D/'build_candidate.py')},'history':['VM entry rc124: no compiler evidence, subsequent execution explicitly handed to outer','host01 failed errno assumption; Darwin underlying strtoll/strtoull set EINVAL on no conversion, host02 directly compares forwarding and passes','candidate01 input collection not entirely before build; candidate02 records all 55 before and after'],'limits':['No Linux OS image/dynamic host library closure','Actual Genshin namespace winner UNKNOWN','No game/device/REA execution','__assert2 excluded','No public API freeze or deployment authorization']})
 print('published',len(raw),'raw records; 55 copies; first-slice files unchanged')
if __name__=='__main__':main()
