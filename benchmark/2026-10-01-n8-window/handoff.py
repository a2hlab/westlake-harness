import os,signal,time,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent
owned={2715828:'n8-window/supervise.py',2778717:'n8-window/run_batch.py',2748079:'n8-window/watch.py'}
for pid,needle in owned.items():
 text=Path('/proc/'+str(pid)+'/cmdline').read_bytes().replace(b'\0',b' ').decode();assert needle in text,(pid,text)
os.kill(2715828,signal.SIGSTOP)
os.killpg(2778717,signal.SIGTERM);os.killpg(2748079,signal.SIGTERM)
time.sleep(1)
os.kill(2715828,signal.SIGKILL)
(H/'supervisor-handoff.json').write_text(json.dumps(dict(old_processes=owned,device_processes_signalled=False,reason='Outer approved 45-minute deadline and target-first order',time=time.time()),indent=2)+'\n')
os.execv(sys.executable,[sys.executable,str(H/'supervise_resume.py')])
