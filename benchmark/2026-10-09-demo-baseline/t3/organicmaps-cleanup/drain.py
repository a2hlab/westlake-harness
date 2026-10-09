from pathlib import Path
import os,sys,importlib.util,json,time,shlex
D=Path(__file__).parent;W=Path(os.environ['WORKSPACES']);M=W/'westlake-harness'
p=M/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py';spec=importlib.util.spec_from_file_location('batch',p);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
(D/'commands').mkdir(exist_ok=True);board=b.Board('61b0657200000000000000000324012c',str(W/'westlake-inputs/tools/hdc_mac.sh'),'mac '+shlex.quote(str(W/'westlake-inputs/tools/board_note.sh')),'cx-t0',D/'commands');board.ready()
_,raw=board.shell('bm dump -n app.organicmaps');info=b.parse_bundle(raw,'app.organicmaps');(D/'bundle.txt').write_text(raw);uid=info['uid'];assert uid==20011137
receipts=[]
for attempt in range(3):
 board.shell('aa force-stop app.organicmaps');_,raw=board.shell('ps -A -o PID,PPID,UID,NAME');(D/('before-'+str(attempt)+'.txt')).write_text(raw);rows=b.processes(raw);parents=[r for r in rows if r['uid']==0 and r['ppid']==1 and r['name']=='appspawn-x'];assert len(parents)==1
 targets=[r for r in rows if r['uid']==uid];assert all(r['ppid']==parents[0]['pid'] and r['name']=='appspawn-x' for r in targets),'unexpected child ownership'
 cmds=[]
 for r in targets:
  pid,ppid=r['pid'],r['ppid'];assert pid!=parents[0]['pid'] and uid!=0
  cmds.append(f'if test "$(sed -n \'s/^Uid:[[:space:]]*\\([0-9]*\\).*/\\1/p\' /proc/{pid}/status)" = {uid} && test "$(sed -n \'s/^PPid:[[:space:]]*\\([0-9]*\\).*/\\1/p\' /proc/{pid}/status)" = {ppid}; then kill -9 {pid}; fi')
 if cmds:board.shell('; '.join(cmds))
 _,after=board.shell('ps -A -o PID,PPID,UID,NAME');(D/('after-'+str(attempt)+'.txt')).write_text(after);remaining=[r for r in b.processes(after) if r['uid']==uid];receipts.append(dict(attempt=attempt,parent=parents[0]['pid'],target_count=len(targets),remaining=remaining));(D/'receipt.json').write_text(json.dumps(receipts,indent=2)+'\n')
 if not remaining:
  time.sleep(1);_,again=board.shell('ps -A -o PID,PPID,UID,NAME');(D/'stable-ps.txt').write_text(again)
  if not any(r['uid']==uid for r in b.processes(again)):
   (D/'passed.json').write_text(json.dumps(dict(passed=True,uid=uid,parent_untouched=True,boot=board.boot),indent=2)+'\n');print('DRAIN_PASS');raise SystemExit(0)
raise RuntimeError('OrganicMaps respawns remain after three guarded batches; lock retained')
