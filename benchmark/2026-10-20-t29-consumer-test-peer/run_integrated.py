#!/usr/bin/env python3
"""Merged-tree Rust entry: exact four source pins, real methods and real logger, no skips."""
import argparse,json,os,subprocess,sys,tempfile
from pathlib import Path
import replay
P=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--consumer-root',type=Path,default=Path(os.environ.get('T29_CONSUMER_ROOT',str(P.parents[1]/'benchmark/2026-10-20-t29-window-observation/consumer'))))
    a=ap.parse_args();consumer=a.consumer_root.resolve()
    pins_path=consumer/'design/source-pins.json'
    data=json.loads(pins_path.read_text())
    roles=('derived_surface_texture','derived_texture_view','logger_impl','logger_header')
    expected=data['method_ready_sources']
    before={}
    for role in roles:
        item=expected[role];rel=Path(item['path'])
        assert not rel.is_absolute() and '..' not in rel.parts
        actual=replay.sha(consumer/rel);assert actual==item['sha256'],role+' pin drift'
        before[str(rel)]=actual
    base=Path.home()/'.local/share/westlake/t29-consumer-selectors';base.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='methods-',dir=base))
    (out/'consumer-source-pins.json').write_bytes(pins_path.read_bytes())
    replay.save(out/'inputs.json',{'consumer_source_pins_sha256':replay.sha(pins_path),'sources':before})
    argv=[sys.executable,str(P/'review_observation.py'),'--consumer-source-dir',str(consumer/'derived'),
          '--extra-source',str(consumer/'logger/observe29c.c'),'--include-dir',str(consumer/'logger'),
          '--out',str(out/'actual')]
    replay.save(out/'argv.json',argv)
    with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
        result=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=120)
    (out/'rc').write_text(str(result.returncode)+'\n')
    assert result.returncode==0,(out/'stderr').read_text()[-2000:]+'; evidence='+str(out)
    assert before=={rel:replay.sha(consumer/rel) for rel in before},'consumer changed during actual run'
    report=json.loads((out/'actual/results.json').read_text())
    assert report['status']=='METHOD_OBSERVATION_MATCH' and report['passed']==40 and report['independent_processes']==40
    print(json.dumps({'status':'PASS_REAL_METHODS','cases':40,'independent_processes':40,'raw':str(out),'sources':before}))
    return 0
if __name__=='__main__':sys.exit(main())
