#!/usr/bin/env python3
"""Compile real pinned consumer TUs with external JNI/OH seams; optional derived comparison."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent
REL='sources/api-implementations/bridge-d4fa-source-snapshot/base/westlake/framework/surface/jni'
NAMES=('oh_surface_texture_jni.cpp','oh_texture_view_jni.cpp')
EXPECTED=('c8d3bb700923c393c6e9aad43acf5004dba6d8a168ecfe829d66ec1c9c6f3f61','7189e5c2b70af0aa5fff155ca1bb464305f958655e994737dce4ac1878a0558b')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def command(argv,out,name):
    save(out/(name+'.argv.json'),argv)
    # A real regular stderr file enables the production logger's sink gate.
    with (out/(name+'.stdout')).open('wb') as stdout, (out/(name+'.stderr')).open('wb') as stderr:
        r=subprocess.run(argv,stdout=stdout,stderr=stderr,timeout=60)
    r.stdout=(out/(name+'.stdout')).read_bytes();r.stderr=(out/(name+'.stderr')).read_bytes()
    (out/(name+'.rc')).write_text(str(r.returncode)+'\n')
    if r.returncode:raise RuntimeError(name+' failed: '+r.stderr.decode(errors='replace')[-3000:])
    return r

def build(source,out,extra,includes):
    out.mkdir()
    paths=[(source/n).resolve() for n in NAMES]+[x.resolve() for x in extra]
    headers=list((P/'include').rglob('*.h'))
    for directory in [*includes,*[x.parent for x in extra]]:
        headers.extend(directory.resolve().glob('*.h'))
    inputs=list(dict.fromkeys(paths+headers+[P/'fixture.cpp']))
    before={str(x):sha(x) for x in inputs}
    snapshot=out/'input-snapshot';snapshot.mkdir()
    snapshot_rows=[]
    for i,x in enumerate(inputs):
        dest=snapshot/(str(i)+'-'+x.name);dest.write_bytes(x.read_bytes())
        assert sha(dest)==before[str(x)], 'source changed during snapshot'
        snapshot_rows.append({'file':dest.name,'sha256':sha(dest)})
    save(snapshot/'index.json',snapshot_rows)
    objects=[]
    for i,x in enumerate(extra):
        obj=out/('extra-'+str(i)+'.o');cc='clang' if x.suffix=='.c' else 'clang++'
        argv=[cc,'-c','-std=c11' if cc=='clang' else '-std=c++17','-I'+str(P/'include'),'-I'+str(source)]
        argv+=['-I'+str(d.resolve()) for d in includes]+[str(x.resolve()),'-o',str(obj)]
        command(argv,out,'compile-extra-'+str(i));objects.append(str(obj))
    exe=out/'fixture'
    argv=['clang++','-std=c++17','-pthread','-I'+str(P/'include'),'-I'+str(source),
          '-DPEER_SURFACE_SOURCE="'+str(paths[0])+'"',
          '-DPEERER_TEXTURE_SOURCE="'+str(paths[1])+'"']
    argv+=['-I'+str(d.resolve()) for d in includes]+[str(P/'fixture.cpp'),*objects,'-o',str(exe)]
    command(argv,out,'compile')
    assert before=={str(x):sha(x) for x in inputs},'source changed during compilation'
    r=command([str(exe)],out,'run')
    rows=[json.loads(line) for line in r.stdout.decode().splitlines()]
    save(out/'observations.json',rows)
    return rows,{'sources':[{'file':x.name,'sha256':before[str(x)]} for x in paths],
                 'executable_sha256':sha(exe),'cases':len(rows),
                 'headers_and_fixture':[{'file':x.name,'sha256':before[str(x)]} for x in inputs if x not in paths],
                 'stderr_sink':'regular file', 'stderr_sha256':sha(out/'run.stderr')}

def assert_baseline(rows):
    assert len(rows)==40
    cases={r['case']:r for r in rows}
    for name,row in cases.items():
        if name.startswith('producer/'):continue
        op,variant=name.split('/')
        invalid=variant in ('null-object','null-state','bad-magic','null-image')
        blocked=invalid or (op=='update' and variant=='released')
        calls=[e for e in row['events'] if e.startswith(op+':')]
        assert len(calls)==(0 if blocked else 1),(name,calls)
        if calls:assert calls[0].endswith('errno-in=37'),(name,calls)
        if op=='update':
            throw=blocked or variant in ('error','exception-errno')
            assert row['exception']==throw,(name,row)
            if throw:
                assert row['events'][-2].startswith('throw:') and row['events'][-1]=='delete-local'
            if variant=='exception-errno':assert row['errno']==83
        elif invalid:assert row['errno']==37
        else:assert row['errno']==71
    expected={
        'different':['get:3','unref:1:errno-in=37','set:3:zero','get:1','ref:2:errno-in=71','set:3:nonzero'],
        'alias':['get:3','unref:1:errno-in=37','set:3:zero','get:1','ref:1:errno-in=71','set:3:nonzero'],
        'old-null':['get:3','get:1','ref:2:errno-in=37','set:3:nonzero'],
        'new-null':['get:3','unref:1:errno-in=37','set:3:zero','get:1'],
        'both-null':['get:3','get:1'],
        'released':['get:3','unref:1:errno-in=37','set:3:zero','get:1'],
        'invalid-state':['get:3','unref:1:errno-in=37','set:3:zero','get:1'],
        'null-object':['get:3','unref:1:errno-in=37','set:3:zero'],
        'destroy':['get:3','unref:1:errno-in=37','set:3:zero'],
        'destroy-null':['get:3'],'field-unset':[]}
    expected['ref-unref-error']=expected['different'];expected['existing-exception']=expected['different']
    for name,events in expected.items():
        row=cases['producer/'+name];assert row['events']==events,(name,row['events'])
        assert row['exception']==(name=='existing-exception')
    assert cases['producer/alias']['window']==1
    assert cases['producer/ref-unref-error']['window']==2

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--consumer-source-dir',type=Path);ap.add_argument('--extra-source',type=Path,action='append',default=[])
    ap.add_argument('--include-dir',type=Path,action='append',default=[]);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    source=a.source_root/REL
    design=json.loads((a.source_root/'benchmark/2026-10-20-t29-window-observation/design/source-pins.json').read_text())
    for name,digest in zip(NAMES,EXPECTED):
        assert sha(source/name)==digest,name
        assert any(x['path']==REL+'/'+name and x['sha256']==digest for x in design['pins'])
    rows,pins=build(source,a.out/'baseline',[],[]);assert_baseline(rows)
    result={'status':'BASELINE_PASSED_DERIVED_PENDING','cases':len(rows),'baseline':pins,
            'candidate':None,'device_calls':0,'production_build':False,
            'scope':'real complete TU method bodies; fake external JNI/OH only; logger budget/sink not covered'}
    if a.consumer_source_dir:
        actual,newpins=build(a.consumer_source_dir,a.out/'derived',a.extra_source,a.include_dir)
        differences=[{'case':b['case'],'baseline':b,'derived':d} for b,d in zip(rows,actual) if b!=d]
        if len(actual)!=len(rows):differences.append({'case':'case-count','baseline':len(rows),'derived':len(actual)})
        save(a.out/'differences.json',differences)
        result.update(status='DERIVED_BEHAVIOR_MATCH' if not differences else 'DERIVED_BEHAVIOR_MISMATCH',candidate=newpins,differences=len(differences))
    save(a.out/'results.json',result);print(json.dumps(result))
    return 1 if result['status']=='DERIVED_BEHAVIOR_MISMATCH' else 0
if __name__=='__main__':sys.exit(main())
