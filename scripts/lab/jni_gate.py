#!/usr/bin/env python3
"""Fail closed on unproved JNI coverage, after exact, reviewed exceptions.

Offline only. --package rescans bytes. --matrix additionally requires --package
and verifies every recorded input before accepting the cached scan.
"""
import argparse, collections, gzip, hashlib, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCAN=ROOT/'benchmark/2026-09-29-static-wall-prediction/scan_jni.py'
COVERED={'exported','registered'}

def load(path):
    """JSON from path, or from path.gz when only the compressed copy is in the checkout."""
    path=Path(path)
    if not path.exists() and Path(str(path)+'.gz').exists():path=Path(str(path)+'.gz')
    return json.loads(gzip.open(path,'rt').read() if path.suffix=='.gz' else path.read_text())

def evaluate(result,allowlist):
    accepted={};invalid=[]
    for e in allowlist.get('exceptions',[]):
        if e.get('approval')!='approved':continue
        if not all(e.get(k) for k in ('method','generation','overlay_sha256','status','reason','evidence','approved_by')):
            invalid.append(e.get('method','<missing method>'));continue
        if e['generation']==result['generation'] and e['overlay_sha256']==(result.get('overlay') or {}).get('sha256'):
            accepted[(e['method'],e['status'])]=e
    blockers=[];excepted=[]
    for m in result['methods']:
        if m['status'] in COVERED:continue
        if (m['id'],m['status']) in accepted:excepted.append(m['id'])
        else:blockers.append({'method':m['id'],'status':m['status'],'reason':m['reason']})
    if not result['methods']:invalid.append('empty method inventory')
    return {'pass':not blockers and not invalid,'generation':result['generation'],'method_count':len(result['methods']),'covered_count':sum(m['status'] in COVERED for m in result['methods']),'excepted_count':len(excepted),'blocked_count':len(blockers),'blocked_statuses':dict(collections.Counter(x['status'] for x in blockers)),'blockers':blockers,'invalid_approved_exceptions':invalid}

def cached(path,package):
    data=load(path);manifest=package/'package.json'
    current=json.loads(manifest.read_text());digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    matches=[r for r in data.values() if r['generation']==current['generation'] and Path(r['package']).resolve()==package.resolve()]
    if len(matches)!=1:raise ValueError('matrix does not identify exactly one requested package')
    r=matches[0]
    if digest(SCAN)!=r.get('scanner_sha256'):raise ValueError('scanner changed; rescan')
    if digest(manifest)!=r['package_manifest_sha256']:raise ValueError('stale package manifest; rescan')
    for item in r['inputs']+r.get('source_inputs',[])+r.get('scanner_dependencies',[]):
        if digest(Path(item['path']))!=item['sha256']:raise ValueError('stale matrix input: '+item['path'])
    return r

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--matrix',type=Path);p.add_argument('--allowlist',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args(argv)
    try:
        if a.matrix:r=cached(a.matrix,a.package)
        else:
            spec=importlib.util.spec_from_file_location('b10_scan',SCAN);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);r=mod.scan(a.package)
        verdict=evaluate(r,load(a.allowlist))
    except (OSError,ValueError,KeyError,RuntimeError) as e:
        print(json.dumps({'pass':False,'error':str(e)}));return 2
    text=json.dumps(verdict,indent=2)+'\n'
    if a.output:a.output.write_text(text)
    print(text,end='');return 0 if verdict['pass'] else 1
if __name__=='__main__':sys.exit(main())
