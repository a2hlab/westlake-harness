"""Local existing-evidence closure only; no subprocess or device transport."""
from pathlib import Path
import hashlib,json

HERE=Path(__file__).resolve().parent
WS=HERE.parents[2]
MAIN=WS/'westlake-harness'
RUN=MAIN/'benchmark/2026-10-12-v1-seal-execution'
FINAL=RUN/'seal-final-20261013'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
pins=[]
def verify(ref,base):
 path=Path(ref['path'].replace('$WORKSPACES',str(WS)))
 if not path.is_absolute():path=base/path
 assert path.is_file(),str(path)
 assert sha(path)==ref['sha256'],str(path)+' hash mismatch'
 pins.append({'path':'$WORKSPACES/'+str(path.resolve().relative_to(WS)),'sha256':sha(path)})
 return path

expected={'seal.json':'7f5b6f996482149ffd958bcdf55981cdc8ac6e69cb17738a2984153421f72780',
 'realization-61b/realization.json':'a8fc256f2eb3ec7ca29924e2cdb93720505b6de2101efe5d4d53cb46953bcc75',
 'appendix-5cd/appendix.json':'bcac2341d904aa8e43cfc80aa053f12451cfe34c1d19189d64c9668cb424846a',
 'activation-binding.5cd.json':'c151abb82d8ca127010e0ad93fd9cbb79b1b71ac31465d46bc1667a481df7869'}
for name,value in expected.items():verify({'path':str(FINAL/name),'sha256':value},FINAL)
seal=read(FINAL/'seal.json');proof=read(FINAL/'realization-61b/realization.json')
assert seal['seal_stage']=='v1' and len(seal['packages'])==129
flat={k:v for g in seal['files'].values() for k,v in g.items()};assert len(flat)==sum(map(len,seal['files'].values()))==811
assert {r['target']:r['sha256'] for r in proof['files']}==flat
verify(proof['source_seal'],FINAL);verify(proof['source_identity'],FINAL)
source=read(FINAL/'source-running-r5/observation.json')
assert source['synthetic'] is False and source['boot_before']==source['boot_after']==proof['parameters']['boot_id']
verify(proof['parameter_evidence']['observation'],FINAL)
verify(proof['request'],FINAL)
sourcedir=FINAL/'source-running-r5'
for ref in source['readings'].values():
 assert ref['transport_rc']==ref['remote_rc']==0
 verify(ref['stdout'],sourcedir)
sa=read(sourcedir/'006-host_cmdline.binary.json')
assert sa['accepted'] is True and sa['logical_command']==source['readings']['host_cmdline']['command']
assert b'\0' in (sourcedir/sa['decoded_stdout']['path']).read_bytes()
assert sha(sourcedir/sa['decoded_stdout']['path'])==sa['board_sha256']
for ref in [sa['encoded_stdout'],sa['decoded_stdout'],sa['adapter']]:verify(ref,sourcedir)
assert read(sourcedir/'006-host_cmdline.json')['argv']==sa['actual_argv']
for p in ['generator','observation_validator','sameboard_generator']:
 if proof.get(p):verify(proof[p],FINAL)

board_results={}
for tag,boot in [('61b','9f5af7c8-d359-4c25-99c6-63206b50cf0a'),('5cd','8d0f7543-2352-4d9b-a7ce-e3b5d0ba12a5')]:
 receipt=read(FINAL/f'selfcheck-{tag}-r5.json')
 assert receipt['status']=='PASS' and receipt['passed'] is True and receipt['mode']=='live-readonly' and receipt['synthetic'] is False
 assert receipt['current_boot']==receipt['boot_before']==receipt['boot_after']==boot
 assert receipt['file_count']==len(receipt['checks'])==940
 assert len({c['target'] for c in receipt['checks']})==940
 assert all(c['equal'] is True and c['expected']==c['actual'] for c in receipt['checks'])
 assert receipt['remote_write_operations']==receipt['lock_operations']==0
 dynamic=receipt['dynamic_receipt'];assert dynamic['current_boot']==boot
 verify(dynamic['source_seal'],FINAL);verify(dynamic['source_identity'],FINAL)
 obsdir=FINAL/f'selfcheck-{tag}-r5.json.evidence'
 liveobs=read(obsdir/'observation.json')
 assert liveobs['synthetic'] is False and liveobs['errors']==[]
 assert liveobs['boot_before']==liveobs['boot_after']==boot
 assert liveobs['files']=={c['target']:c['actual'] for c in receipt['checks']}
 assert all(c['transport_rc']==c['remote_rc']==0 for c in liveobs['commands'])
 pe=dynamic['parameter_evidence'];assert pe['boot_id']==boot and pe['serial']==receipt['serial']
 verify(pe['observation'],obsdir)
 for ref in pe['readings'].values():
  assert ref['transport_rc']==ref['remote_rc']==0;verify(ref['stdout'],obsdir)
 cmd=pe['readings']['host_cmdline'];decoded=obsdir/cmd['stdout']['path'];assert b'\0' in decoded.read_bytes()
 audit=read(obsdir/'006-host_cmdline.binary.json')
 assert audit['accepted'] is True and audit['board_sha256']==sha(decoded)
 assert audit['logical_command']==cmd['command']
 verify(audit['encoded_stdout'],obsdir);verify(audit['decoded_stdout'],obsdir);verify(audit['adapter'],obsdir)
 original=read(obsdir/'006-host_cmdline.json')
 assert original['argv']==audit['actual_argv'] and original['command']==audit['encoded_command']
 if tag=='61b':verify(receipt['realization'],FINAL);verify(receipt['observation'],FINAL)
 else:
  activation=receipt['activation'];verify(activation['binding'],FINAL);verify(activation['origin_realization'],FINAL);verify(activation['realization'],FINAL);verify(activation['appendix']['pin'],FINAL)
  assert receipt['synthetic_transaction_recordings'] is False
 board_results[tag]={'boot':boot,'file_count':940,'mismatches':0,'host_uid':pe['host_uid'],'host_pid':pe['host_pid'],'window_id':pe['window_id'],'receipt_sha256':sha(FINAL/f'selfcheck-{tag}-r5.json'),'cmdline_decoded_sha256':sha(decoded)}

binding=read(FINAL/'activation-binding.5cd.json')
assert binding['synthetic'] is False
for key in ['realization','origin_realization','prepared_manifest','admission','restore_adapter','execution_receipt','transaction','placed','appendix']:verify(binding[key],FINAL)
for row in binding['member_receipts']:verify(row,FINAL)
assert len(binding['member_receipts'])==487
appendix=read(FINAL/'appendix-5cd/appendix.json')
verify(appendix['source_seal'],FINAL/'appendix-5cd');verify(appendix['candidate_realization'],FINAL/'appendix-5cd');verify(appendix['sealed_realization'],FINAL/'appendix-5cd')
assert len(appendix['additional_static_targets'])==5 and len(appendix['complete_target_sha256'])==811
assert appendix['signed_by'] is None

recipe=read(RUN/'r4b-completed-restore/recipe-receipt.json')
assert recipe['executor_rc']==0 and recipe['complete'] is True and recipe['manual_app_start'] is False
assert sha(RUN/'r4b-admission-r2/recipe.json')==recipe['recipe_sha256']
assert read(RUN/'r4b-admission-r2/execution-exit.json')['exit']==0
argv=read(RUN/'r4b-admission-r2/execution-command.json')
assert argv[argv.index('--recipe-sha256')+1]==recipe['recipe_sha256'] and argv[-1]=='--execute'
assert sha(RUN/'r4b-completed-restore/directory-transaction/applied.json')==recipe['directory_receipt_sha256']
ready=read(RUN/'5cd-r4b-postboot-ready/ready.json')
assert ready['boot_id']==board_results['5cd']['boot']==ready['receipt']['boot_id']
assert ready['receipt']['state']=='READY' and ready['mounted_table_targets']==56 and ready['autonomous'] is True
assert ready['manual_runtime_repair'] is False and ready['selinux']=='Permissive'
for name in ['5cd-r4b-toutiao','5cd-r4b-consent']:
 rec=read(FINAL/name/'record.json');assert rec['boot_id']==ready['boot_id'] and rec['automatic_consent'] is False
 for im in rec['screenshots']:verify(im,FINAL/name)
state=(RUN/'5cd-r4b-route-state/001-state.stdout').read_text()
assert 'WAITING_FOR_USER_CONSENT' in state and 'privacy_no_touch' in state and 'HOST_SPAWN result=0 pid=7216' in state

driver=RUN/'tools/demo_seal_61b.py';text=driver.read_text()
assert "1 <= len(keys) <= 128" in text
assert "keys == expected_keys" in text and "set(keys) <= set(signoff.get('verdicts', {}))" in text
scope=read(RUN/'window-plan.disabled.json');verify(scope['inputs']['legacy_driver'],MAIN);verify(scope['inputs']['regression_manifest'],MAIN)
manifest=read(RUN/'inputs/demo-manifest-20.json');assert len(manifest['apps'])==20
assert 'new 61b 20 keys plus existing 5cd full128 cross-validation'==scope['regression_scope']
verdict=read(RUN/'regression-review-final/outer-verdict.json');assert {r['key'] for r in verdict['rows']}=={r['key'] for r in manifest['apps']}

result={'status':'ACCEPT_BOUNDARY_NOT_SEAL_SIGNATURE','blocking_items':[],
 'artifact_sha256':expected,'board_selfchecks':board_results,'source_reference_count_verified':len(pins),
 'restore_history_member_receipts_verified':487,'r4b_recipe_rc':0,'scope':'Plan2: current61b20 plus historical5cd128; installed identity940 is not940 app executions',
 'driver_sha256':sha(driver),'privacy':'5cd feed is visibly behind privacy dialog; user manual choice pending. No5cd refresh/article acceptance.',
 'role_signature':'root alone signs literal outer(claude); reviewer does not sign',
 'source_pins':pins}
(HERE/'results.json').write_text(json.dumps(result,indent=2)+'\n')
print('ACCEPT_BOUNDARY: seal/proof/appendix/binding exact; source+selfchecks boots stable; 940/940 each,487 receipts pinned; r4b rc0; Plan2 driver subset; privacy pending, no seal signature')
print('PIN_READS',len(pins))
