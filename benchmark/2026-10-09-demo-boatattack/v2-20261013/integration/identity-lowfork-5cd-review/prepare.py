#!/usr/bin/env python3
"""Offline exact5cd metadata inventory from real placement and readback receipts."""
import hashlib,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').is_file() and (p/'scripts/lab/lab_paths.py').is_file())
WS=Path(os.environ.get('WORKSPACES',str(ROOT.parent))).resolve();MAIN=WS/'westlake-harness';B=Path('benchmark/2026-10-09-demo-boatattack/v2-20261013');STAGE=MAIN/B/'outer/routeb-fresh-boat-stage';META=('mode','uid','gid','label')
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pin(p):return dict(path='$WORKSPACES/'+str(p.resolve().relative_to(WS)),sha256=sha(p))
def resolve(s):return Path(s.replace('$WORKSPACES',str(WS)))
def save(n,d):(HERE/n).write_text(json.dumps(d,indent=2)+'\n')
def main():
 planpath=STAGE/'plan.enabled.json';plan=read(planpath);serial='5cd1e3dd00000000000000000923012c';boot='c9436daa-b3ca-44dc-985f-9ee03445567a'
 assert plan['serial']==serial and plan['boat_uid']==20011301 and plan.get('synthetic') is False
 tx=STAGE/'staged/boat/transaction';receipt=read(STAGE/'staged/boat/receipt.json');assert receipt['executor_rc']==0 and receipt['plan_sha256']==sha(planpath)
 preserved=read(tx/'preserved-verified.json');assert preserved['success'] and preserved['count']==496 and preserved['plan_sha256']==sha(planpath)
 cap=resolve(plan['capture']['path']);assert sha(cap)==plan['capture']['sha256'];capture=read(cap);assert capture['complete'] and capture['serial']==serial
 files={r['target']:{k:r['before'][k] for k in META} for r in plan['preserved']}
 expected={r['target']:r['before']['sha256'] for r in plan['preserved']}
 provenance={r['target']:{'kind':'actual5cd-preserved-preimage-with-postplacement-verification','capture':pin(cap),'verified':pin(tx/'preserved-verified.json')} for r in plan['preserved']}
 for i,r in enumerate(plan['members']):
  placed=read(tx/('placed-%03d.json'%i));assert placed['target']==r['target'] and placed['sha256']==r['sha256']
  provenance[r['target']]={'kind':'actual5cd-placed-after-metadata','plan':pin(planpath),'placed':pin(tx/('placed-%03d.json'%i))}
 for r in plan['members']+plan['binds']:files[r['target']]={k:r['after'][k] for k in META};expected[r['target']]=r['sha256']
 for r in plan['binds']:
  source=next(m for m in plan['members'] if m['target']==r['source']);assert source['sha256']==r['sha256'] and source['after']==r['after'];provenance[r['target']]={'kind':'actual7bind-source-inode-metadata','source':r['source'],'plan':pin(planpath)}
 directories={r['target']:r['after'] for r in plan['directory_prerequisites']+plan['directories']}
 for r in plan['directory_prerequisites']:assert capture['route_b_directories'][r['target']]==r['after'] and r['after']['uid']==20011300
 for i,r in enumerate(plan['directories']):
  created=read(tx/('directory-created-%03d.json'%i));assert created['target']==r['target'] and created['after']==r['after'] and created['plan_sha256']==sha(planpath)
 livepath=STAGE/'final-selfcheck954.json';live=read(livepath);assert live['status']=='PASS' and live['synthetic'] is False and live['boot_before']==live['boot_after']==live['current_boot']==boot
 actual={r['target']:r['actual'] for r in live['checks']};assert all(actual[t]==h for t,h in expected.items())
 assert len(files)==507 and len(directories)==5 and len(provenance)==507
 original=MAIN/B/'integration/final-v2-identity-f28-61b/presence_reader.py';fivecd=MAIN/B/'integration/final-v2-identity-f28-5cd/presence_reader.py';assert sha(original)==sha(fivecd)=='7059cc45215f3f260402763fb6e8ac24994a3913614d6c6d635335f61df898f6'
 new=MAIN/'benchmark/2026-10-14-identity-lowfork-candidate/presence_reader_lowfork.py';assert sha(new)=='9ab15ecd7aa7fd3d2877399f171b231f49753f967254e6075ecb07360e9b85e5'
 pins={'original':pin(original),'original_5cd_equal':pin(fivecd),'candidate':pin(new),'reader':pin(MAIN/'benchmark/2026-10-09-demo-baseline/t3/verify_identity.py'),'transport':pin(WS/'westlake-inputs/tools/hdc_mac.sh'),'lock':pin(MAIN/'scripts/lab/board_note.sh'),'placement_plan':pin(planpath),'composition':live['composition'],'actual954':pin(livepath),'capture':pin(cap),'preserved496':pin(tx/'preserved-verified.json')}
 doc={'schema':'metadata-ab-readonly/v1','execution_enabled':False,'serial':serial,'boot_id':boot,'boat_uid':20011301,'routeb_uid':20011300,'max_seconds':1200,'pins':pins,'files':files,'directories':directories,'candidate_sha256':{r['target']:r['sha256'] for r in plan['members']+plan['binds']},'scope':'metadata507+5 only; no full128 gate replacement','currentboot_complete512_metadata_observed':False,'currentboot_gap':'Archived currentboot954 checks bytes, not a single512 metadata capture. Original phase will freshly verify every expected value; any mismatch aborts comparison.'}
 save('plan.disabled.json',doc);save('metadata-provenance.json',{'files':provenance,'three_routeb_directories':{'capture':pin(cap),'metadata':capture['route_b_directories']},'two_boat_directories':[pin(tx/('directory-created-%03d.json'%i)) for i in range(2)],'source_serial':serial,'placement_boot':plan['boot_id'],'current_boot':boot,'device_calls':0})
 print(json.dumps({'status':'PREPARED_DISABLED','files':507,'directories':5,'serial':serial,'device_calls':0,'plan_sha256':sha(HERE/'plan.disabled.json')}))
if __name__=='__main__':main()
