import collections,hashlib,json,sys
from pathlib import Path
from westlake_gap.ohresolve import index_exports,resolve
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools')
import static_pipeline
version=static_pipeline.tool_version()
p=Path(sys.argv[1]);d=Path.home()/'a2hlab/static';src=Path('/Users/zhaoyue/orca/workspaces/westlake-inputs');c=json.loads((src/'corpus100.json').read_text())['apps'];audit=json.loads((p/'audit.json').read_text());assert audit['complete']
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
a=Path('/home/dspfac/a2hlab/source-closure/verify');dirs=[a/'toolchains/ohos-sdk/native/sysroot/usr/lib/aarch64-linux-ohos',a/'out/native-imports',a/'out/native-runtime'];provided,libs=index_exports(dirs);results={};deltas={};errors=[]
for key,app in c.items():
 s=json.loads((d/'scans'/f'{key}.json').read_text());o=json.loads((d/'oh'/f'{key}.json').read_text());m=json.loads((d/'maps'/key/'gap-map.json').read_text());recalc=resolve(s,provided,{})
 state=json.loads((d/'maps'/key/'pipeline-state.json').read_text())
 checks={'pipeline_fingerprint':state['fingerprint']==static_pipeline.fingerprint(app,d,version),'stage_receipts':all(state['stages'][stage]==sha(d/path) for stage,path in [('scan',f'scans/{key}.json'),('oh',f'oh/{key}.json'),('gap-map',f'maps/{key}/gap-map.json')]),'fresh_input_sha256':sha(Path(app['input']))==s['apk']['sha256'],'oh_recomputed':recalc==o['apps'][key],'all_audit_checks':all(audit['apps'][key]['checks'].values()),'output_hashes_still_current':all(sha(Path(v['path']))==v['sha256'] for v in audit['apps'][key]['outputs'].values()),'native_upcalls_available':s['inventory'].get('native_upcalls') is not None}
 results[key]=checks
 for k,v in checks.items():
  if not v and k!='native_upcalls_available':errors.append([key,k])
 old=Path.home()/'a2hlab/static-history/static-100-original/oh'/f'{key}.json'
 if old.exists():
  oldsyms={x['symbol'] for x in json.loads(old.read_text())['apps'][key]['missing']};newsyms={x['symbol'] for x in recalc['missing']}
  if oldsyms!=newsyms:deltas[key]={'removed_non_target_or_false_missing':sorted(oldsyms-newsyms),'newly_exposed_missing':sorted(newsyms-oldsyms)}
sets={sub:sorted(x.stem if sub!='maps' else x.parent.name for x in (d/sub).glob('*.json' if sub!='maps' else '*/gap-map.json')) for sub in ['scans','oh','maps']}
leader=json.loads((d/'leaderboard.json').read_text());log=(Path.home()/'a2hlab/logs/static-100-v2.log').read_text();checks={'exactly_100_apps':len(c)==100,'unique_packages':len({v['package'] for v in c.values()})==100,'unique_artifacts':len({audit['apps'][k]['artifact']['sha256'] for k in c})==100,'corpus_outputs_present':all(set(c)<=set(v) for v in sets.values()),'ignored_maps_reported':set(leader['ignored_apps'])==set(sets['maps'])-set(c),'toutiao_present_fd_k9_absent':'toutiao' in c and 'fd-k9' not in c,'leaderboard_exact_membership':set(leader['apps'])==set(c),'leaderboard_header_100':'— 100 apps' in (d/'LEADERBOARD.md').read_text().splitlines()[0],'resume_log_100_ok':log.count('ok (')==100,'resume_log_no_failure':'failed' not in log and 'excluded' not in log,'all_app_checks':not errors}
r={'scope':'static only; no board access','checks':checks,'errors':errors,'apps':results,'native_upcalls_available_apps':sum(x['native_upcalls_available'] for x in results.values()),'indexed_provider_libraries':len(libs),'output_directory_extras':{k:sorted(set(v)-set(c)) for k,v in sets.items()},'abi_filter_changed_oh_apps':len(deltas),'abi_filter_deltas':deltas,'complete':all(checks.values())}
(p/'verification.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['apps','abi_filter_deltas']},indent=1));assert r['complete']
