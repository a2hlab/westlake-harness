"""Extra SIGQUIT series, excluded from the unsampled factorial table."""
from run25 import *
import run25,runpy

def diagnostic(r,d,fresh):
 pid=d['child'];log=d['runtime']+f'/private-tmp/adapter_child_{pid}.stderr';events=[]
 def action(c):
  t=time.time();o=dev(c);events.append({'epoch':t,'command':c,'output':o});(r/'actions.json').write_text(json.dumps(events,indent=2));return o
 start=time.monotonic();consented=not fresh
 while time.monotonic()-start<110:
  action('echo v > /data/local/tmp/noice_tap');time.sleep(.4)
  raw=dev('tail -n 900 '+log)
  if not consented and '"同意"' in raw:
   (r/'consent-vt.txt').write_text(raw);action('echo c 600 1273 > /data/local/tmp/noice_tap');consented=True
  if consented and 'FontTextView' in raw and '"头条"' in raw:
   (r/'before-vt.txt').write_text(raw);break
  if '[INITCHILD-FAIL]' in raw:raise RuntimeError('UI exited before diagnostic')
 else:raise RuntimeError('No UI before diagnostic')
 action('aa start -b org.westlake.imehost -a EntryAbility');time.sleep(1)
 tids=re.findall(r'\[TOUCH21-POLL\] enter now=\d+ tid=(\d+)',raw)
 ui=tids[-1] if tids else None
 (r/'ui-tid-candidate.txt').write_text(str(ui))
 action('echo i 309 213 > /data/local/tmp/noice_tap')
 start=time.monotonic()
 for i in range(90):
  # ART's signal catcher dumps all threads; main is selected by stack bottom, not name.
  action(f'cat /proc/uptime; kill -3 {pid}');time.sleep(.4)
  if ui and i%3==0:
   native=action(f'cat /proc/uptime; dumpcatcher -p {pid} -t {ui}; cat /proc/uptime')
   (r/f'native-{i:03}.txt').write_text(native)
  raw=dev("grep -F '[TOUCH21] run action=1 ' "+log)
  if raw.strip():break
  if time.monotonic()-start>60:raise RuntimeError('Touch not consumed during diagnostic')
 time.sleep(2)
 if 'late' in sys.argv:
  time.sleep(45)
  action('echo i 309 213 > /data/local/tmp/noice_tap')
  time.sleep(10)
  action(f'kill -3 {pid}')
  time.sleep(1)
 (r/'network-end.txt').write_text(dev('iptables -nvxL OUTPUT; ip6tables -nvxL OUTPUT; ifconfig wlan0'))
 collect(r,d);print('DIAGNOSED',r.name,flush=True)
run25.measure=diagnostic
# Usage: diagnose25.py offline fresh diag1 (run identity stays distinct)
runpy.run_path(str(pathlib.Path(__file__).with_name('trial25.py')),run_name='__main__')
