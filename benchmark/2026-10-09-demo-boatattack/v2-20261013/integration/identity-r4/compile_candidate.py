"""Local candidate identity/smoke compiler; missing deployment inputs reject."""
import argparse, copy, json
from pathlib import Path
import candidate_identity as c


def build(request, out):
    c.need(not out.exists(),'fresh output required')
    base=c.read(c.pinned(request['baseline']))['expected'];c.need(len(base)==319,'319 baseline required')
    c.need(c.pinned(request['baseline']).resolve()==c.BASE.resolve(),'wrong baseline source')
    extras=request['additional_files']; protected=c.read(c.pinned(request['protected_files']))
    c.valid_rows(protected)
    current_cfg=c.pinned(request['current_cfg']).read_bytes()
    c.need(c.sha(c.pinned(request['current_cfg']))=='7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1','CURRENT v3 cfg required')
    cfg_target='/system/etc/init/00_westlake_u13_recover-v3.cfg'
    expected={**base,**c.CHANGES}
    c.need(len({r['target'] for r in extras})==len(extras),'duplicate extra')
    for row in extras:
        c.need(row['target'] not in expected,'overlap baseline');c.need(c.sha(c.pinned(row['source']))==row['sha256'],'source SHA');expected[row['target']]=row['sha256']
    runtime,boot=c.parts({p:expected[p] for p in base})
    proof={'schema':'boat-candidate-identity/v4','status':'candidate/not_sealed','execution_enabled':False,'serial':request['serial'],'baseline':request['baseline'],'protected_files':request['protected_files'],'current_cfg':request['current_cfg'],'replacements':{p:{'before':base[p],'after':h} for p,h in c.CHANGES.items()},'additional_files':extras,'expected':expected,'generation_sha256':None,'absent_files':request['absent_files'],'placement_plan':request['placement_plan'],'r4_freeze':request['r4_freeze'],'fingerprints':{'runtime_sha256':c.fp(runtime),'boot_sha256':c.fp(boot)},'programs':{'identity':c.pin(c.HERE/'candidate_identity.py'),'reader':c.pin(c.UPSTREAM),'compiler':c.pin(Path(__file__)),'absence_reader':c.pin(c.HERE/'absence_reader.py')},'request':c.pin(request['_request_path'])}
    proof['generation_sha256']=c.generation(proof)
    c.validate(proof)
    smoke=copy.deepcopy(c.read(c.pinned(request['baseline_smoke'])))
    c.need(smoke['expect']=={'runtime_fp':'452447a4a0ba','boot_fp':'ee927db88a67'},'unknown smoke base')
    for target,old in smoke['probe']['files'].items():c.need(base.get(target)==old,'smoke before SHA mismatch')
    smoke['expect']={'runtime_fp':c.fp(runtime)[:12],'boot_fp':c.fp(boot)[:12]}
    smoke['probe']['files']={target:expected[target] for target in smoke['probe']['files']}
    smoke['probe']['files'].update(c.CHANGES)
    # The legacy short fields stay compatible; the candidate gate checks full digest/membership.
    smoke['_comment']='V2 exact candidate smoke; all original groups/fixes/probe predicates retained. Full identity gate is separately pinned.'
    out.mkdir(parents=True)
    (out/'smoke.json').write_text(json.dumps(smoke,indent=2)+'\n');proof['smoke']=c.pin(out/'smoke.json');proof['baseline_smoke']=request['baseline_smoke']
    (out/'candidate-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--request',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    req=c.read(a.request);req['_request_path']=a.request;d=build(req,a.out)
    print(json.dumps({'status':'PREPARED_DISABLED','proof_sha256':c.sha(a.out/'candidate-proof.json'),'generation_sha256':d['generation_sha256'],'paths':len(d['expected']),'remote_writes':0}))
if __name__=='__main__':main()
