#!/usr/bin/env python3
"""Bind collected 61b data locally. No HDC, approval, lock or device actions."""
import argparse
import hashlib
import json
import re
from pathlib import Path

D=Path(__file__).resolve().parent
SERIAL='61b0657200000000000000000324012c'
RT='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
CFG='91e31b959995772d305d5b034c9a5ebdbf3f8371495e3964185ada928db4ee2e'
HAP='b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0'
ORIGIN='benchmark/2026-10-20-t30-request-recovery/deployment/final-01'
sha=lambda b:hashlib.sha256(b).hexdigest()

def run_wid(data,value):
    matches=list(re.finditer(rb'^export WL_PARENT_ID=([0-9]+)\n',data,re.M))
    assert len(matches)==1 and 0<int(matches[0][1])<2147483648,'one positive WID'
    m=matches[0]
    return data[:m.start()]+f'export WL_PARENT_ID={value}\n'.encode()+data[m.end():],int(m[1])

def validate(f,run,repo):
    assert f['serial']==SERIAL and f['uid']==20011206 and f['runtime']==RT
    assert f['boot_before']==f['boot_after'] and re.fullmatch('[0-9a-f-]{36}',f['boot_before'])
    assert f['cfg_sha256']==CFG and f['hap_sha256']==HAP
    assert f['compat_absent'] is True
    assert f['power']=={'timeout':30000,'override':86400000} and f['debug_get_rc']==106
    original,wid=run_wid(run,33)
    assert sha(original)=='d3518cefb37a81be01f386ac7ac54193ab47da3475bdb00d16803853c80077d4','foreign baseline run'
    assert sha(run)==f['run_sha256'] and wid==f['wid']==f['parent_wid']
    assert run.count(b'export ASX_RUNTIME_OWNER_UID=20011206\n')==1
    reference=json.loads((repo/'benchmark/2026-10-20-t33-demo61b-host/static/reference.json').read_text())
    assert f['controls']==reference['controls'],'61b control drift'
    assert f['access_token_id']==reference['accessTokenId'],'token drift'
    for path,digest in reference['runtime'].items():
        if path.endswith('/run.sh'):continue
        assert f['runtime_sha256'][path]==digest,('baseline drift',path)
    dirs=f['directory_identities']
    assert set(dirs)=={RT,RT+'/lib',RT+'/lib/arm64-v8a',RT+'/webview-t-lib'}
    assert len(set(dirs.values()))==4,'target directory aliases'
    assert set(f['protected_directories'])=={'/system/lib64','/data/local/tmp/asx','/data/local/tmp/asx/lib','/data/local/tmp/asx/lib/arm64-v8a','/data/local/tmp/asx/webview-t-lib'}
    for identity in dirs.values():assert re.fullmatch('[0-9]+:[0-9]+',identity)
    for identity in f['protected_directories'].values():
        assert identity is None or (re.fullmatch('[0-9]+:[0-9]+',identity) and identity not in dirs.values()),'shared directory alias'
    assert f['providers']==[
        {'path':'/system/lib64/libOpenSLES.so','sha256':'05d8ac90dbced47c8b47275a5d978bc922d4d8f6f84cd3df1b456633ae6d1100'},
        {'path':RT+'/liblog.so','sha256':'d8ad176b41b820a4868b74394188429ad2dc69025661d320d0986dd713048ca4'}], 'provider differs from accepted candidate; review needed'
    assert f['network_sha256']=='f6c354d1513071533fddcc91749f44e57a626177a584fb1bb9f48bf6446ef01e'
    assert f['parent']['uid']==0 and f['host']['uid']==20011206
    assert f['parent']['exe_sha256']=='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
    for obj in (f['parent'],f['host']):
        assert type(obj['pid']) is int and obj['pid']>1 and type(obj['birth']) is int and obj['birth']>0
        assert obj['tracer']==0 and obj['state'] not in ('Z','X','x')
    assert f['parent']['ppid']==1
    assert re.fullmatch(r'mnt:\[[0-9]+\]',f['parent_mnt'])
    assert f['physical_private_files_equal'] is True
    assert f['evidence'] and all(re.fullmatch('[0-9a-f]{64}',v['sha256']) for v in f['evidence'])
    return wid

def prepare(f,run,repo,out):
    wid=validate(f,run,repo)
    template=(repo/ORIGIN/'run5cd.after.wid29.reference.sh').read_bytes()
    assert sha(template)=='11d3d671bd501205a98ee386e64bf1274501d0458a4cdb35945f7424a388244a'
    assert template.count(b'export ASX_RUNTIME_OWNER_UID=20011300\n')==1
    after=run_wid(template.replace(b'export ASX_RUNTIME_OWNER_UID=20011300\n',b'export ASX_RUNTIME_OWNER_UID=20011206\n'),wid)[0]
    out.mkdir(parents=True,exist_ok=False)
    dump=lambda name,obj:(out/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    dump('fresh.json',f)
    (out/'run61b.before.reference.sh').write_bytes(run)
    (out/'run61b.after.reference.sh').write_bytes(after)
    for name in ('bridge-candidate.json','shim-candidate.json','executor-source-pins.json'):
        (out/name).write_bytes((D/name).read_bytes())
    # Review of these files is separate from creating an unsigned bound package.
    params={'status':'FRESH_DATA_BOUND_NOT_AUTHORIZED','serial':SERIAL,'uid':20011206,'runtime':RT,
            'directory_identities':f['directory_identities'],'protected_directories':f['protected_directories'],
            'run_derivation':{'wid':wid,'before_sha256':sha(run),'after_sha256':sha(after)}}
    dump('parameters.json',params)
    dump('readonly-inputs.json',{'controls':f['controls'],'providers':f['providers']})
    ad={'deployment_scope':'T34_61B_VIDEO','approved_by':None,'signed_at':None,'serial':SERIAL,'uid':20011206,
        'holder':None,'window_start':None,'boot':None,'parent_mnt':None,'parent':None,'host':None,'physical_only':False,
        'wid':wid,'cfg_sha256':CFG,'bridge_metadata':'644:20011206:20011206','shim_metadata':'755:20011206:20011206',
        'bridge_label':'u:object_r:appdat:s0','shim_label':'u:object_r:appdat:s0',
        'providers':f['providers'],'directory_identities':f['directory_identities'],'protected_directories':f['protected_directories'],
        'executor_sha256':sha((D/'executor61b.py').read_bytes())}
    for key,name in [('bridge_candidate','bridge-candidate'),('shim_candidate','shim-candidate'),('parameters','parameters'),
                     ('source_pins','executor-source-pins'),('readonly_inputs','readonly-inputs'),('fresh_data','fresh')]:
        ad[key+'_sha256']=sha((out/(name+'.json')).read_bytes())
    dump('admission.template.json',ad)
    return params

def main():
    p=argparse.ArgumentParser();p.add_argument('--fresh',type=Path,required=True);p.add_argument('--run',type=Path,required=True)
    p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    print(json.dumps(prepare(json.loads(a.fresh.read_text()),a.run.read_bytes(),a.repo,a.out),indent=2))
if __name__=='__main__':main()
