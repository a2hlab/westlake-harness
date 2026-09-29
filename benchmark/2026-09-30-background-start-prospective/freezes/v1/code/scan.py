#!/usr/bin/env python3
"""Offline 66-key lifecycle transition detector; no runtime outcome reads."""
import collections,concurrent.futures,functools,gzip,json,re,sys,traceback
from pathlib import Path
from detector import HERE,OLD,CALIBRATION,inspect_method,resolve_intent,classify
sys.path.insert(0,str(OLD))
import scan_reachability as reach
from scan_jni import sha
ROOT=HERE.parents[1]
ORIGINAL_PATHS=reach.compute_paths
# Reuse the existing conservative dispatch resolver, with Activity-only roots.
def lifecycle_paths(methods,parents,interfaces,roots):
    # Same exact/unique-dispatch rule as scan_reachability.compute_paths;
    # cache repeated hierarchy and target lookups for large multidex APKs.
    signatures=collections.defaultdict(list)
    for mid in methods:signatures[mid.split('.',1)[1]].append(mid)
    @functools.lru_cache(None)
    def ancestors(cls):
        seen=set();todo=[cls]
        while todo:
            current=todo.pop()
            if not current or current in seen:continue
            seen.add(current);todo.extend([parents.get(current)]+interfaces.get(current,[]))
        return seen
    @functools.lru_cache(None)
    def resolve(owner,suffix):
        seen=set()
        while owner and owner not in seen:
            seen.add(owner);mid=owner+'.'+suffix
            if mid in methods:return mid
            owner=parents.get(owner)
        return None
    @functools.lru_cache(None)
    def target_resolution(target,kind):
        owner,suffix=target.split('.',1)
        if kind.startswith(('invoke-static','invoke-direct','invoke-super')) or kind in {'class-initializer','startup-dependency'}:return resolve(owner,suffix),False
        if kind.startswith(('invoke-virtual','invoke-interface')):
            options={mid for mid in signatures.get(suffix,[]) if owner in ancestors(mid.split('.',1)[0])}
            declared=resolve(owner,suffix)
            if declared:options.add(declared)
            return (next(iter(options)),False) if len(options)==1 else (None,len(options)>1)
        return None,False
    discovered={r['method']:{'root':r,'parent':None,'edge':None} for r in roots if r['category']=='launcher_activity' and r['method'] in methods}
    queue=collections.deque(discovered);unresolved=collections.Counter()
    while queue:
        caller=queue.popleft()
        for edge in methods[caller]['edges']:
            resolved,ambiguous=target_resolution(edge['target'],edge['kind'])
            if ambiguous:unresolved['ambiguous_dispatch']+=1
            if resolved and resolved not in discovered:
                discovered[resolved]={'root':discovered[caller]['root'],'parent':caller,'edge':edge};queue.append(resolved)
            elif not resolved:unresolved['external_or_unresolved_call']+=1
    return discovered,dict(unresolved),resolve
reach.compute_paths=lifecycle_paths

def activity_nodes(raw,package):
    nodes=[];node=None;indent=0
    def qualify(s):
        if not s:return None
        return (package+s if s.startswith('.') else s if '.' in s else package+'.'+s).replace('.','/')
    for lineno,line in enumerate(raw.splitlines(),1):
        m=re.match(r'(\s*)E: (\S+)',line)
        if m:
            depth=len(m[1])
            if node is not None and depth<=indent:node=None
            if m[2] in ('activity','activity-alias'):
                node={'tag':m[2],'line':lineno,'attrs':{}};nodes.append(node);indent=depth
        elif node:
            m=re.match(r'\s*A: (?:http://[^:]+:)?([^ (=]+)(?:\([^)]*\))?=(.*)',line)
            # Only direct component attributes, not nested action/category names.
            if m and len(line)-len(line.lstrip())==indent+2:
                q=re.match(r'"([^"]*)"',m[2]);node['attrs'][m[1]]=q[1] if q else m[2]
    for node in nodes:
        node['class']=qualify(node['attrs'].get('name'));node['target']=qualify(node['attrs'].get('targetActivity'))
    return nodes

def scan(entry):
    key=entry['key'];out=HERE/'evidence';result=dict(key=key,apk_sha256=entry.get('apk_sha256'),status='unknown',calls=[],calibration=key in CALIBRATION)
    coverage=json.loads((ROOT/'benchmark/2026-09-30-framework-jni-gaps/app-coverage.json').read_text())
    prior=next(x for x in coverage if x['key']==key)
    try:
        if prior['status']!='scanned':raise ValueError(prior.get('error','prior APK identity unknown'))
        apk=Path(prior['apk']);expected=entry.get('apk_sha256') or prior['apk_sha256']
        if sha(apk)!=expected:raise ValueError('APK identity changed')
        result.update(apk=str(apk),apk_sha256=expected,package=entry['package'],input_scope='all classes*.dex in base APK; split dex, reflection, framework callbacks and branch feasibility unresolved')
        app=dict(key=key,apk=str(apk),sha256=expected,calls=[],features={})
        data=reach.scan(app,output_dir=out,inspect_method=inspect_method)
        nodes=activity_nodes((out/('manifest-'+key+'.txt')).read_text(),entry['package'])
        activities={x['target'] or x['class'] for x in nodes}
        launchers={x['class'].replace('.','/') for x in data['manifest']['launchers']}
        factories={x['method']:x['returns'] for x in data['extra_calls'] if x['kind']=='factory'}
        calls=[]
        for x in data['extra_calls']:
            if x['kind']!='start':continue
            target,proof=resolve_intent(x['intent'],factories)
            row={**x,'resolved_targets':target,'target_resolution':proof,'non_launcher_targets':[t for t in target if t in activities and t not in launchers], 'external_or_undeclared_targets':[t for t in target if t not in activities], 'splash_class':bool(re.search(r'Splash|Launch|Startup',x['method'].split('.',1)[0],re.I))}
            # A name-only constant is a candidate, never a resolved Intent target.
            row['activity_class_hints']=[h for h in row.pop('class_hints_same_method') if h['class_name'] in activities]
            calls.append(row)
        result.update(status='scanned',manifest=data['manifest'],activities=nodes,launchers=sorted(launchers),calls=calls,method_count=data['method_count'],reachable_method_count=data['reachable_method_count'],unresolved_edges=data['unresolved_edges'],manifest_sha256=sha(out/('manifest-'+key+'.txt')))
        result['manifest_splash_to_main_hint']=any(re.search('splash|launch|startup',x,re.I) for x in launchers) and any(re.search('MainActivity|HomeActivity',x or '',re.I) for x in activities-launchers)
        result['counts']=dict(all_start_calls=len(calls),launcher_path_calls=sum(x['startup_reachable']=='yes-static' for x in calls),explicit_nonlauncher_startup=sum(x['startup_reachable']=='yes-static' and bool(x['non_launcher_targets']) for x in calls),splash_class_calls=sum(x['splash_class'] for x in calls))
        # Retain compact per-key witnesses; raw dexdump line/offset is reproducible.
        raw=out/('reachability-'+key+'.json')
        with gzip.open(out/(key+'-graph-result.json.gz'),'wt') as f:json.dump(data,f)
        raw.unlink()
    except (ValueError,OSError,KeyError,RuntimeError) as exc:result['error']=str(exc)
    result.update(classify(key,result['calls'],result['status']))
    (out/(key+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print('RESULT',key,result['status'],result['tier'],result.get('counts'),flush=True)
    return result

def main():
    entries=json.loads((ROOT/'benchmark/2026-09-28-bms-route-deploy/batch/apps.json').read_text())['apps']
    # Calibration keys first; this allows early evidence review without outcomes.
    entries.sort(key=lambda x:(x['key'] not in CALIBRATION,x['key']))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(scan,entries))
    (HERE/'scan-results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('DONE',collections.Counter(r['tier'] for r in rows),flush=True)
if __name__=='__main__':main()
