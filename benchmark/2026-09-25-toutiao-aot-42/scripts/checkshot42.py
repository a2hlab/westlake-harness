from board42 import *
name=sys.argv[1]
if not re.fullmatch(r'[a-z0-9-]+',name):raise ValueError(name)
r=R/name;d=json.loads((r/'device-report.json').read_text());remote=d['stage']+'/check.jpeg'
stamps=dev('cat /proc/uptime; snapshot_display -f '+remote+' >/dev/null; cat /proc/uptime')
recv(remote,r/'check.jpeg');(r/'check-uptime.txt').write_text(stamps);print(stamps)
