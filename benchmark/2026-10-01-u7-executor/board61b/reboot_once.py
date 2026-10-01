"""One explicitly authorized reboot, read-only new-boot capture, then lab wake/clock setup."""
import json,sys,time
from pathlib import Path
repo=Path(__file__).resolve().parents[3];sys.path.insert(0,str(repo/'scripts/lab'));import u7_executor as u
out=Path(__file__).resolve().parent;serial='61b0657200000000000000000324012c'
old=json.loads((out/(sys.argv[1] if len(sys.argv)>1 else 'apply1-journal.json')).read_text())
io=u.DeviceIO(serial,'cx-t0',out/'reboot-device')
io.guard(old['boot_id'])
result={'before_boot':io.boot,'reboot_sent':True,'automatic_replay':False}
(out/'reboot.json').write_text(json.dumps(result,indent=2))
try:io.shell('reboot',timeout=15)
except Exception as exc:result['reboot_transport_result']=str(exc)
(out/'reboot.json').write_text(json.dumps(result,indent=2))
for attempt in range(60):
    time.sleep(2)
    try:
        fresh=u.DeviceIO(serial,'cx-t0',out/f'postboot-read-{attempt}')
        if fresh.boot==old['boot_id']:continue
        values,absent=fresh.snapshot(sorted(old['plan']['expected']),old['plan']['expected'])
        result.update(after_boot=fresh.boot,postboot_hashes=values,postboot_absent=absent,
                      postboot_mounts=fresh.mounts(),postboot_processes=fresh.ps())
        (out/'reboot.json').write_text(json.dumps(result,indent=2))
        # Read-only capture above is complete before any new-boot setup write.
        result['lab_preflight']=fresh.b.preflight(fresh.board,fresh.out)
        fresh.shell('power-shell wakeup')
        fresh.shell('uitest uiInput swipe 600 1700 600 300 2000')
        (out/'reboot.json').write_text(json.dumps(result,indent=2))
        print('new boot',fresh.boot,'absent',len(absent));break
    except Exception as exc:
        result['last_poll_error']=str(exc)
        (out/'reboot.json').write_text(json.dumps(result,indent=2))
else:raise SystemExit('board did not become ready after the single reboot')
