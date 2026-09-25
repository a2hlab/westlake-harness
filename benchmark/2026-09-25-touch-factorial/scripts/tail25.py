from board25 import *
r=R/sys.argv[1];d=json.loads((r/'device-report.json').read_text());p=d['child'];log=d['runtime']+f'/private-tmp/adapter_child_{p}.stderr'
print(dev('tail -n '+(sys.argv[2] if len(sys.argv)>2 else '80')+' '+log))
