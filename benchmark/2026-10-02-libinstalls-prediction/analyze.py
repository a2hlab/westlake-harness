#!/usr/bin/env python3
"""Read signed U10.1T8 runs offline; distinguish install portability from current fatal movement."""
import collections,csv,datetime,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts/lab'))
import first_fatal,cluster_first_cause
WS=ROOT.parent
BASE=ROOT/'benchmark/2026-10-02-u10-1-t8-rerun'
SIGN=ROOT/'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json'
DONOR=WS/'westlake-harness-bms/benchmark/2026-10-02-libinstalls-unification'
OLD='2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0'
NEW='51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def portable(p):return str(p.resolve()).replace(str(WS),'$WORKSPACES')
def evidence(p):return {'path':portable(p),'sha256':sha(p)} if p.exists() else None
def summary(run):
 p=run/'record.json';d=json.loads(p.read_text());ins=d.get('install',{});install=run/'install.txt';text=install.read_text(errors='replace') if install.exists() else ''
 chain=run.parent/'installation-chain/installation-chain.json';c=json.loads(chain.read_text()) if chain.exists() else {}
 disk=c.get('disk_identities',{});versions={disk.get('/system/lib64/'+x),disk.get('/system/lib64/platformsdk/'+x)} if (x:='libinstalls.z.so') else set()
 if len(versions)!=1 or None in versions:raise ValueError('missing or unequal installer aliases '+str(run))
 version=next(iter(versions));assert version in [OLD,NEW]
 fp=run.parent/'runtime-fingerprint.txt';hashes={l.split()[-1]:l.split()[0] for l in fp.read_text().splitlines() if len(l.split())==2}
 assert hashes['/system/bin/appspawn-x'].startswith('65cc3535') and hashes['/system/android/framework/oh-adapter-runtime.jar'].startswith('5ae3dd29'),str(run)
 accepted=ins.get('success_text') is True and 'success' in text.lower() and not re.search(r'code:\s*\d+|failed to install',text,re.I)
 status='accepted' if accepted else 'rejected' if re.search(r'failed to install|code:\s*\d+',text,re.I) else 'unknown'
 log=run/'install-hilog.txt';lines=log.read_text(errors='replace').splitlines() if log.exists() else []
 witnesses=[{'line':n,'text':l} for n,l in enumerate(lines,1) if any(s in l for s in ['accepted reviewed APK payload exception','APK native extraction failed:','CRC/payload/owner/mode'])]
 return {'key':d['key'],'package':d['package'],'board':d['serial'][:8],'serial':d['serial'],'libinstalls_sha256':version,'apk_sha256':d.get('apk_sha256'),'status':d.get('status'),'install_verdict':status,'bm_return_code':ins.get('return_code'),'finished_at':d.get('finished_at',0),'record':evidence(p),'install':evidence(install),'install_hilog':evidence(log),'identity_receipt':evidence(chain),'install_witnesses':witnesses,'_run':run}
def moves_install_wall(row, tuple_packages):
    return (row['package'] in tuple_packages and row['install_verdict']=='rejected'
            and row['libinstalls_sha256']==OLD
            and any('CRC/ELF/owner/mode' in w['text'] for w in row['install_witnesses']))

def select(rows):
 # Prefer final completed install acceptance; an earlier rejected attempt remains in all-attempt evidence.
 return max(rows,key=lambda r:(r['install_verdict']=='accepted',r['status'] not in ['started','batch_interrupted'],r['finished_at']))
def compact_fatal(run):
 record,events,pids,reports,gone,pins=first_fatal.load_run(run)
 t20=[s.get('captured_at') for s in record.get('screenshots',[]) if s.get('captured') and s.get('scheduled_seconds')==20]
 cutoff=datetime.datetime.fromtimestamp(max(t20)).strftime('%m-%d %H:%M:%S.%f') if t20 else None
 registry=json.loads(first_fatal.benign.REGISTRY.read_text())
 result=first_fatal.analyze(events,pids,reports,gone,registry,registry['context'],cutoff)
 sig=cluster_first_cause.cluster_key(result)
 terminal=result.get('terminal') or {};event=terminal.get('event') or {};root=result.get('root') or {}
 return {'status':result['status'],'cutoff':cutoff,'kind':sig['kind'],'cause':sig['cause'],'first_frame':sig['first_frame'],'terminal_line':event.get('line'),'terminal_text':event.get('message'),'root_event':root.get('event'),'target_pids':sorted(pids),'hilog':evidence(run/'hilog.txt'),'record_hilog_binding':pins,'limitations':result.get('limitations',[])}
def main():
 OUT.mkdir(exist_ok=True);signed=json.loads(SIGN.read_text());keys=set(signed['keys']);bykey=collections.defaultdict(list);attempts=[]
 for sub in ['window/boards','window2','window3','window4','window5']:
  for p in sorted((BASE/sub).rglob('record.json')):
   if '/runner/' not in str(p) or '/smoke/' in str(p) or p.parent.name not in keys:continue
   row=summary(p.parent);attempts.append(row);bykey[row['key']].append(row)
 assert set(bykey)==keys,(keys-set(bykey));assert len(keys)==166
 chosen=[];table=[]
 for n,key in enumerate(sorted(keys),1):
  row=select(bykey[key]);fatal=compact_fatal(row['_run']);v=signed['keys'][key]
  entry={k:x for k,x in row.items() if k!='_run'};entry.update(signed_verdict=v['verdict'],signed_note=v.get('note'),first_fatal=fatal,tuple_target=row['package'] in ['com.junkfood.seal','com.ss.android.article.news'],predicted_current_first_fatal_moved=moves_install_wall(row, {'com.junkfood.seal','com.ss.android.article.news'}))
  chosen.append(entry);table.append({'key':key,'board':row['board'],'version':row['libinstalls_sha256'][:8],'install':row['install_verdict'],'outer_verdict':v['verdict'],'first_fatal_kind':fatal['kind'],'cause':fatal['cause'],'tuple_target':entry['tuple_target'],'predicted_moved':int(entry['predicted_current_first_fatal_moved'])})
  if n%25==0:print('analyzed',n,flush=True)
 clean=[{k:v for k,v in r.items() if k!='_run'} for r in attempts]
 source=DONOR/'evidence/source.diff';source_text=source.read_text();tuples=re.findall(r'\{"([^"]+)", "([^"]+)", "([^"]+)", "([a-f0-9]{64})"\}',source_text)
 assert len(tuples)==4 and {t[0] for t in tuples}=={'com.junkfood.seal','com.ss.android.article.news'}
 def counts(rows):
  out={}
  for row in rows:
   cell=out.setdefault(row['board'],{'attempts':0,'accepted':0,'rejected':0,'unknown':0,'first_fatal_clusters':{}});cell['attempts']+=1;cell[row['install_verdict']]+=1
   if 'first_fatal' in row:
    k=row['first_fatal']['kind'];cell['first_fatal_clusters'][k]=cell['first_fatal_clusters'].get(k,0)+1
  return out
 targets=[r for r in clean if moves_install_wall(r,{t[0] for t in tuples})]
 results={'schema':'libinstalls-prediction/v1','device_access':False,'signed_baseline':evidence(SIGN),'source_diff':evidence(source),'raw_attempts':len(clean),'unique_keys':len(keys),'canonical_selected':len(chosen),'all_attempts_by_board':counts(clean),'canonical_by_board':counts(chosen),'source_tuple_targets':tuples,'current_canonical_first_fatal_keys_expected_moved':[r['key'] for r in chosen if r['predicted_current_first_fatal_moved']],'current_canonical_first_fatal_keys_expected_moved_count':sum(r['predicted_current_first_fatal_moved'] for r in chosen),'historical_stage_A_install_wall_keys':sorted({r['key'] for r in targets}),'historical_stage_A_install_wall_keys_count':len({r['key'] for r in targets}),'old_board_portability_target_keys':['fd-seal','toutiao'],'portability_target_count':2,'predicted_extra_lit_keys':0,'plan_created':False,'causal_limit':'Disjoint shards; no paired 166-key two-version experiment. Counts of runtime terminal kinds are descriptive, not installer causal effects. Canonical Seal/Toutiao attempts already use NEW and install. Earlier OLD Toutiao rejection is retained, not counted as its current fatal.'}
 (OUT/'attempts.json').write_text(json.dumps(clean,indent=2,ensure_ascii=False)+'\n');(OUT/'selected166.json').write_text(json.dumps(chosen,indent=2,ensure_ascii=False)+'\n');(OUT/'results.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
 with (OUT/'predictions.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
 print(json.dumps(results,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
