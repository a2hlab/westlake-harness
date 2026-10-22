#!/usr/bin/env python3
"""Compare a snapshot dir against fixed expectations. mode: baseline (preflight / after R4) or report-only."""
import sys,json,hashlib,re
from pathlib import Path
home=Path.home()/'.local/share/westlake'
d=Path(sys.argv[1]); mode=sys.argv[2]
def rd(n): return (d/f'{n}.stdout').read_text()
p2=(home/'t46p2-member-inputs-20261022/raw/pre_stat.stdout').read_text().strip().split('\n')
t44=home/'t44-verified-desktop-observation-20261022/raw/02-pre'
out={}; probs=[]
def chk(k,ok,detail=''):
    out[k]=bool(ok)
    if not ok: probs.append(f'{k}: {detail}')
ctrl=rd('ctrl').strip().split('\n'); mem=rd('members').strip().split('\n')
shaline=lambda L:[l for l in L if re.match(r'^[0-9a-f]{64} ',l)]
nomtime=lambda L:[re.sub(r' (dev|ino|mtime)=\d+','',l) for l in L]
if mode=='baseline-exact':
    chk('ctrl9_exact_T46P2',ctrl==p2[:18],'ctrl drift'); chk('members9_exact_T46P2',mem==p2[18:],'member drift')
else:
    chk('ctrl9_sha_mode_owner_T46P2',nomtime(ctrl)==nomtime(p2[:18]),'ctrl sha/mode/owner drift'); chk('members9_exact_T46P2',mem==p2[18:],'member drift')
lz=rd('lsZ'); chk('six_files_and_root_dirs_label_data_file',sum(1 for l in lz.splitlines() if l.startswith('u:object_r:data_file:s0'))==9 and 'u:object_r:data_local_tmp:s0 /data/local/tmp' in lz,lz[-300:])
rc=rd('ready_chain'); chk('ready_chain_sha','897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762' in rc and '291451a1a3b821a5527e3c8619d932664d047e25116e9c653d185d2ea5ee878f' in rc,rc[:200])
out['ready_param']=rc.strip().split('\n')[-1].strip()
chk('runtime124',rd('fp')==(t44/'fp_manifest.stdout').read_text() and rd('fp').count('\n')==124,'fp drift')
chk('boot36',rd('bi')==(t44/'bi_manifest.stdout').read_text(),'bi drift')
chk('stops_absent',all(l.startswith('ABSENT') for l in rd('stops').strip().split('\n')),rd('stops'))
h=rd('host'); chk('host_hap_b189','b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0' in h,h[:120])
chk('datadir_ino','ino=152607' in h and 'ino=153780' in h and 'uid=20011300' in h,h)
t=rd('bm'); j=json.loads(t[t.find('{'):]); ai=j['applicationInfo']; chk('bundle_identity',(ai['uid'],ai['accessTokenId'],ai['versionCode'],ai['appProvisionType'])==(20011300,537137511,2,'release'),str(ai.get('uid')))
pw=rd('power'); out['power']=pw.strip().split('\n')[-1].strip()
if mode!='report': chk('power_10000_10000','Timeout=10000ms  OverrideTimeout=10000ms' in pw,pw)
pa=rd('parents'); chk('stage_backup_new_absent','EXISTS' not in pa,pa)
out['parents']=[l for l in pa.splitlines() if l.startswith('/')]
out['boots_list']=rd('boots').split(); out['boot_id']=rd('bootid').split()[0]
out['problems']=probs
json.dump(out,open(d/'admission.json','w'),indent=1); print(json.dumps({k:v for k,v in out.items() if k not in('boots_list','parents')})[:900])
