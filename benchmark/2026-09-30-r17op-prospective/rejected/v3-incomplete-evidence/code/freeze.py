#!/usr/bin/env python3
"""One-way paired forecast publication; no future run input."""
import collections,datetime,hashlib,json,shutil
from pathlib import Path
H=Path(__file__).resolve().parent
LABELS={'亮','推进','不变','unknown'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 rows=json.loads((H/'predictions.json').read_text());profiles=json.loads((H/'profiles.json').read_text());assert len(rows)==len({r['key'] for r in rows})==66
 for r in rows:
  assert len(r['apk_sha256'])==64 and r['primary_evidence'] and r['progress_checkpoint']
  assert all(r[v] in LABELS and r['reason_'+v] for v in profiles)
 out=H/'freezes/v3';out.mkdir(parents=True,exist_ok=False)
 policy={'labels':{'亮':'Own app content, including accepted loading/onboarding/upgrade pages, visible in verified capture. Survival is not sufficient.',
 '推进':'Pass the named positive checkpoint, possibly blocked later. Lit is a minimum-promise success but a distinct exact class.',
 '不变':'Still blocked by the per-key named frozen reference wall; lack of a screenshot alone is not this outcome.',
 'unknown':'Abstention: missing identity, conflicting visual state or unresolved first wall.'},
 'reference':'Per-key frozen prior_wall cites v2 or already-disclosed r17o targeted first wall. Progress is against that exact checkpoint, not an arbitrary later log.',
 'timing':'Only clicked_at strictly after this receipt. Targeted r17o observations read before freeze form a separate exposure stratum. No r17p outcome read.',
 'identity':'5ea only; original APK hash, exact selected JAR, package manifest + measured runtime projection including hwui override, installer shell/foundation readback, grant/launcher/sidecars and boot required.',
 'metrics':'Per actual JAR: exact/minimum accuracy, scored/outcome coverage, confusion, abstentions and always-unchanged baseline on the same denominator; additionally by exposure. No best-column selection.',
 'repeated_attempts':'First completed attempt per board/key/profile; resumed segments preserve provenance and report protocol changes. Controls and repeated attempts separate.',
 'unknowns':'Native/domain availability cannot be inferred from disk presence. EGL is runtime-only; r17p visual forecasts are low-confidence source-informed hypotheses.',
 'prelaunch':'Seal/Toutiao validation rejection and Subway identity failure reported separately; no clicked_at means excluded from post-click accuracy.',
 'future_changes':'Any JAR/native/batch behavior change outside these exact profiles requires a new freeze; this table is not retroactively amended.'}
 save(H/'policy.json',policy)
 for name in ['predictions.csv','predictions.json','profiles.json','results.json','policy.json']:shutil.copy2(H/name,out/name)
 shutil.copytree(H/'evidence',out/'evidence')
 for p in sorted(H.glob('*.py')):copy=out/'code'/p.name;copy.parent.mkdir(exist_ok=True);shutil.copy2(p,copy)
 stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
 for variant,profile in profiles.items():
  d=out/'variants'/variant;save(d/'profile.json',profile);save(d/'policy.json',policy)
  flat=[{**r,'forecast':r[variant],'reason':r['reason_'+variant],'prior_exposure':r[variant+'_exposure']} for r in rows]
  save(d/'predictions.json',flat);(d/'evidence').mkdir();shutil.copy2(out/'evidence/v3c-package.json',d/'evidence/v3c-package.json')
  save(d/'freeze.json',{'version':'v3-'+variant,'frozen_at':stamp,'hashes':{str(p.relative_to(d)):sha(p) for p in sorted(d.rglob('*')) if p.is_file()}})
 receipt={'version':'v3','frozen_at':stamp,'keys':66,'counts':{v:dict(collections.Counter(r[v] for r in rows)) for v in profiles},'upcoming_full_sweep_results_read':False,'r17p_outcomes_read':False,
          'hashes':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
 save(out/'freeze.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k!='hashes'},ensure_ascii=False));print('predictions.csv SHA256',sha(out/'predictions.csv'));print('freeze.json SHA256',sha(out/'freeze.json'))
if __name__=='__main__':main()
