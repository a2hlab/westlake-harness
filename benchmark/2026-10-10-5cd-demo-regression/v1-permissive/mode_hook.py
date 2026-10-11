#!/usr/bin/env python3
"""Authorized runtime mode only; existing U13 identity gates bracket each batch.
No reboot, deployment, installation, persistent configuration or Boat overlay.
"""
import argparse,json,os,subprocess,sys,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
WS=Path(os.environ.get('WORKSPACES',REPO.parent))
BASE=REPO/'benchmark/2026-10-09-demo-baseline'
SERIAL='5cd1e3dd00000000000000000923012c'
BOOT='a565a760-c10e-4ad4-80cd-23cd98165b28'
NOTE=WS/'westlake-inputs/tools/board_note.sh'
BOARD=WS/'westlake-harness/.octos/boards/app-lighting.md'
HDC=Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc')
def shell(command,out,tag):
 marker='__V1_RC_'+uuid.uuid4().hex+'__'
 r=subprocess.run([str(HDC),'-t',SERIAL,'shell',command+'; x=$?; printf "\\n'+marker+'%s\\n" "$x"'],capture_output=True,text=True,timeout=45)
 (out/(tag+'.txt')).write_text(r.stdout+r.stderr)
 import re
 m=re.search(marker+r'(\d+)\s*$',r.stdout)
 assert r.returncode==0 and m and m.group(1)=='0','HDC/status failure: '+tag
 return r.stdout[:m.start()].strip()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--round',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--phase',choices=['apply','finish'],required=True);a=ap.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 held=subprocess.check_output([str(NOTE),'held',SERIAL],text=True);assert 'cx-t0' in held;(a.out/'held.txt').write_text(held)
 assert shell('cat /proc/sys/kernel/random/boot_id',a.out,'boot')==BOOT,'unexpected reboot: refuse automatic continuation'
 if a.phase=='apply':
  subprocess.run([sys.executable,str(BASE/'t4/round_identity.py'),'--round',str(a.round),'--out',str(a.out/'identity')],check=True)
  assert shell('cat /sys/fs/selinux/enforce',a.out,'initial-mode')=='1'
 shell('setenforce '+('0' if a.phase=='apply' else '1'),a.out,'set-mode')
 expected='0' if a.phase=='apply' else '1'
 assert shell('cat /sys/fs/selinux/enforce',a.out,'read-mode')==expected
 if a.phase=='finish':
  subprocess.run([sys.executable,str(BASE/'t4/round_identity.py'),'--round',str(a.round),'--out',str(a.out/'identity')],check=True)
 result={'phase':a.phase,'serial':SERIAL,'boot_id':BOOT,'enforce':expected,'identity_paths':319,'runtime':'452447a4a0ba','boot':'ee927db88a67'}
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
 subprocess.run([str(NOTE),'progress',str(BOARD),'91','cx-t0','5cd v1预跑 '+a.phase+'：运行时enforce='+expected+'读回，319 diff{}、452447a4a0ba/ee927db88a67、同boot a565a760；无Boat/换件/重装/重启。'],check=True)
if __name__=='__main__':main()
