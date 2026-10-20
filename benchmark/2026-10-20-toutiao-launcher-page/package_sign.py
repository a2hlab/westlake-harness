#!/usr/bin/env python3
"""Offline exact-member host HAP assembly/signing. Never installs or contacts a device."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

INDEX='ets/pages/Index.abc'
META='.pages.info'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(b): return hashlib.sha256(b).hexdigest()
def require(ok, message):
    if not ok: raise ValueError(message)
def payload(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        require(len(names)==len(set(names)), 'DUPLICATE_MEMBERS')
        require(all(not n.startswith('/') and '..' not in Path(n).parts for n in names), 'UNSAFE_MEMBER')
        return {n:z.read(n) for n in names}
def original(path, lock):
    require(sha(path)==lock['original_hap']['sha256'], 'HAP_SHA')
    require(path.stat().st_size==lock['original_hap']['bytes'], 'HAP_SIZE')
    data=payload(path)
    require({n:digest(b) for n,b in data.items()}==lock['original_hap']['members'], 'ORIGINAL_MEMBERS')
    return data

def compiled(folder,lock,here):
    receipt=json.loads((folder/'receipt.json').read_text())
    require(receipt['status']=='EXACT_BASELINE_AND_CANDIDATE_COMPILED','COMPILE_STATUS')
    require(receipt['compiler']['sha256']==lock['compiler_sha256'],'COMPILER_SHA')
    require(receipt['source_pins']==lock['sources'],'COMPILE_SOURCE_PINS')
    for n,h in lock['sources'].items(): require(sha(here/n)==h,'SOURCE_SHA '+n)
    tags=['baseline-EntryAbility','baseline-Index','candidate-Index']
    require(receipt['commands']==[{'tag':n,'rc':0} for n in tags],'COMPILE_COMMANDS')
    expected_raw={f'raw/{tag}.{ext}' for tag in tags for ext in ['argv.json','stdout','stderr','rc']}
    require(set(receipt['raw_pins'])==expected_raw,'RAW_CLOSURE')
    for n,h in receipt['raw_pins'].items(): require(sha(folder/n)==h,'RAW_SHA '+n)
    for tag in tags:require((folder/f'raw/{tag}.rc').read_text().strip()=='0','RAW_RC '+tag)
    require(set(receipt['artifacts'])=={'baseline/EntryAbility.abc','baseline/Index.abc','candidate/Index.abc'},'ABC_CLOSURE')
    for n,info in receipt['artifacts'].items():
        require(sha(folder/n)==info['sha256'] and (folder/n).stat().st_size==info['bytes'],'ABC_SHA '+n)
    require(sha(folder/'baseline/EntryAbility.abc')==lock['original_hap']['members']['ets/entryability/EntryAbility.abc'],'BASELINE_ENTRY')
    require(sha(folder/'baseline/Index.abc')==lock['original_hap']['members'][INDEX],'BASELINE_INDEX')
    require(sha(folder/'candidate/Index.abc')!=lock['original_hap']['members'][INDEX],'NO_PROGRAM_CHANGE')
    return receipt

def compare(before,after,candidate,signed):
    require(set(before)==set(after),'MEMBER_SET')
    require(after[INDEX]==candidate,'CANDIDATE_INDEX')
    allowed={INDEX,META} if signed else {INDEX}
    changed={n for n in before if before[n]!=after[n]}
    require(INDEX in changed and not changed-allowed,'UNEXPECTED_PAYLOAD_CHANGE '+str(sorted(changed)))
    return sorted(changed)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['intake','compiled','profile','signing-dist','signer','java','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args(); here=Path(__file__).resolve().parent;lock=json.loads((here/'inputs.lock.json').read_text())
    before=original(a.intake,lock);cr=compiled(a.compiled,lock,here)
    require(sha(a.profile)==lock['profile_sha256'],'PROFILE_SHA')
    require(sha(a.signer)==lock['signer_sha256'],'SIGNER_SHA')
    for n,h in lock['signing_public_inputs'].items():require(sha(a.signing_dist/n)==h,'PUBLIC_SIGNING_SHA '+n)
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);(out/'raw').mkdir()
    receipt={'status':'INCOMPLETE','device_calls':0,'deployment_accepted':False,'compile_receipt_sha256':sha(a.compiled/'receipt.json'),'input_lock_sha256':sha(here/'inputs.lock.json'),'tools':{'java_sha256':sha(a.java.resolve()),'signer_sha256':sha(a.signer)},'commands':[]}
    def save():(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    save()
    def run(tag,args):
        argv=[str(a.java.resolve()),'-jar',str(a.signer.resolve())]+[str(x) for x in args]
        (out/'raw'/f'{tag}.argv.json').write_text(json.dumps(argv,indent=2)+'\n')
        with (out/'raw'/f'{tag}.stdout').open('wb') as stdout,(out/'raw'/f'{tag}.stderr').open('wb') as stderr:
            r=subprocess.run(argv,stdout=stdout,stderr=stderr)
        (out/'raw'/f'{tag}.rc').write_text(str(r.returncode)+'\n')
        receipt['commands'].append({'tag':tag,'rc':r.returncode});save();require(r.returncode==0,'COMMAND_FAILED '+tag)
    shutil.copyfile(a.intake,out/'rollback-exact.hap')
    run('verify-original',['verify-app','-inFile',out/'rollback-exact.hap','-outCertChain',out/'original.cer','-outProfile',out/'original.p7b'])
    require(sha(out/'original.p7b')==lock['profile_sha256'],'EXTRACTED_PROFILE')
    require(sha(out/'original.cer')==lock['original_cert_chain_sha256'],'ORIGINAL_CERT_CHAIN')
    run('verify-profile',['verify-profile','-inFile',out/'original.p7b','-outFile',out/'profile-verified.json'])
    require(json.loads((out/'profile-verified.json').read_text())['verifiedPassed'] is True,'PROFILE_VERIFICATION')
    candidate=(a.compiled/'candidate/Index.abc').read_bytes()
    unsigned=out/'candidate-unsigned.hap'
    with zipfile.ZipFile(unsigned,'x',zipfile.ZIP_STORED) as z:
        for n,b in sorted(before.items()):
            item=zipfile.ZipInfo(n,(1980,1,1,0,0,0));item.create_system=3;item.external_attr=0o100644<<16
            z.writestr(item,candidate if n==INDEX else b)
    compare(before,payload(unsigned),candidate,False)
    run('sign-candidate',['sign-app','-mode','localSign','-keyAlias','openharmony application release','-appCertFile',a.signing_dist/'OpenHarmonyApplication.pem','-profileFile',out/'original.p7b','-inFile',unsigned,'-outFile',out/'candidate-signed.hap','-compatibleVersion','20','-signCode','1','-signAlg','SHA256withECDSA','-keystoreFile',a.signing_dist/'OpenHarmony.p12','-keyPwd','123456','-keystorePwd','123456'])
    # Password above belongs only to the pinned public upstream development key.
    run('verify-candidate',['verify-app','-inFile',out/'candidate-signed.hap','-outCertChain',out/'candidate.cer','-outProfile',out/'candidate.p7b'])
    require((out/'candidate.cer').read_bytes()==(out/'original.cer').read_bytes(),'CERTIFICATE_DRIFT')
    require((out/'candidate.p7b').read_bytes()==(out/'original.p7b').read_bytes(),'PROFILE_DRIFT')
    after=payload(out/'candidate-signed.hap');changed=compare(before,after,candidate,True)
    receipt.update(status='OFFLINE_SIGNED_CANDIDATE_VERIFIED_NOT_DEPLOYED',changed_members=changed,unchanged_members=sorted(set(before)-set(changed)),members={n:{'before_sha256':digest(before[n]),'after_sha256':digest(after[n])} for n in sorted(before)},artifacts={n:{'sha256':sha(out/n),'bytes':(out/n).stat().st_size} for n in ['candidate-signed.hap','candidate-unsigned.hap','rollback-exact.hap','original.cer','candidate.cer','original.p7b','candidate.p7b']},raw_pins={str(f.relative_to(out)):sha(f) for f in sorted((out/'raw').iterdir())})
    save();print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
