#!/usr/bin/env python3
"""Unsigned exact-finding comparison. Never writes the main registry or approvals."""
import json,sys
from pathlib import Path
from inspect_inputs import sha,save
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3];MAIN=WS/'westlake-harness'
def read(p):return json.loads(p.read_text())
def body(r):return {k:v for k,v in r.items() if k not in ['issue_id','disposition','exception']}
def key(r):return json.dumps(body(r),sort_keys=True,separators=(',',':'))
def main():
    sys.path.insert(0,str(MAIN/'scripts/lab'));import u7_executor as u7
    oldroot=WS/'westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4/native';old=read(MAIN/'benchmark/2026-10-03-u13-final-assembly/evidence/native-v3.json');registry=read(MAIN/'knowledge/gates/native-predeploy-exceptions.json')
    oldexceptions={(r['gate'],r['issue_id']):r for r in registry['exceptions'] if r['package_manifest_sha256']==old['package_manifest_sha256'] and r['inputs_sha256']==old['inputs_sha256']}
    def objects(root):
        m=read(root/'package.json');v={t:r['sha256'] for t,r in u7.effective_files(m).items()};d=read(root/'native-checks/native-gates.json');v.update({r['target']:r['sha256'] for r in d['namespaces']['system_files']});return v
    oldobj=objects(oldroot);results={};proposal=[]
    for kind in ['baseline','candidate']:
        root=HERE/'.private/assembly-02'/kind/'native';report=read(HERE/f'.private/gates-02/native-{kind}.stdout');assert not report['errors'];newobj=objects(root)
        oldns=read(oldroot/'native-checks/native-gates.json')['namespaces'];newns=read(root/'native-checks/native-gates.json')['namespaces']
        assert oldns==newns
        assert sha(oldroot/oldns['owner_artifact']['path'])==sha(root/newns['owner_artifact']['path'])==oldns['owner_artifact']['sha256']
        assert sha(oldroot/'native-checks/namespace-manifest.json')==sha(root/'native-checks/namespace-manifest.json')
        for source in read(root/'native-checks/namespace-manifest.json')['config_sources']:
            assert sha(oldroot/'native-checks'/source['path'])==sha(root/'native-checks'/source['path'])==source['sha256']
        rows=[]
        for gate in ['N1','N2']:
            historical={key(r):r for r in old['gates'][gate]['findings']}
            for r in report['gates'][gate]['findings']:
                previous=historical.get(key(r));approval=oldexceptions.get((gate,previous['issue_id'])) if previous else None
                evidence={};f=body(r)
                if gate=='N2':
                    paths=set([f['library']] if f.get('library') else []);paths.update(f.get('outside_domain_candidates',[]))
                    if f.get('resolved'):paths.add(f['resolved'])
                    if f.get('directory'):paths.update(p for p in set(oldobj)|set(newobj) if str(Path(p).parent)==f['directory'])
                    evidence={p:{'historical_sha256':oldobj.get(p),'current_sha256':newobj.get(p),'role':'consumer' if p==f.get('library') else ('directory-member' if f.get('directory') else 'provider-candidate')} for p in sorted(paths)}
                changes={p:x for p,x in evidence.items() if x['historical_sha256']!=x['current_sha256']}
                group_review=gate=='N2' and ((f.get('needed')=='liboh_android_runtime.so') or f.get('directory') in ['/system/android/lib64','/system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac'])
                row={'gate':gate,'issue_id':r['issue_id'],'finding':f,'old_issue_id':previous['issue_id'] if previous else None,'exact_finding_match':previous is not None,'old_approval_found':approval is not None,'old_approval_reference':{'registry':'knowledge/gates/native-predeploy-exceptions.json','package_manifest_sha256':old['package_manifest_sha256'],'inputs_sha256':old['inputs_sha256'],'issue_id':previous['issue_id']} if approval else None,'objects':evidence,'changed_objects':changes,'review_class':'REVIEW_CHANGED_OBJECTS' if group_review else ('REVIEW_NEW_FINDING' if not approval else 'EXACT_FINDING_AND_OBJECTS_REBIND_REVIEW'),'consumer':f.get('library'),'provider_resolution':f.get('resolved'),'namespace_inheritance_used':f.get('inherit_used'),'reason':'Same finding text is not byte equivalence; re-review current objects and G18 policy change' if group_review else 'Exact historical finding and inspected object SHA match; owner/config unchanged; new manifest/inputs still require actual outer approval'}
                if gate=='N1':row.update(review_class='CURRENT_SOURCE_BINDING_REVIEW',reason='Use n1-current-source-attestation.json; exact finding match alone does not authorize a source/artifact binding')
                if gate=='N2' and not group_review:assert not changes
                rows.append(row)
                proposal.append({'status':'UNSIGNED_PROPOSAL','package':kind,'gate':gate,'package_manifest_sha256':report['package_manifest_sha256'],'inputs_sha256':report['inputs_sha256'],'issue_id':r['issue_id'],'review_class':row['review_class'],'reason':row['reason'],'removal_condition':approval['removal_condition'] if approval else 'Requires new complete evidence or verified fix','evidence':['benchmark/2026-10-21-commercial-game/gles-transaction-package/exception-comparison.json','benchmark/2026-10-21-commercial-game/gles-transaction-package/n1-current-source-attestation.json'],'approved_by':None,'approved_at':None})
        n2=[r for r in rows if r['gate']=='N2'];assert len(n2)==104 and all(r['exact_finding_match'] and r['old_approval_found'] for r in n2);assert sum(r['review_class']=='REVIEW_CHANGED_OBJECTS' for r in n2)==4
        results[kind]={'package_manifest_sha256':report['package_manifest_sha256'],'inputs_sha256':report['inputs_sha256'],'N1_findings':len([r for r in rows if r['gate']=='N1']),'N2_findings':104,'N2_exact_finding_matches':104,'N2_changed_object_review':4,'N2_exact_object_rebind_review':100,'N1_unmatched_findings':sum(r['gate']=='N1' and not r['exact_finding_match'] for r in rows),'rows':rows}
    save(HERE/'exception-comparison.json',{'status':'UNSIGNED_NOT_A_REGISTRY','execution_enabled':False,'registry_sha256':sha(MAIN/'knowledge/gates/native-predeploy-exceptions.json'),'old_report_sha256':sha(MAIN/'benchmark/2026-10-03-u13-final-assembly/evidence/native-v3.json'),'packages':results,'note':'Four N2 review classes are union across baseline/candidate. Baseline route object may be unchanged; candidate loader changes there. No approval/signature transferred.'})
    save(HERE/'exceptions.unsigned.json',{'status':'UNSIGNED_NOT_CONSUMABLE_BY_GATE','exceptions':proposal})
    print(json.dumps({k:{n:v for n,v in d.items() if n!='rows'} for k,d in results.items()},sort_keys=True))
if __name__=='__main__':main()
