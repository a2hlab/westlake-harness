from pathlib import Path
import json,sys,shlex
R=Path(__file__).resolve().parent
REPO=R.parents[1]
sys.path.insert(0,str(REPO/'scripts/lab'))
import lab_paths
MASTER=lab_paths.harness(); W=lab_paths.workspaces(); TOOLS=lab_paths.tools()
sys.path.insert(0,str(MASTER/'benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b
SERIAL='61b0657200000000000000000324012c'
BASE=W/'westlake-generation-n2-51a78bde'
CANDIDATE=W/'westlake-generation-n3-8a7880fa'
REF=MASTER/'benchmark/2026-09-30-j3-u3-sweep/runs/j3-61b'/SERIAL
JAR='/system/android/framework/oh-adapter-runtime.jar'
JAR_SHA=next(l.split()[0] for l in (REF/'runtime-fingerprint.txt').read_text().splitlines() if l.endswith(JAR))
def board(stage):
 x=b.Board(SERIAL,str(R/'transport/hdc_mac.sh'),'mac '+shlex.quote(str(TOOLS/'board_note.sh')),'cx-t0',R/stage/'commands');x.ready();return x
