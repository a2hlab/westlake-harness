"""Export immutable raw evidence with path normalization and exact image bytes.

No device access and no lit verdict. Large logs/binaries stay in the persistent
raw archive; its chunked inventory binds every file rather than dropping it.
"""
from pathlib import Path
import os,json,re,hashlib,shutil,datetime
H=Path(__file__).resolve().parent;P=H.parent;W=H.parents[3]
ARCHIVE=W/'westlake-inputs/generations/u13-stageA-window3-20261003'
ROWS=[]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def clean(s):
 for a,b in [(str(W),'$WORKSPACES'),(str(Path.home()),'$MAC_HOME'),(os.environ.get('LAB_HOME','__unused_lab_home__'),'$LAB_HOME')]:s=s.replace(a,b)
 s=re.sub(r'/home/[^/\s\"\']+', '$VM_HOME',s)
 return s
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(clean(json.dumps(d,indent=2,ensure_ascii=False))+'\n')
def public(src,dest):
 if not src.is_file():return
 dest.parent.mkdir(parents=True,exist_ok=True)
 if src.suffix.lower() in {'.jpeg','.jpg','.png'}:shutil.copyfile(src,dest);method='byte-identical'
 else:dest.write_text(clean(src.read_text(errors='replace')));method='private-path-normalization'
 ROWS.append({'source':clean(str(src)),'public':str(dest.relative_to(H)),'raw_sha256':sha(src),'public_sha256':sha(dest),'method':method})
def records(root):
 return sorted(root.glob('*/*/*/*/record.json'))
coverage={};selftests={};longwait=[];sheet_index={}
for board,d in [('5ea',H),('5cd',H),('61b',P/'window3-61b')]:
 plan=json.loads((d/f'plan-{board}.json').read_text());out=Path(plan['out'].replace('$WORKSPACES',str(W)));root=out.parent
 measured=[];seen=[];no_t20=[]
 for r in records(out):
  data=json.loads(r.read_text())
  if data.get('status') in {'captured','foreground_unconfirmed','app_failed'} and data.get('finished_at'):
   row={'shard':r.relative_to(out).parts[0],'key':r.parent.name,'record':clean(str(r)),'status':data['status'],'finished_at':data['finished_at']}
   t20=[shot for shot in data.get('screenshots',[]) if shot.get('captured') and ('t20.' in str(shot.get('path','')) or shot.get('at_seconds')==20)]
   row['captured_t20']=bool(t20);measured.append(row);seen.append(r.parent.name)
   if not t20:no_t20.append({**row,'error':data.get('error'),'reason':'completed attempt without captured t20; not screenshot-comparable'})
 remaining=[]
 for shard in plan['shards']:
  keys=Path(shard['keys_file'].replace('$WORKSPACES',str(W))).read_text().split()
  done={x['key'] for x in measured if x['shard']==shard['name']}
  remaining += [{'shard':shard['name'],'key':key,'reason':'35-minute new-key cutoff'} for key in keys if key not in done]
 coverage[board]={'planned_observations':sum(len(Path(s['keys_file'].replace('$WORKSPACES',str(W))).read_text().split()) for s in plan['shards']), 'measured_observations':len(measured),'measured_unique_keys':len(set(seen)),'measured':measured,'remaining':remaining,'remaining_observations':len(remaining),'retry_needed_no_t20':no_t20,'auxiliary_not_in_regression_denominator':True}
 tests=[]
 for f in sorted((out/'selftest').glob('*.json')):
  r=json.loads(f.read_text());tests.append({'shard':f.stem,**{k:r[k] for k in ['run_count','selftest_error_count','badtag_count','probe_error_count','unknown_runs']}});public(f,H/'evidence'/board/'selftest'/f.name)
 selftests[board]=tests
 # All control and observation records; do not descend full diagnostic trees.
 all_records=records(out)+sorted((out/'additional').glob('*/*/*/*/record.json'))+sorted((out/'smoke').glob('*/*/*/*/record.json'))
 for recovery in root.glob('recovery-smoke-*'):all_records+=sorted(recovery.glob('*/*/*/*/record.json'))
 view=H/('contact-index-'+board);view.mkdir(exist_ok=True);image_order=[]
 for i,r in enumerate(all_records):
  data=json.loads(r.read_text());relative=r.relative_to(root);dest=H/'evidence'/board/relative;public(r,dest)
  for pat in ['t*.jpeg','t*.png','processes-t*.txt','maps-t*.txt','install.txt','install-*.json','preflight.json']:
   for f in r.parent.glob(pat):
    if f.is_file() and f.stat().st_size<1000000:public(f,dest.parent/f.name)
  log=r.parent/'hilog.txt';selected=[]
  if log.exists():
   for n,line in enumerate(log.open(errors='replace'),1):
    if re.search(r'\[WL-KS-PROBE\]|\[B43-BIND\]|FATAL EXCEPTION|JniAbort|UnsatisfiedLinkError|Fatal signal|exit.*signal|DfxFaultLogger.*Pid|ICUWrapper|load libicu',line):
     selected.append(f'{n}: {line.rstrip()}')
     if len(selected)>=170:break
   save(dest.parent/'hilog-excerpt.json',{'full_log_archive':clean(str(ARCHIVE/d.name/log.relative_to(d))),'raw_sha256':sha(log),'selection':'first170 probe/bind/exception candidates; not a terminal verdict','lines':selected})
  if 'additional' in relative.parts:
   pid_re=re.compile(r'^\S+ \S+\s+(\d+)\s+\d+\s+\w\s');pids=set();bind_start=[];bind_ok=[];terminal=[];exceptions=[]
   if log.exists():
    lines=log.read_text(errors='replace').splitlines()
    for n,l in enumerate(lines,1):
     if '[B43-BIND] ensureBindApplication start bundle='+data['package'] in l:
      m=pid_re.match(l)
      if m:pids.add(m[1]);bind_start.append({'line_number':n,'line':l})
    for n,l in enumerate(lines,1):
     m=pid_re.match(l)
     fault_target=('DfxFaultLogger' in l and any(re.search(r'(?:Pid|pid)\s*[=:]\s*'+pid+r'\b',l) for pid in pids))
     if (not m or m[1] not in pids) and not fault_target:continue
     if '[B43-BIND]' in l and 'handleBindApplication returned OK' in l:bind_ok.append({'line_number':n,'line':l})
     if fault_target or re.search(r'JniAbort|FATAL EXCEPTION|Fatal signal|exit.*signal|JNI DETECTED ERROR',l):terminal.append({'line_number':n,'line':l})
     if re.search(r'(?:\[stderr\]\s*|failed[:=]\s*)[\w.$]*(?:Exception|Error):|(?:load|dlopen).*libicu.*fail|ICUWrapper',l):exceptions.append({'line_number':n,'line':l})
   longwait.append({'board':board,'key':data['key'],'record':clean(str(r)),'status':data['status'],'launch_error':data.get('error'),'target_pids_from_exact_bind_bundle':sorted(pids),'bind_start':bind_start[:1],'bind_returned_OK':bind_ok[:1],'first_terminal':terminal[:1],'first_exception_candidate':exceptions[:1],'terminal_if_absent':'unknown; do not substitute nonterminal SIGILL/sigchain noise','captured_paths':[clean(x['path']) for x in data.get('screenshots',[]) if x.get('captured')]})
  image=dest.parent/'t20.jpeg'
  if image.exists():
   label=f'{i:03d}-'+r.parent.name;link=view/label
   if not link.exists():link.symlink_to(dest.parent.resolve(),target_is_directory=True)
   image_order.append({'label':label,'record':str(dest.relative_to(H)),'kind':'recovery' if relative.parts[0].startswith('recovery-smoke') else 'candidate'})
 sheet_index[board]=image_order
 for pat in ['baseline/identity.json','baseline/process-view.json','post-apply/identity.json','post-apply/process-view.json','restored-*/identity.json','restored-*/process-view.json','final-*/identity.json','final-*/process-view.json','finish.json','runner/board-run-result.json','runner/smoke/smoke-result.json','recovery-smoke-*/smoke-result.json']:
  for f in root.glob(pat):
   if f.stat().st_size<1000000:public(f,H/'evidence'/board/f.relative_to(root))
 for f in root.glob('apply.json'):
  a=json.loads(f.read_text());save(H/'evidence'/board/'apply-summary.json',{'raw_sha256':sha(f),'full_archive':clean(str(ARCHIVE/d.name/f.relative_to(d))),'status':a.get('status'),'verification':a.get('verification'),'fingerprints':a.get('fingerprints'),'operations':len(a.get('operations',[]))})
 save(H/'sheets'/(board+'-order.json'),image_order)
for d in [H,P/'window3-61b']:
 for pat in ['gate-*-pass.json','infra*.json','reopen.json','arm-receipt.json','production-*.txt','gates/*/summary.json','gates/*/native-gate.json','gates/*/static-checks.json','gates/*/image-gates.json','gates/*/tools.json','gates/*/frozen*.json','gates/*/t4b.json','gates/*/rb.txt','gates/*/frozen.txt']:
  for f in d.glob(pat):
   if f.stat().st_size<1000000:public(f,H/'evidence/production'/d.name/f.relative_to(d))
for b in ['5ea','5cd','61b']:
 for stem in ['run-facts','facts']:
  f=H/(f'run-facts-{b}.txt' if stem=='run-facts' else f'facts-{b}-verbatim.txt');public(f,H/'evidence/facts'/f.name)
save(H/'coverage.json',coverage);save(H/'selftest-summary.json',selftests);save(H/'longwait-readout.json',longwait);save(H/'public-evidence-index.json',ROWS)
print(json.dumps({b:{k:r[k] for k in ['measured_observations','measured_unique_keys','remaining_observations']} for b,r in coverage.items()},indent=2))
