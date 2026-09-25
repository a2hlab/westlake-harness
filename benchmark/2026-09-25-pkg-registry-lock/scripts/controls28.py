from run25 import *
app=sys.argv[1]
r,d=launch('control-'+app,app=app)
print('LAUNCHED',app,d['child'],flush=True)
log=d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr'
(r/'observation-start.txt').write_text(dev(f'cat /proc/{d["child"]}/stat; cat /proc/uptime'))
dev('aa start -b org.westlake.imehost -a EntryAbility')
time.sleep(8)
n=int(dev('wc -l < '+log).strip())
dev('echo v > /data/local/tmp/noice_tap');time.sleep(2)
(r/'before-vt.txt').write_text(dev(f'tail -n +{n+1} '+log))
print('READY_FOR_CLICK',app,flush=True)
