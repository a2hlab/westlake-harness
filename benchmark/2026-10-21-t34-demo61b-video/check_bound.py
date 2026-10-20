#!/usr/bin/env python3
"""Thin selectors for bound inputs, actual offline refusals and pending human evidence."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

D=Path(__file__).resolve().parent
sys.path.insert(0,str(D/'deployment'))
import prepare_data as pd
B=D/'bound-data-01'
MAIN=Path(os.environ.get('T34_MAIN',str(D.parents[1])))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def debug_semantics(f):
    assert f['debug_get_rc']==106 and f['debug_get_process_rc']==0
    assert f['debug_get_raw_line']=='Get parameter "debug.ttplayer.log.enable" fail! errNum is:106!'
    assert f['debug_get_rc_semantics']=='param body errNum; legacy field name, not subprocess rc'

def preflight():
    assert sha(D/'deployment/executor61b.py')=='d75ecd42714f03b52db167c0978ec14c3ed7bcb5ad7e96c98be0d5b594c7060e'
    f=json.loads((B/'fresh.json').read_text());debug_semantics(f)
    pd.validate(f,(B/'run61b.before.reference.sh').read_bytes(),MAIN)
    ad=json.loads((B/'admission.template.json').read_text())
    for key in ('approved_by','signed_at','holder','window_start','boot','parent','host','parent_mnt'):
        assert ad[key] is None,('unsigned data must not fill/sign new window',key)
    for key,name in [('bridge_candidate','bridge-candidate'),('shim_candidate','shim-candidate'),('parameters','parameters'),
                     ('source_pins','executor-source-pins'),('readonly_inputs','readonly-inputs'),('fresh_data','fresh')]:
        assert ad[key+'_sha256']==sha(B/(name+'.json')),(key,'pin drift')
    params=json.loads((B/'parameters.json').read_text())
    assert sha(B/'run61b.before.reference.sh')==params['run_derivation']['before_sha256']
    assert sha(B/'run61b.after.reference.sh')==params['run_derivation']['after_sha256']
    template=(MAIN/pd.ORIGIN/'run5cd.after.wid29.reference.sh').read_bytes()
    expected=pd.run_wid(template.replace(b'export ASX_RUNTIME_OWNER_UID=20011300\n',b'export ASX_RUNTIME_OWNER_UID=20011206\n'),f['wid'])[0]
    assert expected==(B/'run61b.after.reference.sh').read_bytes()
    assert len(f['field_sources'])==82
    for values in f['field_sources'].values():
        assert values and all(v in f['evidence'] for v in values)
    for name in ('bridge-candidate.json','shim-candidate.json'):
        c=json.loads((B/name).read_text())
        for ref in c['production_refs']:assert sha(MAIN/ref['path'])==ref['sha256'],ref['path']
    for path,digest in json.loads((B/'executor-source-pins.json').read_text()).items():
        assert sha(MAIN/path)==digest,path
    return {'selector':'demo61b_video_preflight','offline_check':'PASS','human':'PENDING_REVIEW',
            'device_calls':0,'approved_by':None,'field_sources':82}

def negative():
    f=json.loads((B/'fresh.json').read_text())
    for key,value in [('debug_get_rc',0),('debug_get_process_rc',106)]:
        bad=copy.deepcopy(f);bad[key]=value
        try:debug_semantics(bad)
        except AssertionError:pass
        else:raise AssertionError('semantic errno/process rc conflation accepted')
    result=subprocess.run([sys.executable,str(D/'test_offline.py')],env=dict(os.environ,T34_MAIN=str(MAIN)))
    assert result.returncode==0,'actual derived executor rejection suite'
    return {'selector':'demo61b_video_negative','offline_check':'PASS','additional_semantic_negatives':2,'device_calls':0}

def evidence():
    obj=json.loads((D/'fresh-evidence-status.json').read_text())
    assert obj['status']=='PENDING_REVIEW' and obj['visual_acceptance']=='NOT_PERFORMED'
    assert obj['window_admission']=='UNSIGNED' and obj['retained_candidate'] is None
    assert obj['screenshots']=='unknown' and obj['new_61b_audio_confirmation'] is None
    return {'selector':'demo61b_video_evidence','structure_check':'PASS','human':'PENDING_REVIEW',
            'visual_pass':False,'device_calls':0}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('selector',choices=['preflight','negative','evidence']);a=p.parse_args()
    print(json.dumps({'preflight':preflight,'negative':negative,'evidence':evidence}[a.selector](),indent=2))
