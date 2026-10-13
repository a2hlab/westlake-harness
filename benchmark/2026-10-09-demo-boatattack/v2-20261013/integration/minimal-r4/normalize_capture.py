"""Normalize only outer's actual r4 raw capture and exact restored receipts."""
import re,json
from pathlib import Path
import prepare as p
import installer as i

def capture():
 window=p.MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/candidate-window2';result=window/'r4-readonly/result.json';raw=window/'r4-readonly/stdout.txt';d=i.read(result)
 i.need(d['rc']==0 and d['script_sha256']==i.sha(p.HERE/'capture-readonly.sh') and d['stdout_sha256']==i.sha(raw),'actual capture script/raw/rc mismatch')
 text=raw.read_text();boot=re.search(r'^BOOT_BEFORE=(.+)$',text,re.M).group(1)
 i.need(text.endswith('BOOT_AFTER='+boot+'\n') and '\nR4_ROOT=ABSENT\n' in text and '\nboot_id='+boot+'\n' in text and '\nstate=READY\n' in text and '\nlayers=56\n' in text,'same boot/READY56/absence missing')
 rows={}
 for target,h,path,mode,uid,gid,label in re.findall(r'^FILE=(\S+)\n([a-f0-9]{64})  (\S+)\nMETA=(\d+):(\d+):(\d+):([^\n]+)$',text,re.M):
  i.need(target==path and target not in rows,'capture target/duplicate');rows[target]={'target':target,'exists':True,'sha256':h,'mode':mode,'uid':int(uid),'gid':int(gid),'label':label}
 i.need(set(rows)=={p.LIBANDROID,p.RUNTIME,i.CFG},'exact three captured files')
 rbpath=window/'execution/rollback-1791862475415506000.json';rb=i.read(rbpath);i.need(rb['success'] is True and rb['baseline319_equal'] is True and rb['files_and_binds_restored'] is True,'W2 restore incomplete')
 bootpath=window/'restored-boot-result.json';b=i.read(bootpath);i.need(b['boot_id']==boot and b['ready'] is True,'restored boot mismatch')
 oldplan=i.read(p.MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/candidate-window1/plan.json');cfg=oldplan['members'][-1]['before']
 i.need(all(rows[i.CFG][k]==cfg[k] for k in ['sha256','mode','uid','gid','label']),'original cfg metadata differs')
 baseline_path=window/'r4-readonly/baseline319.json';baseline_raw=window/'r4-readonly/baseline319.stdout';baseline=i.read(baseline_path)
 i.need(baseline['rc']==0 and baseline['complete'] is True and baseline['boot_id']==boot and baseline['expected_count']==baseline['actual_count']==319 and baseline['diff']==[] and baseline['stdout_sha256']==i.sha(baseline_raw),'same-boot full319 receipt mismatch')
 lines=baseline_raw.read_text().splitlines();i.need(lines[0]==lines[-1]==boot,'full319 boot changed')
 actual={}
 for line in lines[1:-1]:
  m=re.fullmatch(r'([a-f0-9]{64})\s+(/\S+)',line);i.need(m is not None,'malformed319 row');h,target=m.groups();i.need(target not in actual,'duplicate319 row');actual[target]=h
 original_baseline=i.read(p.pinned(oldplan['baseline319']))['expected'];i.need(actual==original_baseline and len(actual)==319,'actual319 exact membership/SHA mismatch')
 link=p.MAIN/'benchmark/2026-10-10-boat-runtime-port-spec/evidence/linkfix-verification.json'
 doc={'serial':oldplan['serial'],'boot_id':boot,'runtime_before':rows[p.RUNTIME],'libandroid_before':rows[p.LIBANDROID],'cfg':rows[i.CFG],'absence':{'target':i.ROOT,'exists':False},'original_cfg_restored':True,'baseline319_equal':True,'baseline319_evidence_scope':'same-boot319 raw independently parsed, full membership/SHA equal, both boot endpoints match','runtime_closure':p.pin(link),'evidence':{'r4_absence':p.pin(raw),'runtime_metadata':p.pin(raw),'libandroid_metadata':p.pin(raw),'capture_receipt':p.pin(result),'restored_baseline':p.pin(baseline_path),'full319_raw':p.pin(baseline_raw),'prior_rollback':p.pin(rbpath),'boot_identity':p.pin(bootpath)}}
 return doc
if __name__=='__main__':print(json.dumps(capture(),indent=2))
