"""Archive the signed promotion's real disk/loader observations, without boards."""
import csv,hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'scripts/lab'))
import installation_chain as chain, lab_paths

def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 W=lab_paths.workspaces();source=W/'westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/stageB-final/u101-t8-B1-20261002T093222'
 expected=json.loads((R/'benchmark/2026-10-02-u10-1-t8-rerun/expected-run.json').read_text())['boards'];boards={};rows=[];sources={}
 for label in ['5ea','5cd','61b']:
  signed=json.loads((source/label/'retained-final/candidate-318.json').read_text())
  assert signed['identity_assertions']==318 and not signed['diff'] and not signed['absent']
  receipt=next((source/label/'runner/smoke').rglob('installation-chain.json'))
  baseline=json.loads((receipt.parent.parent/'baseline.json').read_text());serial=baseline['serial'] if 'serial' in baseline else next(k for k in expected if k.startswith(label))
  ex={p:expected[serial]['expected'][p] for p in chain.PATHS};actual=json.loads(receipt.read_text())
  result=chain.compare_expected(ex,actual);assert result['passed']
  assert signed['fingerprints']==expected[serial]['fingerprints']
  save(H/'evidence'/f'{label}-installation-chain.json',actual)
  save(H/'evidence'/f'{label}-assertion.json',result)
  save(H/'evidence'/f'{label}-signed-318.json',signed)
  save(H/'evidence'/f'{label}-expected-services.json',{'services':ex})
  boards[serial]={'label':label,'services':ex,'runtime_fingerprint':signed['fingerprints']['runtime'],'boot_fingerprint':signed['fingerprints']['boot'],'identity_assertions':318,'unique_paths':316,'disk_assertion':'PASS','loaded_verdict':result['loaded_verdict'],'unobserved_libraries':result['unobserved_libraries']}
  for path,value in ex.items():rows.append({'board':label,'serial':serial,'path':path,'sha256':value,'disk_matches_signed':actual['disk_identities'][path]==value})
  sources[label]={'installation_chain':str(receipt).replace(str(W),'$WORKSPACES'),'installation_chain_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),'retained_identity':str(source/label/'retained-final/candidate-318.json').replace(str(W),'$WORKSPACES'),'outer_signature':str(source/label/'outer-promotion.json').replace(str(W),'$WORKSPACES')}
 cross=[{'path':p,'boards':{b['label']:b['services'][p] for b in boards.values()},'equal':len({b['services'][p] for b in boards.values()})==1} for p in chain.PATHS]
 save(H/'unified-state.json',{'state':'U10.1T8','bundle_sha256':'190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736','native_manifest_sha256':'4db327033870b597248a7188ab7f007e1979dafbb330edc58a4f052b6a086e00','installation_chain_unified':all(row['equal'] for row in cross),'boards':boards,'comparison':cross,'device_access':False,'basis':'Fresh signed Stage B readbacks; this report performs no new board observation.'})
 save(H/'source-references.json',sources)
 with (H/'comparison.csv').open('w',newline='') as out:
  w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 print('six aliases x three boards checked; exact unequal paths:',[r['path'] for r in cross if not r['equal']])
 print('all disks match their signed per-board state; libinstalls actual loader remains unknown on all three fresh controls')
if __name__=='__main__':main()
