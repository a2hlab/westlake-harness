"""Pure G13 admission checks; no transports."""
import datetime
import re

SERIAL='5ea34a4500000000000000001123012c'
ORIGINAL='51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5'
CANDIDATE='7c24bd11190b0728b81ecd958519f01c688efb2533ef26c9b7ae4eefc82151db'
APK='abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc'
TARGETS=['/system/lib64/libinstalls.z.so','/system/lib64/platformsdk/libinstalls.z.so']
class Refuse(RuntimeError): pass
def need(ok,msg):
    if not ok: raise Refuse(msg)
def identity(line):
    m=re.fullmatch(r'(\d+) \((.*)\) (.+)',line)
    need(m is not None,'malformed stat'); fields=m[3].split();need(len(fields)>=20,'short stat')
    return dict(pid=int(m[1]),comm=m[2],ppid=int(fields[1]),starttime=int(fields[19]))
def maps_snapshot(text):
    blocks=re.findall(r'BEGIN_PROC /proc/(\d+)\n(.*?)END_PROC /proc/\1(?:\n|$)',text,re.S)
    count=re.findall(r'^PROC_COUNT=(\d+)$',text,re.M)
    need(len(count)==1 and int(count[0])==len(blocks)>0,'maps coverage/count missing')
    ids={}; hits=[]
    for pid,body in blocks:
        need(int(pid) not in ids,'duplicate PID')
        for tag in ['STAT_BEFORE_RC','MAPS_RC','STAT_AFTER_RC']:
            need(re.findall('^'+tag+r'=(\d+)$',body,re.M)==['0'],tag+' incomplete/nonzero')
        stats=[l for l in body.splitlines() if re.match('^'+pid+r' \(',l)]
        need(len(stats)==2,'stat bracket missing')
        a,b=map(identity,stats);need(a==b,'PID identity drift '+pid);ids[int(pid)]=a
        for line in body.splitlines():
            if 'libinstalls.z.so' in line:
                f=line.split(None,5);need(len(f)==6,'malformed libinstalls mapping')
                hits.append(dict(pid=int(pid),line=line,dev=f[3],inode=int(f[4]),path=f[5]))
    return dict(identities=ids,hits=hits,count=len(ids))
def processes(text):
    rows={}
    for l in text.splitlines():
        f=l.split(None,3)
        if len(f)==4 and all(s.isdigit() for s in f[:3]):rows[int(f[0])]=dict(ppid=int(f[1]),uid=int(f[2]),name=f[3])
    need(bool(rows),'empty ps');return rows
def check_coverage(snapshot,before,after):
    a,b=processes(before),processes(after);ids=snapshot['identities']
    for table in [a,b]:
        for pid in table.keys()-ids.keys():
            row=table[pid];parent=table.get(row['ppid'],{})
            observer=(row['name']=='sh' and parent.get('name')=='hdcd') or (row['name']=='ps' and parent.get('name')=='sh' and table.get(parent['ppid'],{}).get('name')=='hdcd')
            need(observer,'uncovered non-observer PID '+str(pid))
    for pid in (a.keys()&b.keys()):
        need((a[pid]['ppid'],a[pid]['uid'])==(b[pid]['ppid'],b[pid]['uid']),'ps parent/uid drift '+str(pid))
        # NAME may change (e.g. kworker queue); birth is bracketed by proc stat.
    return True
def guard(cfg,held,boot,now,new_test=False):
    need(cfg['serial']==SERIAL,'wrong serial');need(held.strip()==cfg['bindings']['holder'],'full holder drift')
    fields=held.split();need(len(fields)==3 and fields[0]==cfg['bindings']['lane'] and fields[1].isdigit(),'bad holder')
    need(boot.strip()==cfg['expected_boot'],'boot drift')
    elapsed=now-datetime.datetime.fromisoformat(fields[2]).timestamp()
    need(0<=elapsed<1800,'window budget expired/future holder')
    if new_test:need(elapsed<1200,'new tests stopped at20min')
    return elapsed
