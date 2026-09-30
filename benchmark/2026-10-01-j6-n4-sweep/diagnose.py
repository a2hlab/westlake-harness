from pathlib import Path
import sys,json
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts/lab'));import lab_paths
sys.path.insert(0,str(lab_paths.harness()/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
name=sys.argv[1];serial=next(s for s in lab_paths.boards('oh') if s.startswith(name));out=HERE/name/'diagnostics';out.mkdir(exist_ok=True)
board=b.Board(serial,str(ROOT/'benchmark/2026-09-30-n3-61b/transport/hdc_mac.sh'),'mac '+str(lab_paths.tools()/'board_note.sh'),'cx-t0',out/'commands');board.ready()
remote='/data/local/tmp/j6n4-failed-hilog.txt'
board.shell('hilog -x > '+remote,timeout=60);board.receive(remote,out/'hilog.txt')
files=b.fault_files(board,out,'current')
for path in sorted(files):
 if 'helloworld' in path or 'appspawn' in path:
  board.receive(path,out/Path(path).name)
print(out,flush=True)
