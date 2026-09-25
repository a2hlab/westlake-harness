from run25 import *
app=sys.argv[1];r=R/('control-'+app);d=json.loads((r/'device-report.json').read_text());log=d['runtime']+f'/private-tmp/adapter_child_{d["child"]}.stderr'
print(dev('readlink /data/local/tmp/noice_tap'))
n=int(dev('wc -l < '+log).strip());dev('echo v > /data/local/tmp/noice_tap');time.sleep(2)
raw=dev(f'tail -n +{n+1} '+log);(r/'before-vt-refresh.txt').write_text(raw)
print('\n'.join(s for s in raw.splitlines() if any(x in s for x in ('TextView','Button','[VT','[OH-TOUCH','[OHTouch'))))
