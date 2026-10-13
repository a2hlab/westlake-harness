from pathlib import Path
import json,sys,os,hashlib,importlib.util,subprocess,time
R=Path.cwd(); os.environ['WORKSPACES']=str(R.parent)
D=R/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/5ea-base-recovery'
spec=importlib.util.spec_from_file_location('recovery',R/'benchmark/2026-10-12-recovery-executor/executor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=json.loads((D/'plan.json').read_text()); sha=lambda x:hashlib.sha256(Path(x).read_bytes()).hexdigest()
assert sha(D/'apply.sh')==p['apply_sha256']; assert json.loads((D/'sepolicy.json').read_text())['failures']==[]
assert sys.argv[1:]==['--execute']
review=json.loads((D/'independent-review.json').read_text()); assert review['verdict']=='ACCEPT' and review['apply_sha256']==p['apply_sha256']
serial=p['serial'];board=R/'.octos/boards/app-lighting.md'; assert serial=='5ea34a4500000000000000001123012c'
held=subprocess.check_output(['bash','scripts/lab/board_note.sh','held',serial],text=True).strip();assert held.startswith('outer(codex) ')
out=D/'execution';out.mkdir();(out/'logs').mkdir()
dev=m.Device({'serial':serial,'hdc':'/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','tools':{'driver':{'path':str(R/'scripts/lab/demo_seal_61b.py')}}},out/'logs')
assert dev.shell('boot','cat /proc/sys/kernel/random/boot_id')==p['boot_id']
for n,r in enumerate(p['rows']):
 got=dev.probe(r['target']);assert m.equal(got,r['before']),(r['target'],got,r['before'])
 if r['before']['exists']:
  dev.recv('preimage-'+str(n),r['target'],out/('preimage-'+str(n)));assert sha(out/('preimage-'+str(n)))==r['before']['sha256']
 elif r['after']['exists']: assert sha(R/r['source'])==r['after']['sha256']
stage=p['staging_root'];dev.shell('stage-precheck','test ! -e '+m.q(stage)+'; test ! -L '+m.q(stage)+'; test -d /data/westlake-demo/u13/sources-boat; test ! -L /data/westlake-demo/u13/sources-boat; test ! -e /data/westlake-demo/u13/DISABLED; test ! -L /data/westlake-demo/u13/DISABLED')
# Retain exact reviewed source, user scope and boot/lock binding before first device write.
auth={'approved_by':'outer(codex)','serial':serial,'boot_id':p['boot_id'],'apply_sha256':p['apply_sha256'],'plan_sha256':sha(D/'plan.json'),'holder':held,'started_epoch':time.time(),'independent_review_sha256':sha(D/'independent-review.json'),'action':'five base control paths; preserve old Boat archive; no runtime writes; reboot separate'}
(out/'authorization.json').write_text(json.dumps(auth,indent=2)+'\n')
dev.shell('stage-create','set -eu; mkdir '+m.q(stage)+'; chown 0:0 '+m.q(stage)+'; chmod 700 '+m.q(stage)+'; chcon u:object_r:data_file:s0 '+m.q(stage))
for n,r in enumerate(p['rows']):
 meta=r['after'] if r['after']['exists'] else r['before'];name=('candidate-' if r['after']['exists'] else 'preimage-')+str(n);src=R/r['source'] if r['after']['exists'] else out/name;target=stage+'/'+name
 dev.send(name,src,target);dev.shell('stage-meta-'+str(n),'set -eu; chown 0:0 '+m.q(target)+'; chmod '+meta['mode']+' '+m.q(target)+'; chcon '+meta['label']+' '+m.q(target));assert m.equal(dev.probe(target),meta)
dev.send('stage-apply',D/'apply.sh',stage+'/apply.sh');assert dev.probe(stage+'/apply.sh')['sha256']==p['apply_sha256']
raw=dev.shell('apply-reviewed','/system/bin/sh '+m.q(stage+'/apply.sh'));assert 'BASE_CONTROLS_PLACED_RESEALED_NO_REBOOT' in raw
checks=[]
for r in p['rows']:
 got=dev.probe(r['target']);assert m.equal(got,r['after']),(r['target'],got);checks.append({'target':r['target'],'actual':got})
assert dev.shell('boot-end','cat /proc/sys/kernel/random/boot_id')==p['boot_id']
(out/'receipt.json').write_text(json.dumps({'status':'BASE_CONTROLS_PLACED_RESEALED_NO_REBOOT','boot_id':p['boot_id'],'checks':checks,'apply_sha256':p['apply_sha256']},indent=2)+'\n');print('BASE5 PASS; no reboot yet',flush=True)
