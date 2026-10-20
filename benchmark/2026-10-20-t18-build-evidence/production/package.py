#!/usr/bin/env python3
"""Package frozen T18 inputs and existing executions. No build, device or network calls."""
import argparse,hashlib,json,os,shlex,subprocess,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'scripts/lab/run_facts.py').is_file())
PROD='benchmark/2026-10-20-t18-audiotrack-production'
SIZE='benchmark/2026-10-20-t18-audiotrack-size'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--write',action='store_true');a=ap.parse_args()
 if not a.write:print('Read-only default. --write verifies inputs and creates one fresh archive.');return
 home=Path.home();base=home/'.local/share/westlake/toutiao-resume-20261020';build=home/'.local/share/westlake/t18-production';repo=ROOT.parent/'westlake-harness';producer=ROOT.parent/'westlake-harness-video-plan';private=HERE/'.private/archive-01';private.mkdir(parents=True,exist_ok=False);public=HERE/'packet';public.mkdir(exist_ok=False)
 def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
 def resolve(s):
  if s.startswith('$HOME/'):return home/s[6:]
  if s.startswith('$BASE20/'):return base/s[8:]
  raise ValueError('Unsupported raw alias')
 def raw_alias(p):
  if p.is_relative_to(base):return 'raw/BASE20/'+str(p.relative_to(base))
  return 'raw/HOME/'+str(p.relative_to(home))
 selected={};sourcepins=[]
 def add(name,p):
  assert not name.startswith('/') and '..' not in Path(name).parts and p.is_file(),name
  if name in selected:assert selected[name].resolve()==p.resolve(),name
  selected[name]=p
 def tree(p):
  assert p.is_dir()
  for f in sorted(p.rglob('*')):
   if f.is_file():add(raw_alias(f),f)
 for rep,short in [(repo,'4bfd621299'),(repo,'7c0423ddcc'),(producer,'9b3cd6cbc')]:
  commit=subprocess.check_output(['git','-C',str(rep),'rev-parse',short],text=True).strip()
  names=subprocess.check_output(['git','-C',str(rep),'diff-tree','--no-commit-id','--name-only','-r',commit],text=True).splitlines()
  for rel in names:
   blob=subprocess.check_output(['git','-C',str(rep),'show',commit+':'+rel]);p=private/'source-snapshots'/commit/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob);add('source-repo/'+rel,p);sourcepins.append(dict(path=rel,commit=commit,sha256=sha(p),bytes=p.stat().st_size))
 prodcommit=sourcepins[-1]['commit'];frozenroot=private/'source-snapshots'/prodcommit/PROD
 validation=[]
 for rep,rel,commit in [(repo,SIZE,'4bfd621299'),(producer,PROD,'9b3cd6cbc')]:
  blob=subprocess.check_output(['git','-C',str(rep),'show',commit+':'+rel+'/private-raw-index.json'])
  for r in json.loads(blob):
   p=resolve(r['path']);assert p.is_file() and p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],r['path'];add(raw_alias(p),p);validation.append(dict(path=r['path'],sha256=r['sha256'],bytes=r['bytes']))
 # Completed attempts, including files not individually mentioned by the index.
 for p in sorted(base.glob('t18-peer-*')):
  if p.is_dir():tree(p)
 tree(home/'.local/share/westlake/t18-owner-object/first');tree(home/'.local/share/westlake/t18-hostchecks')
 for name in ['baseline-mac-01','audio-baseline-mac-01','production-01','production-02','peer-thunk-review','peer-deploy-review']:tree(build/name)
 for p in sorted(build.iterdir()):
  if p.is_file():add(raw_alias(p),p)
 # Recover only the roots from actual successful compile argv. No guessed personal path.
 argv=json.loads((build/'production-02/baseline-compile.argv.json').read_text());sysroot=Path(next(x.split('=',1)[1] for x in argv if x.startswith('--sysroot=')));inputs=sysroot.parents[3];sdk=Path(argv[0]).parents[2]
 assert inputs/'toolchains/ohos-sdk/native/sysroot'==sysroot
 pins=json.loads((frozenroot/'input-pins.json').read_text());assert len(pins)==720
 assert pins==json.loads((build/'production-02/input-pins.json').read_text())
 inputrows=[]
 for name,r in pins.items():
  alias,rel=name.split('/',1);assert alias in ['$INPUTS','$SDK'];p=({'$INPUTS':inputs,'$SDK':sdk}[alias])/rel
  assert p.is_file() and p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],name
  an='input-bundle/'+alias[1:]+'/'+rel;add(an,p);inputrows.append(dict(recipe_path=name,archive_path=an,**r,mode=oct(p.stat().st_mode&0o777)))
 deps=json.loads((build/'production-02/all-includes.json').read_text());depmap=[]
 for name,r in deps.items():
  p=Path(name);assert p.is_file() and sha(p)==r['sha256'] and p.stat().st_size==r['bytes']
  if p.is_relative_to(inputs):key='$INPUTS/'+str(p.relative_to(inputs));an='input-bundle/INPUTS/'+str(p.relative_to(inputs));assert pins[key]==r
  elif p.is_relative_to(sdk):key='$SDK/'+str(p.relative_to(sdk));an='input-bundle/SDK/'+str(p.relative_to(sdk));assert pins[key]==r
  else:assert p.is_relative_to(build/'production-02');an=raw_alias(p);assert an in selected
  depmap.append(dict(archive_path=an,**r))
 assert len(depmap)==607
 originals=[]
 for rel in ['out-touch21/fd/bridge15/artifacts.json','out-ability38/native-stack/artifacts.json']:
  p=inputs/rel;assert p.is_file();an='original-build-records/INPUTS/'+rel;add(an,p);originals.append(dict(archive_path=an,sha256=sha(p),bytes=p.stat().st_size,scope='Existing source/build records, preserved separately from new executions.'))
 # Preserve the exact current gate and registry as contextual input; gate still requires repository git history.
 for rel in ['scripts/lab/check_frozen.py','knowledge/frozen/frozen.json']:
  p=repo/rel;add('repository-context/'+rel,p)
 outcomes=[]
 for name in ['production-01','production-02']:
  d=build/name;assert sha(d/'baseline.so')=='d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b';assert sha(d/'candidate.so')=='dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9'
  stages={n:int((d/(n+'.rc')).read_text()) for n in ['frozen','baseline-link','baseline-compile','candidate-compile','candidate-link','baseline-elf','candidate-elf']};assert all(v==0 for v in stages.values())
  outcomes.append(dict(attempt=name,stages=stages,result_sha256=sha(d/'result.json'),baseline_sha256=sha(d/'baseline.so'),candidate_sha256=sha(d/'candidate.so'),provenance='NEW_EXECUTION_NOT_HISTORICAL_BUILD_LOG'))
 for n in ['baseline-mac-01','audio-baseline-mac-01']:assert (build/n/'rc').read_text().strip()=='0'
 dump(public/'input-bundle-index.json',dict(count=len(inputrows),bytes=sum(x['bytes'] for x in inputrows),files=inputrows))
 dump(public/'include-coverage.json',dict(count=len(depmap),original_pinned=605,generated_in_production02=2,files=depmap))
 dump(public/'source-pins.json',dict(files=sourcepins))
 dump(public/'original-records.json',originals)
 dump(public/'private-raw-validation.json',dict(entries=len(validation),all_match=True,files=validation))
 results=dict(token='t18-production-archive',status='LOCAL_COMPLETE_REMOTE_PENDING',source_only_originals_preserved=True,production_freeze=prodcommit,input_count=720,actual_include_count=607,production_attempts=outcomes,baseline_mac_sha256=sha(build/'baseline-mac-01/liboh_adapter_bridge.so'),candidate_sha256=outcomes[-1]['candidate_sha256'],whole_bridge_source_rebuild=False,incremental_relink_inputs_present=True,runtime_registration='UNKNOWN',audio_output='UNKNOWN',video='NOT_PASSED_NOT_TESTED_HERE',device_calls=0,builds_by_archive_lane=0)
 dump(public/'results.json',results)
 # Explanatory extraction instructions stay with the archive; no absolute user paths in this text.
 notes=private/'INPUT-BUNDLE.md';notes.write_text('T18 incremental relink input bundle\n\nExtract into a persistent directory. INPUTS is input-bundle/INPUTS; SDK is input-bundle/SDK. Files are regular bytes (including dereferenced compiler symlinks), with source modes preserved. source-repo/ preserves the exact frozen source, recipes and tests; use them in the corresponding repository checkout. build.py --inputs "$INPUTS" --sdk "$SDK" --out "$NEW_OUT" --execute is the original producer entry. This archive did not rerun it at relocated paths. check_frozen.py --git requires the original repository git history; repository-context/ is an evidence snapshot, not a replacement for that history. Exact 720 pins are supplied; tools are the recorded host SDK binaries and still require a compatible host OS/system libraries. Original build records are separate from raw/HOME/.local/share/westlake/t18-production new executions. No claim that all legacy bridge objects were rebuilt from source.\n')
 add('input-bundle/README.md',notes)
 for p in sorted(public.iterdir()):add('archive-review/'+p.name,p)
 add('archive-review/package.py',Path(__file__).resolve())
 members=[dict(path=n,sha256=sha(p),bytes=p.stat().st_size,mode=oct(p.stat().st_mode&0o777)) for n,p in sorted(selected.items())];dump(private/'members.json',dict(files=members));add('archive/members.json',private/'members.json')
 index={x['path']:x for x in members};index['archive/members.json']=dict(sha256=sha(private/'members.json'),bytes=(private/'members.json').stat().st_size)
 tarpath=private/'window.tar.gz'
 with tarfile.open(tarpath,'w:gz') as tar:
  for n,p in sorted(selected.items()):tar.add(p.resolve(),arcname=n,recursive=False)
 with tarfile.open(tarpath,'r:gz') as tar:
  ms=tar.getmembers();assert len(ms)==len(selected)
  for member in ms:
   assert member.isfile() and member.size==index[member.name]['bytes'];assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==index[member.name]['sha256']
 assert all(sha(p)==index[n]['sha256'] for n,p in selected.items()),'input drift during packaging'
 old=json.loads((home/'.local/share/westlake/toutiao-resume-20261019/video-r10-window-archive/receipt.json').read_text());remote_root=os.environ.get('HW248_ARTIFACT_ROOT',str(Path(old['remote']).parent.parent));rd=remote_root.rstrip('/')+'/toutiao-t18-audiotrack-production-20261020'
 cmds=[['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','test ! -e '+shlex.quote(rd)+' && mkdir -p '+shlex.quote(rd)],['scp','-o','BatchMode=yes','-o','ConnectTimeout=10',str(tarpath),'hw248:'+rd+'/window.tar.gz'],['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','hw248','sha256sum '+shlex.quote(rd+'/window.tar.gz')+' && stat -c %s '+shlex.quote(rd+'/window.tar.gz')]]
 dump(private/'remote-commands.private.json',cmds)
 receipt=dict(token='t18-production-archive',archive_sha256=sha(tarpath),bytes=tarpath.stat().st_size,member_count=len(selected),local_member_sha_verified=True,input_pins_verified=720,includes_covered=607,remote='HW248_ARTIFACT_ROOT/toutiao-t18-audiotrack-production-20261020/window.tar.gz',remote_verified=False,commands=[],members_index_sha256=sha(private/'members.json'),remote_commands_sha256=sha(private/'remote-commands.private.json'))
 dump(private/'receipt.json',receipt);dump(public/'archive-receipt.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
