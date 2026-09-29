"""66 APK bounded startup paths joined to at most six framework Java call edges."""
import collections,concurrent.futures,gzip,json,sys,time
from pathlib import Path
import graph as g
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def trace_app(mid,paths):
    trace=[];cur=mid
    while paths[cur]['parent'] is not None:
      e=paths[cur];trace.append({'caller':e['parent'],'callee':cur,**e['edge']});cur=e['parent']
    return {'root':paths[mid]['root'],'path':list(reversed(trace))}

def trace_framework(start,native,edges,depth):
    todo=collections.deque([(start,[])]);seen={start}
    while todo:
      node,path=todo.popleft()
      if node==native:return path
      if len(path)>=depth:continue
      for nxt in edges.get(node,[]):
        if nxt not in seen:seen.add(nxt);todo.append((nxt,path+[{'caller':node,'callee':nxt}]))
    return None

def scan_app(entry,fw):
    key=entry['key'];out=HERE/'evidence/apps';out.mkdir(exist_ok=True)
    result={'key':key,'status':'started','startup':{},'all_code':[], 'app_direct_native':[]}
    try:
      folder=Path.home()/'a2hlab/app-inputs'/key
      meta=json.loads((folder/'app-input.json').read_text());expected=entry.get('apk_sha256') or meta['apk_sha256']
      if meta['apk_sha256']!=expected:raise ValueError('manifest vs app-input identity mismatch')
      candidates=sorted(folder.glob('*.apk'))
      apk=next((p for p in candidates if g.sha(p)==expected),None)
      if apk is None:raise ValueError('original APK bytes do not match the pinned input')
      result.update(apk=str(apk),apk_sha256=expected,app_input_sha256=g.sha(folder/'app-input.json'),split_dex_scope='base APK only; split dex not scanned')
      mf=g.manifest(apk);(out/('manifest-'+key+'.txt')).write_text(mf.pop('raw'))
      methods,parents,interfaces,_=g.parse_zip(apk)
      roots=g.startup_roots(mf,methods,parents)
      paths,unresolved,_=g.compute_paths(methods,parents,interfaces,roots)
      allmask=0;startmask=0;direct=set();witness={};combined=dict(fw['parents']);combined.update(parents)
      # App-owned methods shadow same-named framework methods: only external calls join FW.
      for caller,m in methods.items():
        for edge in m['edges']:
          target=edge['target']
          if target in methods:continue
          resolved=g.resolve(target,fw['nodes'],combined)
          if not resolved:continue
          mask=fw['masks'].get(resolved,0)
          if not mask:continue
          allmask |= mask
          if resolved in fw['index']:direct.add(resolved)
          if caller not in paths:continue
          fresh=mask & ~startmask
          if not fresh:continue
          startmask |= mask
          apptrace=trace_app(caller,paths)
          for i in g.bits(fresh):
            mid=fw['native_ids'][i]
            witness[mid]={'caller':caller,'framework_entry':resolved,'edge':edge,
                          'startup_root':apptrace['root'],'app_path':apptrace['path'],
                          'framework_path':None,'reachability':'conditional-static',
                          'framework_depth_limit':fw['depth']}
      # Save compact witnesses; framework paths reconstructed on publication only for gaps.
      result.update(status='scanned',manifest=mf,roots=roots,method_count=len(methods),reachable_method_count=len(paths),unresolved_edges=unresolved,
                    all_code=[fw['native_ids'][i] for i in g.bits(allmask)],startup=witness,app_direct_native=sorted(direct))
      print(key,'methods',len(methods),'startup methods',len(paths),'native startup/all',len(witness),len(result['all_code']),flush=True)
    except (OSError,ValueError,KeyError,RuntimeError) as exc:
      result.update(status='unknown',error=str(exc));print(key,'UNKNOWN',str(exc),flush=True)
    with gzip.open(out/(key+'.json.gz'),'wt') as f:json.dump(result,f)
    return {k:v for k,v in result.items() if k in ['key','status','error','apk','apk_sha256','method_count','reachable_method_count','unresolved_edges','split_dex_scope']}

def main():
    fw=json.load(gzip.open(HERE/'evidence/framework-graph.json.gz','rt'))
    fw['masks']={k:int(v,16) for k,v in fw['masks'].items()}
    fw['nodes']=set(fw['methods'])|set(fw['native_ids']);fw['index']={mid:i for i,mid in enumerate(fw['native_ids'])}
    del fw['methods'];del fw['edges']
    entries=json.loads((ROOT/'benchmark/2026-09-28-bms-route-deploy/batch/apps.json').read_text())['apps']
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
      rows=list(pool.map(lambda e:scan_app(e,fw),entries))
    (HERE/'app-coverage.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('coverage',collections.Counter(r['status'] for r in rows),flush=True)
if __name__=='__main__':main()
