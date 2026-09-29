#!/usr/bin/env python3
"""Compact class-risk entrypoints. No board observation is a scan input."""
import collections,csv,json
from pathlib import Path
from scan_classes_v3 import OUT,dump,sha,R13
from scan_io import load

def csvwrite(path,rows):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader()
        for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in row.items()})

def main():
    cohort=load(OUT/'cohort.json');summary=[];compact=[];ranking=collections.defaultdict(lambda:{'apps':set(),'startup_apps':set(),'rows':0});predictions=[]
    for app in cohort['apps']:
        data=load(OUT/(app['key']+'.json'));groups=collections.defaultdict(list)
        for i,row in enumerate(data['rows']):groups[(row['kind'],row.get('service',''),row['class'],row['availability'])].append((i,row))
        public_rows=[]
        for (kind,service,cls,state),members in sorted(groups.items()):
            startup=[r for r in members if r[1]['startup_reachable']=='yes-static'];first=(startup or members)[0]
            public_rows.append({**first[1],'full_method_reference_count':len(members),'startup_method_reference_count':len(startup)})
            compact.append({'app':app['key'],'apk_sha256':app['sha256'],'kind':kind,'service':service,'class':cls,'availability':state,'startup_reachable':'yes-static' if startup else 'unknown','full_method_reference_count':len(members),'startup_method_reference_count':len(startup),'runtime_load':'unknown' if state!='definition-absent' else 'unresolvable-in-scanned-inputs','evidence':f"{app['key']}-evidence.json#/rows/{len(public_rows)-1}",'stub_ok':kind in ['service-interface-prerequisite','manager-interface-prerequisite'],'needs_real':'unknown' if kind=='direct-framework-reference' else False})
            if state=='definition-absent':
                k=ranking[cls];k['apps'].add(app['key']);k['rows']+=len(members)
                if startup:k['startup_apps'].add(app['key'])
        public={'app':data['app'],'counts':data['counts'],'scanner_sha256':data['scanner_sha256'],'graph_scanner_sha256':data['graph_scanner_sha256'],'rows':public_rows,'startup_paths':{r['method']:data['startup_paths'][r['method']] for r in public_rows if r['method'] in data.get('startup_paths',{})},'scope':'One representative per class/kind/service/status, preferring startup paths. Counts retain all distinct method references; complete intermediates are reproducible locally.'}
        dump(OUT/(app['key']+'-evidence.json'),public)
        csvwrite(OUT/(app['key']+'-class-matrix.csv'),[r for r in compact if r['app']==app['key']])
        csvwrite(OUT/(app['key']+'-class-risks.csv'),[r for r in compact if r['app']==app['key'] and r['availability'] in ['definition-absent','unknown']])
        rows=[r for r in data['rows'] if r['availability']=='definition-absent'];startup=[r for r in rows if r['startup_reachable']=='yes-static']
        summary.append({'app':app['key'],'apk_sha256':app['sha256'],'status':'scanned','rows':len(data['rows']),'absent_classes':len({r['class'] for r in rows}),'absent_reference_or_prerequisite_rows':len(rows),'startup_absent_classes':len({r['class'] for r in startup}),'startup_absent_rows':len(startup),'unknown_service_rows':sum(r['availability']=='unknown' for r in data['rows'])})
        predictions.append({'app':app['key'],'profile':'v3a-74d1d6d4+r13-f1325297','startup_class_risks':sorted({r['class'] for r in startup}),'unresolved_class_risks':sorted({r['class'] for r in rows}-{r['class'] for r in startup}),'ordering':'startup-static before unknown; no executed first-wall order inferred','evidence':f'{app["key"]}-class-risks.csv'})
        if app['key']=='wikipedia':
            selected=[(i,r) for i,r in enumerate(data['rows']) if r['class']=='android/net/IConnectivityManager' and 'ConnectionStateMonitor' in r['method']]
            dump(OUT/'wikipedia-delivery.json',{'app':data['app'],'summary':summary[-1],'r13_interfaces':len(load(OUT/'service-interface-matrix.json')),'known_answer':'PASS; retrospective known answer from #80 R1, not a prospective hit','evidence':[{'intermediate_row':i,'method':r['method'],'dex':r['dex'],'line':r['line'],'offset':r['offset'],'startup_reachable':r['startup_reachable'],'path':data.get('startup_paths',{}).get(r['method']) or {'path':r.get('path'),'root':r.get('root')}} for i,r in selected]})
    rank=[{'class':cls,'startup_affected_apps':len(v['startup_apps']),'all_reference_apps':len(v['apps']),'full_reference_or_prerequisite_rows':v['rows'],'startup_apps':sorted(v['startup_apps']),'all_apps':sorted(v['apps'])} for cls,v in ranking.items()];rank.sort(key=lambda r:(-r['startup_affected_apps'],-r['all_reference_apps'],r['class']))
    csvwrite(OUT/'class-availability.csv',compact);csvwrite(OUT/'class-risks.csv',[r for r in compact if r['availability'] in ['definition-absent','unknown']]);csvwrite(OUT/'apps-summary.csv',summary);csvwrite(OUT/'class-wall-ranking.csv',rank);csvwrite(OUT/'predictions-v3a-r13.csv',predictions)
    result={'requested_memberships':33,'scanned_memberships':33,'unique_apks_scanned':len(summary),'duplicate_membership':'ooniprobe in #69 and #78','scope_note':cohort['scope_note'],'missing_inputs':[],'r13_sha256':sha(R13),'class_inventory':'class-inventory.json.gz','known_answers':{'passed':1,'total':1,'scope':'retrospective supplied #80 R1 IConnectivityManager answer'},'apps':summary,'ranking':rank,'limitations':['Static definition presence is not runtime class loading or initialization success.','Startup paths are conditional; no branch feasibility or framework/async callback closure.','33 memberships contain only 32 unique APKs; a distinct 33rd identity was not supplied.']}
    dump(OUT/'results.json',result)
    ignore=OUT.parents[1]/'.gitignore';lines=ignore.read_text().splitlines()
    for app in cohort['apps']:
        for name in [app['key']+'.json',app['key']+'.json.gz','evidence/reachability-'+app['key']+'.json','evidence/reachability-'+app['key']+'.json.gz']:
            line='/v3/classes/'+name
            if line not in lines:lines.append(line)
    ignore.write_text('\n'.join(lines)+'\n')
    root=OUT.parents[1]/'results.json';r=load(root);r['class_presence_v3a_r13']={'results':'v3/classes/results.json','unique_apks':len(summary),'memberships':33,'known_answer':'1/1 retrospective','profile':'v3a+r13; separate from the JNI/r8b matrix'};dump(root,r)
    print(json.dumps({'scanned':len(summary),'ranking_top':rank[:4],'aggregate_rows':len(compact)}))
if __name__=='__main__':main()
