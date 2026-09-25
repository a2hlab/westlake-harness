from board45 import *
assert c40_done()
r=R/'first';assert not r.exists()
source=R.parents[1]/SOURCE/'ability38/warm-b11/launch-config.json'
cmd=json.loads(source.read_text())['argv']
for key,val in [('--serial',S),('--out',str(r)),('--framework-report',str(R/'framework/device-report.json'))]:cmd[cmd.index(key)+1]=val
# Foreground before spawning: doing this afterward can steal the new child focus.
dev('aa start -b org.westlake.imehost -a EntryAbility');time.sleep(1);dev('uinput -T -d 1150 1140 -u 1150 1140')
with (R/'first.driver.log').open('w') as f:p=subprocess.run(cmd,cwd=pathlib.Path.home()/'a2hlab/manifest',stdout=f,stderr=subprocess.STDOUT)
if p.returncode:raise RuntimeError((R/'first.driver.log').read_text()[-3000:])
d=json.loads((r/'device-report.json').read_text())
for fp in d.get('touch',{}).get('forwarder_pid','').split():
 if 'touchfwd' in dev('readlink /proc/'+fp+'/exe'):dev('kill '+fp)
(r/'launch-config.json').write_text(json.dumps({'argv':cmd},indent=2)+'\n')
recv(d['runtime']+'/run.sh',r/'run.sh')
print('OPERATOR45_LIVE',json.dumps({k:d[k] for k in ('parent','child','stage','runtime')}),flush=True)
