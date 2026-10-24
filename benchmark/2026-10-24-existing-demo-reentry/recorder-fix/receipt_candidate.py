import json,time,datetime,subprocess,re
from review_wait import publish_once
from pathlib import Path
RUN=Path(__file__).resolve().parent
CTX=json.loads((RUN/'context.json').read_text()); PLAN=json.loads((RUN/'plan.json').read_text())
def wall():return datetime.datetime.now().astimezone().isoformat()
def call(label,cmd,deadline=120):
    clock=json.loads((RUN/'clock.json').read_text()); start=time.monotonic()
    args=[v.replace('$MAIN',CTX['main']).replace('$RUN_ID',RUN.name).replace('$RUN',str(RUN)) for v in cmd['argv']]
    limit=min(cmd['timeout_seconds'],clock['monotonic']+deadline-start)
    if limit<=0:raise RuntimeError('deadline before '+label)
    with (RUN/(label+'.reserved')).open('x') as reservation:reservation.write(wall())
    rec={'argv':args,'start_wallclock':wall(),'start_monotonic':start,'timeout_seconds':limit}
    publish_once(RUN/(label+'.begin.json'),rec)
    with (RUN/(label+'.stdout')).open('xb') as o,(RUN/(label+'.stderr')).open('xb') as e:
        p=subprocess.Popen(args,stdout=o,stderr=e)
        try:rc=p.wait(timeout=limit); timed=False
        except subprocess.TimeoutExpired:p.kill();p.wait();rc=p.returncode;timed=True
    rec.update(end_wallclock=wall(),end_monotonic=time.monotonic(),rc=rc,timeout=timed)
    publish_once(RUN/(label+'.json'),rec)
    text=(RUN/(label+'.stdout')).read_text(errors='replace');err=(RUN/(label+'.stderr')).read_text(errors='replace')
    print(label,rc,'timeout' if timed else '',flush=True)
    return rec,text,err
def good(r,s,e):
    if r['rc']!=0 or r['timeout'] or e.strip() or re.search(r'(?i)connect server failed|permission denied|approval|\[fail\]|no such file|not found',s):raise RuntimeError('command unsuccessful: '+str(r['argv']))
def power(s):
    m=re.findall(r'ScreenOffTime:\s*Timeout=(\d+)ms\s+OverrideTimeout=(\d+)ms',s)
    if len(m)!=1:raise RuntimeError('ambiguous power')
    return dict(zip(('base','override'),map(int,m[0])))
def identity(s):
    lines=s.splitlines()
    if not lines or lines[0].strip()!=PLAN['baseline_receipt']['boot']:raise RuntimeError('boot mismatch')
    stats={};procs={}
    for line in lines[1:]:
        m=re.match(r'^(4958|5129) \(.+\) (.+)$',line)
        if m:
            fields=m[2].split();stats[m[1]]={'birth':int(fields[19]),'ppid':int(fields[1])};continue
        cols=line.split(None,3)
        if len(cols)==4 and all(v.isdigit() for v in cols[:3]):
            if re.search(r'article',cols[3],re.I):raise RuntimeError('article child present')
            if cols[0] in ('4958','5129'):
                if cols[0] in procs:raise RuntimeError('duplicate PID')
                procs[cols[0]]={'ppid':int(cols[1]),'uid':int(cols[2]),'args':cols[3]}
    if set(stats)!=set(('4958','5129')) or set(procs)!=set(stats):raise RuntimeError('missing identity')
    if 'imehost' not in procs['4958']['args'] or 'appspawn' not in procs['5129']['args']:raise RuntimeError('name mismatch')
    for pid in stats:
        if stats[pid]['ppid']!=procs[pid]['ppid']:raise RuntimeError('PPID mismatch')
        procs[pid].update(stats[pid])
    return procs
