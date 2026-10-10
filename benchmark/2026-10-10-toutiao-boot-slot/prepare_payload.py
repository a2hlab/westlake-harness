#!/usr/bin/env python3
"""Prepare an inactive local Route B slot; no HDC, SSH, service or board writes."""
import argparse,hashlib,json,shutil,tarfile
from pathlib import Path
D=Path(__file__).parent
INPUTS={
 'source-host.hap':'df3856387ba6971202b33e4475fde4e0fb1bf7fb33da0f4250429fe6535b014a',
 'tt-rt.tar':'014c566e3813109e680c1361d6054adb181a7e3e9fb80d13d682faa161da847f',
 'tt-stage.tar':'6b4c9528abadfc946c2ac92d37f752a71a35f7ee2b38caf4c2ddc858263a3382',
 'tt-wd.tar':'16a72b27c0bd12b4dd43f9456aa44284e602b7a902ac5a9b17262b87a0741aad'}
ROOT='/data/westlake-demo/toutiao'; F='/data/local/tmp/operator45/selfheal48';RT='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--inputs',type=Path,default=Path.home()/'a2hlab-provision/ttbundle');a.add_argument('--out',type=Path,required=True);args=a.parse_args()
 assert not args.out.exists(),'fresh local output required'
 rows=[]
 for name,digest in INPUTS.items():
  p=args.inputs/name;assert sha(p)==digest,'input SHA mismatch: '+name
  rows.append({'input':name,'sha256':digest,'size':p.stat().st_size,'board_archive':'/data/local/tmp/tt-prov/'+name})
 args.out.mkdir(parents=True);files=[]
 for src in (D/'payload/scripts').glob('*.sh'):
  dest=args.out/'data/scripts'/src.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
  files.append({'source':str(dest.relative_to(args.out)),'target':ROOT+'/scripts/'+src.name,'sha256':sha(dest),'mode':'0550'})
 cfg=D/'payload/init/01_westlake_u13_toutiao.cfg.disabled';shutil.copyfile(cfg,args.out/cfg.name)
 files.append({'source':cfg.name,'target':'/system/etc/init/'+cfg.name,'sha256':sha(cfg),'mode':'0550','inactive':True})
 # Proven donor binary; never synthesize its classifier or alter the watchdog UI logic.
 with tarfile.open(args.inputs/'tt-wd.tar') as tar:
  selected=[m for m in tar if m.isfile() and Path(m.name).name=='screen-gate']
  assert len(selected)==1,'screen-gate archive identity ambiguous'
  p=args.out/'screen-gate';p.write_bytes(tar.extractfile(selected[0]).read());files.append({'source':p.name,'target':F+'/screen-gate','sha256':sha(p),'mode':'0550'})
 # Donor watchdog calls its original fixed paths; copy these three verbatim support scripts there.
 for name in ['start-parent.sh','spawn.sh']:
  p=args.out/'data/scripts'/name;files.append({'source':str(p.relative_to(args.out)),'target':F+'/'+name,'sha256':sha(p),'mode':'0550'})
 # The on-board /system/etc entry is exactly the staged worker, not a second implementation.
 p=args.out/'data/scripts/westlake-u13-toutiao-overlay.sh';files.append({'source':str(p.relative_to(args.out)),'target':'/system/etc/westlake-u13-toutiao-overlay.sh','sha256':sha(p),'mode':'0550'})
 immutable=[(r['sha256'],r['target']) for r in files if not r.get('inactive')]
 immutable.extend((r['sha256'],r['board_archive']) for r in rows)
 immutable.append(('a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c',RT+'/appspawn-x'))
 (args.out/'immutable.tsv').write_text(''.join(h+' '+p+'\n' for h,p in immutable))
 report={'schema':'toutiao-boot-slot/v1','execution_enabled':False,'board_serial':'61b0657200000000000000000324012c','source_inputs':rows,'placements':files,'immutable_tsv_sha256':sha(args.out/'immutable.tsv'),'runtime_run_template':'data/scripts/run.sh','precondition':'one-time Route B SAFE provisioning complete; exact host UID 20010053; U13 operational; disabled legacy cfg unchanged','cfg_activation':'outer-approved future init placement only; no cfg enable command generated'}
 (args.out/'placement.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'prepared':True,'execution_enabled':False,'input_shas':{r['input']:r['sha256'] for r in rows},'files':len(files),'placement_sha256':sha(args.out/'placement.json')},indent=2))
if __name__=='__main__':main()
