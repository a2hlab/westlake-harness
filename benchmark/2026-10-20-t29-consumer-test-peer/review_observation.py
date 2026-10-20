#!/usr/bin/env python3
"""One process per case: real ready methods + real logger, frozen original behavior oracle."""
import argparse,json,sys
from pathlib import Path
import replay

P=Path(__file__).resolve().parent
OH,STATE,IMAGE,OLD,NEW,TEX,RELEASED,DETACHED,RAW,PUBLIC,PROVIDER,REF,UNREF=[1<<i for i in range(13)]

def parse(stderr):
    text=stderr.decode('utf-8',errors='strict')
    identity=None;records=[]
    for line in text.splitlines(keepends=True):
        if line.startswith('[PEER-IDENTITY] '):
            assert identity is None, 'multiple fixture cases in one process output'
            identity={k:int(v,16) for k,v in (item.split('=',1) for item in line.split()[1:])}
        if line.startswith('[WL-R29] side=consumer '):
            assert line.endswith('\n'), 'truncated record'
            fields=dict(item.split('=',1) for item in line.split()[1:])
            required={'self','p','v','oh','state','image','oldw','neww','called','raw','rc','rel','det','exbranch','ref','unref'}
            assert required<=fields.keys(), required-fields.keys()
            records.append(fields)
        assert not ('FIRST_LIMIT' in line or 'FINAL_EXHAUSTION' in line or 'TRUNC' in line), 'per-case coverage lost'
    assert identity is not None,'fixture identity receipt missing'
    assert identity['regular']==1, 'stderr was not a regular file'
    return identity,records

def dec(record,key):return int(record[key])
def ptr(record,key):return int(record[key],16)
def triple(record,key):return tuple(map(int,record[key].split('/')))
def valid(record,bit):return bool(int(record['v'],16)&bit)

def verify(name,identity,records):
    op,variant=name.split('/')
    assert all(ptr(record,'self')!=0 for record in records), 'method self-PC missing'
    if op!='producer':
        assert len(records)==1,(name,'expected exactly one method record',len(records))
        r=records[0];assert dec(r,'p')=={'attach':0,'detach':1,'update':2}[op]
        has_state=variant not in ('null-object','null-state','bad-magic')
        has_image=has_state and variant!='null-image'
        called=has_image and not(op=='update' and variant=='released')
        raw=-23 if variant in ('error','exception-find-fails','exception-errno') else 0
        assert dec(r,'called')==int(called)
        assert valid(r,STATE)==has_state and ptr(r,'state')==(identity['state'] if has_state else 0)
        assert valid(r,IMAGE)==has_image and ptr(r,'image')==(identity['image'] if has_image else 0)
        assert valid(r,OH)==has_state and ptr(r,'oh')==(identity['second'] if has_state else 0), 'OH must be NativeWindow, never image'
        assert valid(r,RAW)==called
        if called:assert dec(r,'raw')==raw
        assert valid(r,PUBLIC)==(op!='update')
        if op!='update':assert dec(r,'rc')==(raw if called else -1)
        detached_known=op!='update' and called and raw==0
        assert valid(r,DETACHED)==detached_known
        assert triple(r,'det')[0]==int(detached_known)
        if detached_known:assert triple(r,'det')[1]==int(op=='detach')
        assert valid(r,TEX)==(op=='attach')
        if op=='attach':assert dec(r,'tex')==42
        if op=='update':
            assert dec(r,'exbranch')==int(not called or raw!=0)
            if valid(r,RELEASED):
                assert has_state and triple(r,'rel')==(1,int(variant=='released'))
        assert triple(r,'ref')==(0,0,0) and triple(r,'unref')==(0,0,0)
        return
    destroy_only=variant in ('destroy','destroy-null','field-unset')
    assert [dec(r,'p') for r in records]==([4] if destroy_only else [4,3]), (name,'phase/order/coverage')
    old_exists=variant not in ('old-null','both-null','destroy-null','field-unset')
    d=records[0]
    if variant=='field-unset':assert int(d['v'],16)==0, 'unset field identity must remain unknown'
    assert dec(d,'called')==int(old_exists)
    assert triple(d,'unref')==((1,1,-31 if variant=='ref-unref-error' else 0) if old_exists else (0,0,0))
    assert valid(d,UNREF)==old_exists
    assert triple(d,'ref')==(0,0,0) and not valid(d,REF)
    assert valid(d,OH)==old_exists and ptr(d,'oh')==(identity['first'] if old_exists else 0)
    if old_exists:assert valid(d,OLD) and ptr(d,'oldw')==identity['first']
    if not destroy_only:
        r=records[1]
        new_exists=variant not in ('new-null','both-null','released','invalid-state','null-object')
        assert dec(r,'called')==int(new_exists)
        assert triple(r,'ref')==((1,1,-29 if variant=='ref-unref-error' else 0) if new_exists else (0,0,0))
        assert valid(r,REF)==new_exists
        assert triple(r,'unref')==((1,1,-31 if variant=='ref-unref-error' else 0) if old_exists else (0,0,0))
        assert valid(r,UNREF)==old_exists
        if old_exists:assert valid(r,OLD) and ptr(r,'oldw')==identity['first']
        else:assert ptr(r,'oldw')==0
        target=identity['first'] if variant=='alias' else identity['second']
        assert valid(r,OH)==new_exists and ptr(r,'oh')==(target if new_exists else 0)
        if new_exists:assert valid(r,NEW) and ptr(r,'neww')==target

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--consumer-source-dir',type=Path,required=True)
    ap.add_argument('--extra-source',type=Path,action='append',required=True)
    ap.add_argument('--include-dir',type=Path,action='append',default=[])
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    # Baseline is the already verified original40 receipt; no baseline compile is repeated here.
    baseline=json.loads((P/'baseline-observations.json').read_text())
    actual,pins=replay.build(a.consumer_source_dir,a.out/'candidate',a.extra_source,a.include_dir,P/'fixture-observation.cpp')
    errors=[]
    if actual!=baseline:errors.append({'case':'combined-behavior','error':'does not match frozen original40'})
    rows=[]
    for expected in baseline:
        name=expected['case'];out=a.out/name.replace('/','-');out.mkdir()
        result=replay.command([str(a.out/'candidate/fixture'),'--case',name],out,'run')
        behavior=[json.loads(line) for line in result.stdout.decode().splitlines()]
        identity=None;records=[];problem=None
        try:
            identity,records=parse(result.stderr)
            assert behavior==[expected], 'behavior differs from original40'
            verify(name,identity,records)
        except AssertionError as e:
            problem=str(e) or 'field assertion failed';errors.append({'case':name,'error':problem})
        rows.append({'case':name,'passed':problem is None,'error':problem,'records':records,
                     'identity':identity,'stderr_sha256':replay.sha(out/'run.stderr')})
    pids=[x['identity']['pid'] for x in rows if x['identity']]
    if len(set(pids))!=40:errors.append({'case':'process-isolation','error':'expected 40 distinct PIDs'})
    report={'independent_processes':len(set(pids)),'status':'METHOD_OBSERVATION_MATCH' if not errors else 'METHOD_OBSERVATION_MISMATCH',
            'cases':len(rows),'passed':sum(x['passed'] for x in rows),'errors':errors,
            'pins':pins,'baseline_observations_sha256':replay.sha(P/'baseline-observations.json'),
            'fixture_sha256':replay.sha(P/'fixture-observation.cpp'),'checker_sha256':replay.sha(Path(__file__)),
            'scope':'actual method fields and original behavior only; not logger concurrency/budget or production ABI',
            'device_calls':0,'records':rows}
    replay.save(a.out/'results.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))
    return bool(errors)
if __name__=='__main__':sys.exit(main())
