from board45 import *
label=sys.argv[1] if len(sys.argv)>1 else 'guard-test'
r=R/label;r.mkdir(exist_ok=False);root=pathlib.Path(__file__).resolve().parents[1]
pid=int(dev('cat /data/local/tmp/operator45/child.pid').strip())
(r/'before.txt').write_text(dev(f'cat /data/local/tmp/operator45/guard.pid; cat /proc/{pid}/stat; cat /data/local/tmp/operator45/watchdog.log'))
(r/'kill.txt').write_text(dev(f'echo CONTROLLED_SIGKILL_PID={pid}; cat /proc/uptime; kill -9 {pid}; cat /proc/uptime'))
start=time.monotonic()
for seconds in (3,10,20,40,80):
 time.sleep(max(0,start+seconds-time.monotonic()))
 text=dev('cat /proc/uptime; cat /data/local/tmp/operator45/child.pid; cat /data/local/tmp/operator45-crashes/INDEX; cat /data/local/tmp/operator45/watchdog.log')
 (r/f'after-{seconds}s.txt').write_text(text)
 remote='/data/local/tmp/operator45-guard-test.jpeg';dev('snapshot_display -f '+remote+' >/dev/null');recv(remote,r/f'after-{seconds}s.jpeg')
 p=root/'preview'/label/f'after-{seconds}s.jpeg';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((r/f'after-{seconds}s.jpeg').read_bytes())
 print('RECOVERY_OBSERVED',seconds,text[:700],flush=True)
