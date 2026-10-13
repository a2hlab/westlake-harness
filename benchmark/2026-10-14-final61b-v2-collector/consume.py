#!/usr/bin/env python3
"""Local binding seam for the original raw adapter and seal compiler. No board transport."""
import argparse,copy,hashlib,importlib.util,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2])))
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def need(ok,message):
 if not ok:raise ValueError(message)
def expand(p):return Path(str(p).replace('$WORKSPACES',str(WS)))
def checked(ref):
 p=expand(ref['path']);need(sha(p)==ref['sha256'],'independent input SHA differs: '+str(p));return p
def pin(p):
 p=Path(p).resolve();return {'path':'$WORKSPACES/'+str(p.relative_to(WS)) if p.is_relative_to(WS) else str(p),'sha256':sha(p)}
def module(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def consume(args):
 plan=read(HERE/'collector.readonly.disabled.json')
 need(not args.out.exists(),'fresh offline output required')
 archived=WS/'westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final61b-approved-execution'
 need(not args.out.resolve().is_relative_to(archived.resolve()),'archived approved-execution output forbidden')
 cp=args.capture/'capture.json';need(cp.is_file(),'PENDING actual collector capture.json; no snapshot or errors manufactured')
 need(sha(cp)==args.capture_sha256,'actual raw capture fullSHA differs')
 capture=read(cp);need(capture.get('synthetic') is False and capture['serial']==plan['serial'],'actual same61b collector required')
 need(capture['groups']==read(checked(plan['groups'])),'actual collector group membership differs')
 names=[a['package'] for a in read(checked(plan['manifest']))['apps'] if a.get('install') is not False]+plan['extra_packages']
 need(capture['package_names']==names and len(set(names))==130,'actual full130 package collection required')
 adapter=module(checked(plan['programs']['adapter']),'original_final_seal_adapter')
 snapshot=adapter.convert(args.capture) # Every original raw SHA, command, transport/remote marker/boot gate remains.
 need(snapshot.get('synthetic') is False and snapshot['boot_before']==snapshot['boot_after']==plan['expected_candidate_boot'],'actual snapshot boot/source binding differs')
 expected=read(HERE/'expected-files.actual-derived.json');actual={t:h for rows in snapshot['files'].values() for t,h in rows.items()}
 need(actual==expected and len(actual)==824,'actual824 SHA set differs from admitted running composition')
 packages={r['package']:r for r in snapshot['packages']};wanted={r['package']:r for r in read(HERE/'packages.expected.json')}
 need(set(packages)==set(wanted) and len(packages)==130,'actual130 package identity differs')
 for name,row in wanted.items():
  got=packages[name];need(all(str(got[k])==str(row[k]) for k in ['version_code','version_name','apk_path','apk_sha256']),'actual installed package differs: '+name)
 need(snapshot['inventories']==plan['preserved_original_inventories'],'original inventories lost/changed')
 overlays=read(HERE/'overlays.pending.json');refs={}
 for role,path,digest in [('toutiao-route-b',args.routeb_admission,args.routeb_admission_sha256),('boatattack',args.boat_admission,args.boat_admission_sha256)]:
  need(path is not None and digest is not None,'PENDING independent real outer admission: '+role)
  need(sha(path)==digest,'independent admission SHA differs: '+role);a=read(path)
  need(str(a.get('status','')).startswith('ACCEPT') and a.get('admitted') is True and a.get('approved_by')=='outer(claude)' and a.get('actual_reviewer')=='outer(codex)','real legacy-role outer admission required: '+role)
  need(a.get('serial')==plan['serial'] and a.get('boot_id')==snapshot['boot_after'] and a.get('overlay_id')==role,'admission board/boot/role differs')
  wantedrow=next(r for r in overlays['items'] if r['id']==role)
  need(a['exact_members']==wantedrow['files'] and a['source']==wantedrow['source'] and a['rollback']==wantedrow['rollback'],'admission exact members/source/rollback changed')
  need(a.get('snapshot_capture')==pin(cp),'admission not bound to actual final raw capture')
  ui=checked(a['UI_review']);checked(a['root_scoped_UI_acceptance'])
  need(a['independent_UI_review']==a['UI_review'],'actual independent UI review pin differs')
  # Existing scoped game/feed limitations are carried, not promoted to general usability.
  need(read(ui).get('boot_id')==snapshot['boot_after'],'UI review from another boot')
  refs[role]=pin(path);wantedrow['admission']=refs[role];wantedrow['admission_status']='ACTUAL_OUTER_SIGNED_EXACT_OVERLAY'
  for key in ['source','rollback']:checked(wantedrow[key])
  if role=='boatattack':
   retained=read(checked(wantedrow['rollback']))
   for ref in retained['backup_objects']:checked(ref)
 builder=module(checked(plan['programs']['build_seal']),'original_final_seal_compiler')
 seal=builder.build(snapshot,overlays,read(checked(plan['manifest'])))
 # Retain original CLI's exact provenance encoding; no signing or new observation is fabricated.
 args.out.mkdir(parents=True)
 def save(name,value):
  p=args.out/name;p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');return p
 sp=save('snapshot.actual-adapter.json',snapshot);op=save('overlays.actual-admitted.json',overlays)
 seal['provenance']['input_sha256']={'snapshot':sha(sp),'overlays':sha(op),'manifest':plan['manifest']['sha256']}
 sealed=save('seal.unsigned.v2.json',seal)
 request=read(WS/'westlake-harness/benchmark/2026-10-14-final61b-seal-command-card/request.running.final-seal.pending.json')
 request['source_identity']=dict(kind='seal',**pin(sealed));request['source_seal']=pin(sealed)
 need(request['parameters']['boot_id']==snapshot['boot_after'],'original request parameter boot differs; new raw WMS rebind required')
 save('request.running.actual.disabled.json',request)
 receipt={'status':'ACTUAL_COLLECTOR_AND_OUTER_ADMISSION_BOUND_UNSIGNED_DISABLED','device_calls':0,'execution_enabled':False,'snapshot':pin(sp),'overlays':pin(op),'seal':pin(sealed),'admissions':refs,'same61b128_review':'PENDING_SEPARATE_FINAL_SIGNOFF','V2_signed':False}
 save('binding.json',receipt);return receipt

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True);p.add_argument('--capture-sha256',required=True);p.add_argument('--routeb-admission',type=Path);p.add_argument('--routeb-admission-sha256');p.add_argument('--boat-admission',type=Path);p.add_argument('--boat-admission-sha256');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:print(json.dumps(consume(a)));return 0
 except (ValueError,TypeError,KeyError,OSError) as e:print('REFUSED: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
