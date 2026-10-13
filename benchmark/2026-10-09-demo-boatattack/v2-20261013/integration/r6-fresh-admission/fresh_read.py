#!/usr/bin/env python3
"""Future root-only read entry; default refuses transport. T0 never runs collection."""
import argparse,json,sys,time,subprocess
from pathlib import Path
from unittest.mock import patch
import binding as b

def collect(q,out):
    c,p=b.artifact(q);origin_boot,_=b.origin(q,c,p);after=b.deployment(q,c,p)
    b.need(sys.platform!='darwin','run the frozen Reader in Orb; controller/lock stay Mac')
    out.mkdir(parents=True,exist_ok=False);rows=[];original_run=subprocess.run;started=time.time()
    def record(argv,**kwargs):
        begin=time.time();r=original_run(argv,**kwargs);end=time.time();n=len(rows)+1
        stdout=out/('command-%03d.stdout.txt'%n);stderr=out/('command-%03d.stderr.txt'%n)
        stdout.write_text(r.stdout);stderr.write_text(r.stderr)
        rows.append(dict(argv=argv,rc=r.returncode,started=begin,finished=end,stdout=b.pin(stdout),stderr=b.pin(stderr)))
        return r
    upstream=b.load(p['programs']['reader'],'actual_frozen_reader');absence=b.load(p['programs']['absence_reader'],'actual_frozen_absence')
    try:
        with patch('subprocess.run',record):
            result=c.check(absence.with_absence(upstream.Reader)(out,b.SERIAL),p,out,origin_boot)
        b.need(result['passed'] is True and result['boot_before']==result['boot_after']==q['candidate_boot'],'candidate fresh boot identity')
    finally:
        cap=dict(schema='r6-original-reader-capture/v1',serial=b.SERIAL,origin_boot=origin_boot,candidate_boot=q['candidate_boot'],proof=q['artifact']['proof'],collector=b.pin(__file__),binding=b.pin(b.__file__),started=started,finished=time.time(),commands=rows,identity=b.pin(out/'identity.json') if (out/'identity.json').is_file() else None)
        (out/'capture.json').write_text(json.dumps(cap,indent=2)+'\n')
    # Re-run only local recorded bytes, using the exact frozen Reader/check.
    q=dict(q,fresh_capture=b.pin(out/'capture.json'));replay=out/'offline-replay';replay.mkdir()
    b.replay(q,c,p,replay,after)
    print(json.dumps({'capture':b.pin(out/'capture.json'),'recorded_read_calls':len(rows),'remote_writes':0,'execution_enabled':False}))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--request',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--collect-read-only',action='store_true');a=ap.parse_args()
    b.need(a.collect_read_only,'disabled: explicit read-only collection flag required')
    collect(b.read(a.request),a.out)
if __name__=='__main__':main()
