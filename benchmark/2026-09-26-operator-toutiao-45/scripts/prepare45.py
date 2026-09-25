from board45 import *
ref=R.parents[1]/SOURCE/'ability38/framework-candidate/device-report.json'
base=R.parent/'campaign22/framework/device-report.json'
a=json.loads(ref.read_text());b=json.loads(base.read_text())
(R/'reference38.json').write_bytes(ref.read_bytes());(R/'reference61.json').write_bytes(base.read_bytes())
changes={k:v for k,v in a['files'].items() if v!=b['files'].get(k)}
for k,v in changes.items():
 p=R/'overlay'/k
 if not p.exists() or sha(p)!=v['sha256']:recv(a['stage']+'/'+k,p,SOURCE)
 assert sha(p)==v['sha256'],k
print('OVERLAY_READY',len(changes),flush=True)
while not c40_done():time.sleep(3)
(R/'c40-exit.json').write_text(json.dumps({'observed_epoch':time.time(),'vm_pid':1460613,'cmdline_no_longer_c40':True})+'\n')
# Only now touch the operator board.
(R/'before-processes.txt').write_text(dev('ps -A -o PID,PPID,NAME'))
(R/'setup.txt').write_text(dev('date '+time.strftime('%m%d%H%M%Y.%S')+'; power-shell timeout -o 86400000; power-shell wakeup; uinput -T -m 600 1500 600 300 400; bm dump -n org.westlake.imehost; ip addr show wlan0; ip route; ping -c 2 -W 3 223.5.5.5'))
stage='/data/local/tmp/a2hlab-framework-operator45-v7'
assert 'COPIED' in dev(f'if [ -e {stage} ]; then echo EXISTS; else cp -a {b["stage"]} {stage} && echo COPIED; fi',300)
for k in changes:send(R/'overlay'/k,stage+'/'+k)
expected={stage+'/'+k:v['sha256'] for k,v in a['files'].items()}
actual=dev('sha256sum '+' '.join(expected),180)
(R/'stage-hashes.txt').write_text(actual)
values={line.split()[1]:line.split()[0] for line in actual.splitlines() if len(line.split())==2}
assert all(values.get(k)==h for k,h in expected.items()),'stage hash mismatch'
fw=dev('sha256sum '+' '.join(a['firmware']),180);(R/'firmware-hashes.txt').write_text(fw)
values={line.split()[1]:line.split()[0] for line in fw.splitlines() if len(line.split())==2}
assert values==a['firmware'],'firmware mismatch'
cmd=a['device_command'].replace(a['stage'],stage)
log=dev(cmd+' 2>&1; echo PRELOAD_RC=$?',120);(R/'preload.log').write_text(log)
assert 'PRELOAD_RC=0' in log,log[-2000:]
a.update(stage=stage,device_command=cmd,device_log_sha256=hashlib.sha256(log.encode()).hexdigest(),operator45_source=str(ref),passed=True)
(R/'framework').mkdir(exist_ok=True);(R/'framework/device-report.json').write_text(json.dumps(a,indent=2)+'\n')
print('OPERATOR45_STAGE_PASS',len(expected),flush=True)
