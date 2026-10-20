#!/usr/bin/env python3
"""Single historical fixed-range read. No application or UI operations."""
import argparse, datetime, hashlib, json, re, shlex, subprocess, sys, time, uuid
from pathlib import Path
START, END = 26377929, 57241402
PROFILE_SHA = 'eb2887fbdbdaf23d6fc1cd2840b0d8d80ea5854962753e7d4d13ce311346a077'
LOG = '/data/service/el1/public/appspawnx/adapter_child_1601.stderr'
SERIAL = '5cd1e3dd00000000000000000923012c'

def need(ok, reason):
    if not ok: raise ValueError(reason)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, x): p.write_text(json.dumps(x, indent=2)+'\n')

def plan(start, end):
    need(type(start) is int and type(end) is int and 0 <= start < end, 'range')
    aligned = start//4096*4096; length = end-aligned
    need(length <= 64*1024*1024, 'raw cap')
    return dict(start=start, end=end, aligned=aligned, raw_length=length, trim=start-aligned,
                blocks=length//4096, tail=length%4096, selected_length=end-start)

def script(path, p, token, scratch, guard):
    need(re.fullmatch('[a-f0-9]{32}', token), 'token')
    q=shlex.quote; full_end=p['aligned']+p['blocks']*4096
    # Diagnostic files keep dd stderr out of the declared binary payload.
    return f'''(set -eu; {guard}; mkdir {q(scratch)}
printf 'T15_BEGIN_{token}:{p['raw_length']}\\n'
set +e
dd if={q(path)} bs=4096 skip={p['aligned']//4096} count={p['blocks']} 2>{q(scratch+'/block.err')}
a=$?
dd if={q(path)} bs=1 skip={full_end} count={p['tail']} 2>{q(scratch+'/tail.err')}
b=$?
printf '\\nT15_END_{token}:%s:%s\\n' "$a" "$b"
cat {q(scratch+'/block.err')} {q(scratch+'/tail.err')}
set -e
{guard}
printf '\\nT15_POST_{token}\\n')'''

def decode(raw, p, token, rc, timed_out):
    need(rc == 0 and not timed_out, 'transport incomplete')
    head=f'T15_BEGIN_{token}:{p["raw_length"]}\n'.encode()
    end=f'\nT15_END_{token}:0:0\n'.encode(); post=f'\nT15_POST_{token}\n'.encode()
    at=len(head)+p['raw_length']
    need(raw.startswith(head) and raw[at:at+len(end)]==end and raw.endswith(post), 'short/error/frame/postguard')
    payload=raw[len(head):at]
    return payload[p['trim']:p['trim']+p['selected_length']]

def capture(argv, out, timeout):
    receipt={'argv':argv, 'started':time.time(), 'timeout_seconds':timeout, 'timed_out':False}
    save(out/'transport.json',receipt)
    with (out/'stdout.raw').open('wb') as stdout, (out/'stderr.raw').open('wb') as stderr:
        try: receipt['rc']=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=timeout).returncode
        except subprocess.TimeoutExpired: receipt.update(rc=None,timed_out=True)
        except OSError as e: receipt.update(rc=None,error=str(e))
    receipt['finished']=time.time();save(out/'transport.json',receipt)
    return receipt

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--execute',action='store_true')
    for k in ('repo','profile','out'):ap.add_argument('--'+k,type=Path)
    ap.add_argument('--hdc');ap.add_argument('--holder');ap.add_argument('--start',type=float)
    ap.add_argument('--timeout',type=float,default=180);a=ap.parse_args();p=plan(START,END)
    if not a.execute:
        print(json.dumps(dict(execute=False,device_calls=0,serial=SERIAL,path=LOG,plan=p)));return
    need(all((a.repo,a.profile,a.out,a.hdc,a.holder,a.start)), 'explicit inputs')
    need(sha(a.profile)==PROFILE_SHA,'exact historical profile')
    for rel,digest in json.loads(Path(__file__).with_name('source-pins.json').read_text()).items():
        need(sha(a.repo/rel)==digest,'source pin '+rel)
    need(0<a.timeout<=180,'timeout bound')
    need(abs(a.start-datetime.datetime.fromisoformat(a.holder.split()[2]).timestamp())<1,'holder timestamp')
    age=time.time()-a.start;need(0<=age<280,'300-second window with closure reserve')
    deadline=time.monotonic()+300-age
    need(a.out.is_absolute() and not str(a.out).startswith(('/tmp/','/private/tmp/')),'persistent out')
    a.out.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(a.repo/'benchmark/2026-10-20-t14-play-observation'));import observe
    profile=observe.profile(json.loads(a.profile.read_text()))
    sys.path.insert(0,str(a.repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
    class Board(b.Board):
        def command(self,argv,timeout=60):
            left=deadline-time.monotonic()-20;need(left>0,'deadline')
            return super().command(argv,min(timeout,left,10))
        def ready(self):
            super().ready();rc,holder=self.command(self.lock+['held',SERIAL],10)
            need(rc==0 and holder.strip()==a.holder,'exact holder')
    board=Board(SERIAL,a.hdc,'bash '+shlex.quote(str(a.repo/'scripts/lab/board_note.sh')),a.holder.split()[0],a.out/'commands');board.boot=profile['boot']
    tok=uuid.uuid4().hex;scratch='/data/local/tmp/t15-range-'+tok
    g=observe.guard(profile)+f'; test -f {LOG}; test "$(readlink /proc/1601/fd/2)" = {LOG}; test "$(stat -L -c %d:%i {LOG})" = 66352:178230; test "$(stat -L -c %s {LOG})" -ge {END}'
    cmd=script(LOG,p,tok,scratch,g);(a.out/'recipe.sh').write_text(cmd+'\n')
    result=dict(status='PARTIAL_UNVERIFIED',profile_sha256=PROFILE_SHA,holder=a.holder,start=a.start,plan=p,token=tok,scratch=scratch,device_application_writes=0)
    save(a.out/'result.json',result)
    try:
        board.ready();left=deadline-time.monotonic()-20;need(left>0,'deadline')
        receipt=capture(board.hdc+['-t',SERIAL,'shell',cmd],a.out,min(a.timeout,left))
        raw=(a.out/'stdout.raw').read_bytes();selected=decode(raw,p,tok,receipt['rc'],receipt['timed_out'])
        board.ready()
        (a.out/'selected.raw').write_bytes(selected)
        result.update(status='FIXED_RANGE_BYTES_COMPLETE',source_offset=START,selected_bytes=len(selected),sha256=hashlib.sha256(selected).hexdigest(),runtime_verdict='pending_review')
    except Exception as e: result['error']=str(e)
    finally:
        result['files']={f.name:{'sha256':sha(f),'bytes':f.stat().st_size} for f in a.out.iterdir() if f.is_file() and f.name!='result.json'}
        save(a.out/'result.json',result)
    print(json.dumps(result));return 0 if result['status']=='FIXED_RANGE_BYTES_COMPLETE' else 1

if __name__=='__main__':sys.exit(main())
