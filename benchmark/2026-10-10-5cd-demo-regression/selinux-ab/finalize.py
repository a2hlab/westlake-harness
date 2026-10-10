#!/usr/bin/env python3
"""Offline final report after the authorized driver has restored to Enforcing; lock disposition from receipt; no HDC."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;WS=Path(os.environ.get('WORKSPACES',HERE.parent.parents[2]))
def read(p):return json.loads(Path(p).read_text())
def portable(p):return str(Path(p).resolve()).replace(str(WS),'$WORKSPACES')
def note(s):subprocess.run([str(WS/'westlake-inputs/tools/board_note.sh'),'progress',str(WS/'westlake-harness/.octos/boards/app-lighting.md'),'91','cx-t0',s],check=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--driver-pid',type=int,required=True);a=ap.parse_args()
 for _ in range(120):
  p=subprocess.run(['ps','-p',str(a.driver_pid),'-o','command='],capture_output=True,text=True)
  if p.returncode or 'selinux-ab/driver.py' not in p.stdout:break
  time.sleep(30)
 else:raise RuntimeError('driver still active; no final report')
 result=read(a.run/'result.json')
 if not result.get('restored_enforcing') or not result.get('final319'):raise RuntimeError('restore/final not proven; no completion claim')
 subprocess.run([sys.executable,str(HERE/'readout.py'),'--run',str(a.run),'--out',str(a.out)],check=True)
 cross=WS/'westlake-harness-wiki/benchmark/2026-10-10-u13-autostart/evidence/61b-cantopen'
 evidence=[{'path':portable(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(cross.glob('window6*')) if p.is_file() and p.stat().st_size<100000]
 rows=read(a.out/'comparison.json')['keys'];summary={'enforcing_records':sum('record' in r['enforcing'] for r in rows),'permissive_records':sum('record' in r['permissive'] for r in rows),'keys_target_CANTOPEN':{m:[r['key'] for r in rows if r[m].get('target_cantopen_log_lines',0)>0] for m in ['enforcing','permissive']},'restoration':result,'cross_61b_window6':evidence,'UI_verdict':'pending_outer_review','source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [HERE/'driver.py',HERE/'batch_readonly_prep.py',HERE/'readout.py']}}
 (a.out/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 for mode in ['enforcing','permissive']:
  p=a.out/(mode+'-facts.txt');note('5cd '+mode+'整段run_facts原样:\n'+(p.read_text() if p.exists() else 'unknown: no completed record')+'\ncontact_sheet='+portable(a.out/(mode+'-contact.jpeg')))
 note('5cd 26×2 SELinux图标点击观测已收口；result restored_enforcing=true/final319=true，runtime452447a4a0ba/boot ee927db88a67，按用户新派保锁接Boat（见result.lock_retained）；未测原轮39键不续。逐键两模式CANTOPEN与首致命='+portable(a.out/'comparison.tsv')+'；完整日志定位='+portable(a.out/'comparison.json')+'；61b窗6证据路径/SHA在results.json；截图待外环签，不自报点亮。记录数='+str(summary['enforcing_records'])+'/'+str(summary['permissive_records'])+'（不等于上屏数）。')
 return 0
if __name__=='__main__':raise SystemExit(main())
