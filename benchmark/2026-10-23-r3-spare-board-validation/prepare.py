#!/usr/bin/env python3
"""Offline init plan and promotion assertions. No device executor or promotion writer."""
import argparse,hashlib,json,difflib,stat
from pathlib import Path
OLD='/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012'
NEW='/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261023-5cd-r3'
INIT='/system/etc/init/01_westlake_u13_toutiao.cfg'
PIN='19d0201b59a6edac821feffa5f51ca8e9a08d6ba87d5bc9fd15b4e4d00775152'
SERIAL='5cd1e3dd00000000000000000923012c'
def sha(b):return hashlib.sha256(b).hexdigest()
def regular(p):
 p=Path(p).absolute()
 if '..' in p.parts:raise ValueError('path traversal')
 for x in [p,*p.parents]:
  if x.is_symlink():raise ValueError('symlink '+x.name)
 if not stat.S_ISREG(p.stat().st_mode):raise ValueError('not regular file')
 return p.read_bytes()
def derive_init(before):
 if sha(before)!=PIN:raise ValueError('init preimage SHA')
 a=json.loads(before);service=[x for x in a['services'] if x['name']=='westlake-u13-toutiao-overlay']
 if len(service)!=1 or service[0]['path']!=['/system/bin/sh',OLD+'/boot-entry.sh']:raise ValueError('service identity')
 old=(OLD+'/boot-entry.sh').encode();new=(NEW+'/boot-entry.sh').encode()
 if before.count(old)!=1:raise ValueError('nonunique argv bytes')
 after=before.replace(old,new,1);expected=json.loads(before)
 next(x for x in expected['services'] if x['name']=='westlake-u13-toutiao-overlay')['path'][1]=NEW+'/boot-entry.sh'
 if json.loads(after)!=expected:raise ValueError('extra init structure change')
 return after

def allowed_promotion(before,after):
 # Byte-exact two-field transformation; no shell evaluation.
 pairs=[(b"STARTUP_ENABLED='0'",b"STARTUP_ENABLED='1'"),(b"STARTUP_APPROVED_BY='DISABLED-PENDING-OUTER'",b"STARTUP_APPROVED_BY='outer(codex)'")]
 expected=before
 for old,new in pairs:
  if before.splitlines().count(old)!=1:raise ValueError('promotion preimage field')
  expected=expected.replace(old,new,1)
 if after!=expected:raise ValueError('promotion changes outside two fields')
 return (sha(after)+'\n').encode()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--t120',type=Path,required=True);ap.add_argument('--cfg-receipt',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 raw=regular(a.cfg_receipt);marker=b'---CFG\n'
 if raw.count(marker)!=1:raise ValueError('cfg marker')
 before=raw.split(marker,1)[1];after=derive_init(before)
 (a.out/'init.before.cfg').write_bytes(before);(a.out/'init.after.cfg').write_bytes(after);(a.out/'init.rollback.cfg').write_bytes(before)
 (a.out/'init.diff').write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='init.before.cfg',tofile='init.after.cfg')))
 output=json.loads(regular(a.t120/'output-manifest.json'));payload=a.t120/'package/payload'
 if len(output)!=22:raise ValueError('payload count')
 for rel,pin in output.items():
  p=Path(rel)
  if len(p.parts)!=2 or p.parts[0]!='payload' or p.name in ['.','..']:raise ValueError('manifest path')
  if sha(regular(a.t120/'package'/p))!=pin:raise ValueError('T120 member drift '+p.name)
 modes={}
 for line in regular(payload/'members.tsv').decode().splitlines():
  pin,name,mode=line.split()
  if output['payload/'+name]!=pin or mode not in ['550','440']:raise ValueError('members binding')
  modes[name]=mode
 modes.update({'boot-entry.sh':'550','startup.env':'440','startup.expected.sha256':'440','members.tsv':'440'})
 planned=[{'name':n,'target':NEW+'/'+n,'mode':m,'owner':'0:0','disabled_sha256':output['payload/'+n],'promoted_sha256':'PENDING_T120_PEER_ACCEPTANCE' if n in ['startup.env','startup.expected.sha256'] else output['payload/'+n]} for n,m in sorted(modes.items())]
 plan={'status':'OFFLINE_PREPARATION_ONLY_PROMOTION_PENDING','device_execution_enabled':False,'serial_whitelist':[SERIAL],'parent_output_manifest_sha256':sha(regular(a.t120/'output-manifest.json')),'raw_cfg_sha256':sha(raw),'init_before_sha256':sha(before),'init_after_sha256':sha(after),'rollback_sha256':sha(before),'init_mode':'550','init_owner':'0:0','init_change':{'service':'westlake-u13-toutiao-overlay','index':1,'before':OLD+'/boot-entry.sh','after':NEW+'/boot-entry.sh'},'payload_plan':planned,'excluded_from_install':['payload/recovery.cfg','payload/rollback-inert.cfg'],'promotion_gate':'Wait for T120 peer result binding the actual parent manifest; no promotion bytes written by this tool. Only enabled/approved lines and expected digest may change.','commands_disabled':{'upload_init':['$HDC','-t',SERIAL,'file','send','$PREP/init.after.cfg','$REVIEWED_STAGING/init.after.cfg'],'upload_exact_rollback':['$HDC','-t',SERIAL,'file','send','$PREP/init.rollback.cfg','$REVIEWED_STAGING/init.rollback.cfg'],'verify_init':['$HDC','-t',SERIAL,'shell','sha256sum '+INIT],'reboot':['$HDC','-t',SERIAL,'shell','reboot']},'not_yet_executable':['Promotion SHA pending peer acceptance','Fresh held/boot/init/root/host/network and target absence checks required under CC lock','Staging path/actual mount reseal and atomic init install commands must be bound to existing approved CC deployment method; no invented remount command','Fresh power values and final restoration receipts required; 15min total with last3min reserved rollback'],'rollback_contract':{'bytes':'init.rollback.cfg','expected_sha256':PIN,'original_root':OLD,'preserve_original_root':True,'no_generated_cfg':True,'after_restore':'software reboot to original ROOT, read back identity/power, release lock; no repeated deployment trial'},'actions':{'device':0,'promotion_written':False,'controller_execution':0}}
 (a.out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({'status':plan['status'],'init_before':sha(before),'init_after':sha(after),'payload_install_entries':len(planned)}))
if __name__=='__main__':main()
