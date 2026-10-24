#!/usr/bin/env python3
"""Explicit opt-in, read-only 61b ordinary log increments. No UI/process control."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shlex
import subprocess
import time
import uuid

SERIAL = '61b0657200000000000000000324012c'
PARENT_LOG = '/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/parent.log'
EVENT_ROOT = '/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r3/boots'
UID = 20011206
LIMIT = 1048576
DURATION = 90.0
COMMAND_LIMIT = 10.0
CHILD_NAME = 'com.ss.android.article.news'

class Stop(Exception):
    pass

def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2)
        f.write('\n')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def config(boot, parent, birth):
    if str(uuid.UUID(boot)) != boot or parent <= 1 or birth <= 0:
        raise ValueError('exact boot / positive parent identity required')
    return {'boot': boot, 'parent_pid': parent, 'parent_birth': birth}

def shell(c, previous):
    """Fixed commands/paths only. Size headers frame binary data, not line markers."""
    pid = c['parent_pid']
    paths = [('parent', PARENT_LOG), ('events', f"{EVENT_ROOT}/{c['boot']}/events.log")]
    script = r'''set -eu
export LC_ALL=C
emit() {
    label=$1; shift
    value=$("$@") || exit 91
    printf '@%s %s\n%s\n' "$label" "${#value}" "$value"
}
identity() {
    phase=$1
    emit "boot_$phase" cat /proc/sys/kernel/random/boot_id
    emit "uptime_$phase" cat /proc/uptime
'''
    script += f'    emit "parent_stat_$phase" cat /proc/{pid}/stat\n'
    script += f'    emit "parent_status_$phase" cat /proc/{pid}/status\n'
    script += f'    emit "fd1_$phase" readlink /proc/{pid}/fd/1\n'
    script += f'    emit "fd2_$phase" readlink /proc/{pid}/fd/2\n'
    script += r'''}
identity pre
'''
    # POSIX builtins only for filtering; no awk/tr on OH toybox.
    script += f'''target_ps() {{
    psrows=$(ps -A -o PID,PPID,UID,NAME) || exit 92
    printf '%s\\n' "$psrows" | while read -r row_pid row_ppid row_uid row_name; do
        if [ "$row_pid" = PID ] && [ "$row_ppid" = PPID ] && [ "$row_uid" = UID ] && [ "$row_name" = NAME ]; then
            printf 'PID PPID UID NAME\\n'; continue
        fi
        for number in "$row_pid" "$row_ppid" "$row_uid"; do
            case "$number" in ''|*[!0-9]*) exit 93;; esac
        done
        if [ "$row_ppid" = {pid} ] && [ "$row_uid" = {UID} ] && [ "$row_name" = {CHILD_NAME} ]; then
            printf '%s %s %s %s\\n' "$row_pid" "$row_ppid" "$row_uid" "$row_name"
        fi
    done
}}
rows=$(target_ps) || exit 93
emit ps_pre printf %s "$rows"
child=$(printf '%s\\n' "$rows" | while read -r p rest; do
    [ "$p" = PID ] || printf '%s\\n' "$p"
done)
'''
    script += f'''raw_cmdline() {{
    printf '@%s {len(CHILD_NAME.encode())+1}\\n' "$cmd_label"
    dd if="/proc/$child/cmdline" bs=1 count={len(CHILD_NAME.encode())+1} || exit 97
    printf '\\n'
}}
'''
    script += r'''case "$child" in *[!0-9]* ) exit 93;; esac
emit child_id printf %s "$child"
if [ -n "$child" ]; then
    emit child_pre cat "/proc/$child/stat"
    emit child_status_pre cat "/proc/$child/status"
    cmd_label=child_cmd_pre; raw_cmdline
fi
'''
    for name, path in paths:
        q = shlex.quote(path)
        old = previous.get(name)
        script += f'test ! -L {q} && test -f {q} || exit 94\n'
        script += f"meta=$(stat -c '%d %i %s %f' {q}) || exit 94\n"
        script += f'emit {name}_pre printf %s "$meta"\nset -- $meta\n'
        if old is None:
            script += f"printf '@{name}_data 0\\n\\n'\n"
        else:
            dev, inode, offset, mode = old
            script += f'[ "$1" = {dev} ] && [ "$2" = {inode} ] && [ "$3" -ge {offset} ] && [ "$4" = {shlex.quote(mode)} ] || exit 95\n'
            script += f'n=$(($3 - {offset}))\n[ "$n" -le 65536 ] || exit 96\n'
            script += f'printf "@{name}_data %s\\n" "$n"\n'
            script += f'if [ "$n" -gt 0 ]; then dd if={q} bs=1 skip={offset} count="$n"; fi\nprintf "\\n"\n'
        script += f"emit {name}_post stat -c '%d %i %s %f' {q}\n"
    script += r'''if [ -n "$child" ]; then
    emit child_post cat "/proc/$child/stat"
    emit child_status_post cat "/proc/$child/status"
    cmd_label=child_cmd_post; raw_cmdline
fi
emit ps_post target_ps
identity post
emit done printf complete
'''
    return script

def frames(raw):
    result = {}
    while raw:
        header, sep, rest = raw.partition(b'\n')
        match = re.fullmatch(rb'@([a-z0-9_]+) ([0-9]+)', header)
        if not sep or not match:
            raise Stop('malformed or incomplete frame')
        key = match[1].decode(); n = int(match[2])
        if key in result or n > LIMIT or len(rest) < n + 1 or rest[n:n+1] != b'\n':
            raise Stop('short, duplicate or oversized frame')
        result[key] = rest[:n]; raw = rest[n+1:]
    if result.get('done') != b'complete':
        raise Stop('missing complete marker')
    return result

def proc(raw):
    text = raw.decode(); left, right = text.rsplit(') ', 1)
    a = right.split()
    return (int(left.split(' ', 1)[0]), int(a[1]), int(a[19]), a[0])

def uid(raw):
    matches = re.findall(rb'^Uid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$', raw, re.M)
    if len(matches) != 1:
        raise Stop('missing/malformed UID')
    return tuple(int(x) for x in matches[0])

def child_rows(raw, parent):
    lines = raw.decode().splitlines()
    if not lines or lines[0].split() != ['PID', 'PPID', 'UID', 'NAME']:
        raise Stop('unexpected ps header')
    found = []
    for line in lines[1:]:
        a = line.split(None, 3)
        if len(a) != 4 or not all(x.isdigit() for x in a[:3]):
            raise Stop('malformed ps row')
        if a[3] == CHILD_NAME and int(a[1]) == parent and int(a[2]) == UID:
            found.append(int(a[0]))
    if len(found) > 1:
        raise Stop('multiple target children')
    return found

class State:
    def __init__(self, c):
        self.c = c; self.files = {}; self.child = None; self.uptime = None

    def accept(self, raw):
        f = frames(raw); parent = self.c['parent_pid']
        for phase in ['pre', 'post']:
            if f[f'boot_{phase}'].decode() != self.c['boot']:
                raise Stop('boot changed')
            p = proc(f[f'parent_stat_{phase}'])
            if p[0] != parent or p[2] != self.c['parent_birth'] or p[3] in ['Z', 'X', 'x'] or uid(f[f'parent_status_{phase}']) != (0,)*4:
                raise Stop('parent identity changed')
            if any(f[f'fd{i}_{phase}'].decode() != PARENT_LOG for i in [1, 2]):
                raise Stop('parent log fd target changed')
        if proc(f['parent_stat_pre'])[:3] != proc(f['parent_stat_post'])[:3]:
            raise Stop('parent relation changed')
        pre_up = float(f['uptime_pre'].split()[0]); post_up = float(f['uptime_post'].split()[0])
        if not 0 <= pre_up <= post_up or (self.uptime is not None and pre_up < self.uptime):
            raise Stop('uptime changed backwards')
        ids = child_rows(f['ps_pre'], parent)
        post_ids = child_rows(f['ps_post'], parent)
        transition = self.child is None and not ids and len(post_ids) == 1
        if (ids != post_ids and not transition) or f['child_id'].decode() != (str(ids[0]) if ids else ''):
            raise Stop('child changed during sample')
        current = None
        if ids:
            pre = proc(f['child_pre']); post = proc(f['child_post'])
            if pre[:3] != post[:3] or pre[0] != ids[0] or pre[1] != parent or any(x in ['Z','X','x'] for x in [pre[3],post[3]]):
                raise Stop('child birth/parent/state changed')
            for phase in ['pre','post']:
                if uid(f[f'child_status_{phase}']) != (UID,)*4 or f[f'child_cmd_{phase}'] != CHILD_NAME.encode()+b'\x00':
                    raise Stop('child UID/cmdline changed')
            current = pre[:3]
        if self.child is not None and current != self.child:
            raise Stop('latched child disappeared/replaced')
        newfiles = {}; deltas = {}; intervals = {}
        for name in ['parent','events']:
            def meta(k):
                a = f[k].decode().split()
                if len(a) != 4: raise Stop('bad stat')
                v = (int(a[0]),int(a[1]),int(a[2]),a[3])
                if min(v[:3]) < 0 or int(v[3],16) & 0xf000 != 0x8000: raise Stop('not regular')
                return v
            pre=meta(name+'_pre');post=meta(name+'_post');old=self.files.get(name)
            if pre[:2]!=post[:2] or pre[3]!=post[3] or post[2]<pre[2]: raise Stop('rotation/truncation during sample')
            if old and (pre[:2]!=old[:2] or pre[3]!=old[3] or pre[2]<old[2]): raise Stop('rotation/truncation since sample')
            start = old[2] if old else pre[2]
            data=f[name+'_data']
            if len(data)!=pre[2]-start: raise Stop('increment length mismatch')
            newfiles[name]=pre;deltas[name]=data;intervals[name]={'start':start,'end':pre[2],'sha256':digest(data)}
        self.uptime=post_up
        if transition:
            # Keep existing offsets: the next stable sample re-reads these bytes.
            # If this is the initial sample, pre sizes define its zero-data origin.
            if not self.files:
                self.files=newfiles
            return {'status':'identity_transition/partial','uptime_bracket':[pre_up,post_up],
                    'child_identity':None,'observed_post_pid_unbound':post_ids[0],
                    'offsets_advanced':False,'ranges_unaccepted':intervals},deltas
        self.files=newfiles;self.child=current
        return {'status':'stable','uptime_bracket':[pre_up,post_up],'child_identity':current,'ranges':intervals},deltas

class Transport:
    """Bounded local subprocess streams; never signal a device process."""
    def __init__(self, out, deadline, cap=LIMIT, clock=time.monotonic):
        self.out=out;self.deadline=deadline;self.remaining=cap;self.clock=clock;self.count=0

    def run(self, argv):
        if self.remaining<=0 or self.clock()>=self.deadline: raise Stop('budget exhausted')
        folder=self.out/f'command-{self.count:04d}';folder.mkdir();self.count+=1
        save(folder/'argv.json',argv)
        start=self.clock(); end=min(self.deadline,start+COMMAND_LIMIT)
        chunks={'stdout':bytearray(),'stderr':bytearray()};reason=None;p=None
        with (folder/'stdout').open('xb') as so,(folder/'stderr').open('xb') as se:
            files={'stdout':so,'stderr':se}
            try:
                p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                with selectors.DefaultSelector() as sel:
                    for key,stream in [('stdout',p.stdout),('stderr',p.stderr)]:
                        os.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,key)
                    while sel.get_map():
                        remaining_time=end-self.clock()
                        if remaining_time<=0: reason='timeout';break
                        if self.remaining<=0: reason='byte_cap';break
                        for key,_ in sel.select(min(remaining_time,0.1)):
                            data=os.read(key.fileobj.fileno(),min(8192,self.remaining))
                            if not data:sel.unregister(key.fileobj);continue
                            files[key.data].write(data);files[key.data].flush();chunks[key.data].extend(data);self.remaining-=len(data)
                            if self.remaining==0:reason='byte_cap';break
                        if reason:break
                    if not reason:
                        try:p.wait(timeout=max(0.001,end-self.clock()))
                        except subprocess.TimeoutExpired:reason='timeout'
            except Exception as exc:
                reason=f'local_error:{type(exc).__name__}:{exc}'
            finally:
                if p is not None:
                    if p.poll() is None:
                        # Cancellation is exclusively of the locally launched HDC client.
                        p.kill()
                    p.wait()
                    p.stdout.close();p.stderr.close()
                save(folder/'receipt.json',{'local_rc':None if p is None else p.returncode,'stop':reason,'elapsed_s':self.clock()-start,'stdout_bytes':len(chunks['stdout']),'stderr_bytes':len(chunks['stderr']),'stdout_sha256':digest(chunks['stdout']),'stderr_sha256':digest(chunks['stderr']),'remaining_raw_bytes':self.remaining})
        if reason: raise Stop(reason)
        if p.returncode!=0:raise Stop(f'remote_or_transport_rc:{p.returncode}')
        return bytes(chunks['stdout'])

def observe(c, out, transport, deadline, clock=time.monotonic, sleep=time.sleep):
    state=State(c);n=0;accepted=0;transitions=0;reason='duration_complete'
    try:
        while clock()<deadline:
            tick=clock()
            argv=[c['hdc'],'-t',SERIAL,'shell',shell(c,state.files)]
            raw=transport.run(argv)
            summary,deltas=state.accept(raw)
            save(out/f'sample-{n:04d}.json',summary)
            accepted += summary['status']=='stable'
            transitions += summary['status']=='identity_transition/partial'
            # No duplicate raw logs: the immutable command stdout already contains deltas.
            n+=1
            sleep(max(0,min(deadline-clock(),1-(clock()-tick))))
    except (Stop,ValueError,KeyError,IndexError,UnicodeError) as exc:
        reason=str(exc)
    result={'status':'STOPPED','reason':reason,'observed_samples':n,'accepted_samples':accepted,'identity_transition_samples':transitions,'last_child_identity':state.child,'last_offsets':state.files,'timing_limit':'Visibility intervals only; buffering and truncate/regrow between samples may be unobservable.'}
    save(out/'result.json',result)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--boot',required=True);p.add_argument('--parent-pid',type=int,required=True);p.add_argument('--parent-birth',type=int,required=True)
    p.add_argument('--hdc',default='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc')
    p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true')
    a=p.parse_args();c=config(a.boot,a.parent_pid,a.parent_birth);c['hdc']=a.hdc
    a.out.mkdir(parents=True,exist_ok=False)
    save(a.out/'plan.json',{'config':c,'serial':SERIAL,'duration_s':DURATION,'max_raw_bytes':LIMIT,'max_command_s':COMMAND_LIMIT,'initial_argv':[a.hdc,'-t',SERIAL,'shell',shell(c,{})],'execute':a.execute})
    if not a.execute:
        print('PLAN_ONLY: no subprocess/device call');return 0
    end=time.monotonic()+DURATION
    r=observe(c,a.out,Transport(a.out,end),end)
    print(json.dumps(r));return 0 if r['reason']=='duration_complete' else 2

if __name__=='__main__':
    raise SystemExit(main())
