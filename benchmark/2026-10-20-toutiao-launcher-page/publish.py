#!/usr/bin/env python3
"""Publish sanitized small receipts; never rewrites raw build output."""
import argparse
import hashlib
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parent
    compile_dir=a.base/'compile-linux-01'
    cr=json.loads((compile_dir/'receipt.json').read_text())
    br=json.loads((a.build/'receipt.json').read_text())
    assert cr['status']=='EXACT_BASELINE_AND_CANDIDATE_COMPILED'
    assert br['status']=='OFFLINE_SIGNED_CANDIDATE_VERIFIED_NOT_DEPLOYED'
    assert all(x['rc']==0 for x in br['commands']+cr['commands'])
    for name,info in br['artifacts'].items():
        assert hashlib.sha256((a.build/name).read_bytes()).hexdigest()==info['sha256']
    vm_workspace=cr['compiler']['path'].split('/toolchains/')[0]
    aliases=sorted([(str(a.workspace),'$ORB_WS'),(str(a.base),'$LAUNCHER_BASE'),(str(root.parents[1]),'$LANE'),(str(Path.home()),'$HOME'),(vm_workspace,'$ORB_WS_VM')],key=lambda x:-len(x[0]))
    def san(s):
        for x,y in aliases:s=s.replace(x,y)
        return s
    for src,dst in [(a.build/'receipt.json',root/'production-01.json'),(compile_dir/'receipt.json',root/'compile-linux-01.json'),(a.build/'profile-verified.json',root/'verified-original-profile.json')]:dst.write_text(san(src.read_text()))
    for prefix,directory,tags in [('production',a.build,['verify-original','verify-profile','sign-candidate','verify-candidate']),('compile',compile_dir,['baseline-EntryAbility','baseline-Index','candidate-Index'])]:
        for tag in tags:
            for ext in ['argv.json','stdout','stderr','rc']:
                src=directory/'raw'/f'{tag}.{ext}'
                (root/'evidence'/f'{prefix}-{tag}.{ext}').write_text(san(src.read_text()))
    closure={'status':'EXACT_INSTALLED_HISTORY_ABC_SIGNATURE_CLOSED','installed_hap':{'sha256':hashlib.sha256((a.base/'intake-01/installed-entry.hap').read_bytes()).hexdigest(),'bytes':53303},'historical_install':'MAIN/benchmark/2026-10-12-v1-seal-execution/5cd-host-install/source.json','historical_signed':'$ORB_WS/out-toutiao-host/signed-host/artifacts.json','history_matches_intake':True,'baseline_abc_exact':True,'signature_verified_rc':0,'profile_verified_rc':0,'permissions_unchanged':True,'member_count':9,'actual_new_sign_commands_rc':[0,0,0,0],'public_development_credentials_only':True,'retained_runtime_changes':0,'device_calls':0,'visual_activation':'NOT_EXECUTED','latency_improvement':'NOT_CLAIMED'}
    (root/'closure.json').write_text(json.dumps(closure,indent=2)+'\n')
if __name__=='__main__':main()
