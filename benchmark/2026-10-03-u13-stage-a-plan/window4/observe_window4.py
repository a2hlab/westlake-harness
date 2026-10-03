"""Record shard selftests; conditional one-key capture uses approved launch fallback."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
H=Path(__file__).resolve().parent;W=H.parents[3];sys.path.insert(0,str(H.parent))
import observe
p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--plan',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--cutoff',type=float,required=True);a=p.parse_args()
plan=json.loads(a.plan.read_text())
key='cv2-org-secuso-privacyfriendlyminesweeper'
missing=[r for r in a.root.glob('*/*/*/*/record.json') if r.parent.name==key and json.loads(r.read_text()).get('error')=='exact desktop icon absent across searched pages']
if missing and time.time()<a.cutoff:
 shard=next(s for s in plan['shards'] if 'apps-v2' in s['manifest']);out=a.root/'additional'/key;out.parent.mkdir(parents=True,exist_ok=True)
 cmd=['orb','-m','a2hlab','env','WORKSPACES='+str(W),'MAC_HOME='+str(Path.home()),'python3',str(H/'capture_minesweeper.py'),'--execute','--serial',plan['serial'],'--lane',plan['lane'],'--manifest',observe.expand(shard['manifest']),'--input-root',observe.expand(shard['input_root']),'--keys',key,'--reinstall','--wait','25','--hilog','20','--shots','5,20','--out',str(out),'--hdc-cmd',str(W/'westlake-inputs/tools/hdc_mac.sh'),'--lock-cmd','mac '+str(W/'westlake-inputs/tools/board_note.sh'),'--stop-new-keys-at',str(a.cutoff)]
 with (out.parent/'minesweeper-fallback.log').open('w') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
 observe.assess(plan,out,a.root/'selftest/minesweeper-fallback.json','minesweeper-ability-fallback')
 (out.parent/'minesweeper-fallback-result.json').write_text(json.dumps({'rc':rc,'trigger_record':str(missing[0]),'launch_method':'ability-fallback','out':str(out)},indent=2)+'\n')
 observe.ack(plan,'Minesweeper conditional ability-fallback completed rc='+str(rc)+'; out='+str(out)+'; screenshots are outer-reviewed, ordinary launch failure preserved')
 wrapped=any(json.loads(r.read_text()).get('finished_at') for r in out.glob('*/*/*/record.json'))
 if rc!=0 and not (rc==1 and wrapped):raise SystemExit(rc or 1)
# Capture infrastructure failure propagates; unconditional parent finish remains intact.
