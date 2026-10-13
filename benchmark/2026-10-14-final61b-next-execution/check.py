#!/usr/bin/env python3
"""Offline original-input/parameter checks only; no transport, no deployment or execution authority."""
import ast,copy,hashlib,importlib.util,json,os,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[2])))
MAIN=WS/'westlake-harness'
SERIAL='61b0657200000000000000000324012c'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def expand(p):return Path(str(p).replace('$WORKSPACES',str(WS)))
def main():
    q=read(HERE/'consumer-binding.pending.json');a=read(HERE/'user-approval.realization.json');r=read(HERE/'realization.request.pending.json')
    authority=expand(q['user_authorization']['path']);original=read(authority)
    assert sha(authority)==q['user_authorization']['sha256']==sha(HERE/'user-authorization.original.json')
    assert original['status']=='USER_APPROVED_EXECUTION' and original['authorized_by']=='user' and original['serial']==SERIAL
    assert a['status']=='APPROVED' and a['approved_by']=='user' and a['authoritative_source']==q['user_authorization']
    assert all(a[k]==v for k,v in original.items() if k not in {'schema','status'})
    assert a['execution_enabled'] is False and q['execution_enabled'] is False and q['user_unseal_pending'] is False
    assert all(v is None for v in q['actual'].values()),'unobserved binding filled'
    assert r['execution_enabled'] is False and r['phase']=='running' and r['parameters']['serial']==SERIAL
    assert all(v is None for k,v in r['parameters'].items() if k!='serial')
    assert r['user_approval']['sha256']==sha(HERE/'user-approval.realization.json')
    assert r['source_identity'] is r['source_seal'] is r['parameter_evidence'] is r['source_parameter_evidence'] is None
    assert len(r['source_files'])==824 and sum(v is None for v in r['source_files'].values())==3
    packages=read(HERE/'packages.expected.json');assert len(packages)==130
    assert len({x['apk_path'] for x in packages})==130 and not {x['apk_path'] for x in packages}&set(r['source_files'])
    for ref in q['programs'].values():assert sha(expand(ref['path']))==ref['sha256']
    for role in ['original_manifest','original_tiers','original_same61b_install_index']:
        ref=q[role];assert sha(expand(ref['path']))==ref['sha256']
    spec=importlib.util.spec_from_file_location('original61b_index_guard',expand(q['programs']['candidate_identity']['path']))
    c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
    proof={'manifest':q['original_manifest'],'tiers':q['original_tiers'],'synthetic':False}
    manifest=expand(proof['manifest']['path']);tiers=expand(proof['tiers']['path']);indexpath=expand(q['original_same61b_install_index']['path'])
    c.validate_round_inputs(proof,manifest,tiers,indexpath)
    index=read(indexpath);key=next(iter(index));rejected=0
    mutations=[]
    foreign=copy.deepcopy(index);foreign[key]['serial']='5ea34a4500000000000000001123012c';mutations.append(foreign)
    drift=copy.deepcopy(index);drift[key]['apk_sha256']='0'*64;mutations.append(drift)
    missing=copy.deepcopy(index);missing.pop(key);mutations.append(missing)
    recordpin=copy.deepcopy(index);recordpin[key]['record_sha256']='0'*64;mutations.append(recordpin)
    with tempfile.TemporaryDirectory(prefix='final61b-offline-refusal-') as temporary:
        for i,bad in enumerate(mutations):
            f=Path(temporary)/str(i);f.write_text(json.dumps(bad))
            try:c.validate_round_inputs(proof,manifest,tiers,f)
            except (ValueError,KeyError,TypeError,OSError):rejected+=1
            else:raise AssertionError('borrowed/drifted/missing index admitted')
    # CLI help runs are local. CLI flags in the handoff are additionally checked against argparse AST.
    argv=read(HERE/'commands.disabled.json')
    for item in argv['commands']:
        tree=ast.parse(expand(q['programs'][item['program']]['path']).read_text())
        options={n.args[0].value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument' and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str)}
        if item['program']=='r5_binary_entry':
            delegated=ast.parse(expand(q['programs']['realization_selfcheck']['path']).read_text())
            options.update(n.args[0].value for n in ast.walk(delegated) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument' and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str))
        assert {x for x in item['argv'] if x.startswith('--')}<=options,item['id']
    result={'status':'OFFLINE_PARAMETER_AND_ORIGINAL_INSTALLED_INPUT_GUARD_PASS','serial':SERIAL,'sameboard_original_install_records':128,'negative_indexes_rejected':rejected,'source_files':824,'packages':130,'unknown_source_controls':3,'actual_fields_null':len(q['actual']),'user_authorization_received':True,'program_pins':len(q['programs']),'command_templates':len(argv['commands']),'device_calls':0,'actual954_compiled_or_observed':False,'actual61b128_executed_by_T0':False,'V2_signed':False}
    print(json.dumps(result));return 0
if __name__=='__main__':raise SystemExit(main())
