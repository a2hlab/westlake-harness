#!/usr/bin/env python3
"""Publish the v3 matrix, its delta and strict gate verdict without editing approvals."""
import collections,importlib.util,json,subprocess
from pathlib import Path
from scan_jni import HERE,sha,REPO,PACKAGES
from scan_apps import load_apps
from registration_sources import AOSP
from finalize_v3 import OUT,read,dump,csvwrite

def main():
    current=read(OUT/'jni-results.json');old=read(OUT/'evidence/v2-jni-results.json.gz')
    spec=importlib.util.spec_from_file_location('jni_gate_v3',REPO/'scripts/lab/jni_gate.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    approved=read(HERE/'jni-allowlist.json')
    if approved!=read(OUT/'evidence/v2-jni-allowlist.json.gz'):raise ValueError('approved exceptions changed during scan; do not overwrite')
    called=collections.defaultdict(set)
    for app in load_apps():
        for call in app['native_calls']:called[call['id']].add(app['key'])
    matrix=[];deltas=[];unknown=[];summary={};blockers=[]
    for gen,result in current.items():
        old_methods={m['id']:m for m in old[gen]['methods']}
        newly_registered=[]
        for m in result['methods']:
            row={'generation':gen,'class':m['class'],'method':m['method'],'signature':m['signature'],
                 'id':m['id'],'status':m['status'],'declaration':m['declaration'],'reason':m['reason'],'evidence':m['evidence'],
                 'app_direct_call_count':len(called[m['id']]),'app_direct_callers':sorted(called[m['id']])}
            matrix.append(row)
            if old_methods[m['id']]['status']!=m['status']:
                deltas.append({**row,'old_status':old_methods[m['id']]['status']})
                if m['status']=='registered':newly_registered.append(m['id'])
            if m['status']=='unknown':
                unknown.append({**row,'candidate_compiled_tables':len(m['evidence']),
                    'defer_reason':'Compiled name/descriptor candidates exist, but class/source/function proof is incomplete.' if m['evidence'] else 'No resolved compiled native table/export; absence is not evidence of missing dynamic binding.'})
        now=gate.evaluate(result,approved);before=gate.evaluate(old[gen],approved)
        methods={m['id']:m for m in result['methods']}
        for b in now['blockers']:
            m=methods[b['method']]
            blockers.append({'generation':gen,'method':b['method'],'status':b['status'],
                'app_direct_callers':sorted(called[m['id']]),'candidate_compiled_tables':len(m['evidence']),
                'reason':b['reason'],'matrix_evidence':f'jni-results.json#/{gen}/methods (id={m["id"]})'})
        dump(OUT/('gate-'+gen+'.json'),now)
        summary[gen]={'counts':result['counts'],'old_counts':old[gen]['counts'],'newly_registered':len(newly_registered),
            'newly_registered_app_direct':sum(bool(called[mid]) for mid in newly_registered),
            'gate_before':{k:v for k,v in before.items() if k not in {'blockers','invalid_approved_exceptions'}},
            'gate_after':{k:v for k,v in now.items() if k not in {'blockers','invalid_approved_exceptions'}},
            'remaining_app_direct_unknown':sum(m['status']=='unknown' and bool(called[m['id']]) for m in result['methods'])}
    fields=['generation','class','method','signature','status','app_direct_call_count','app_direct_callers','declaration','reason','evidence']
    csvwrite(OUT/'jni-matrix.csv',matrix,fields);csvwrite(HERE/'jni-matrix.csv',matrix,fields)
    csvwrite(OUT/'jni-delta.csv',deltas,['generation','id','old_status','status','app_direct_call_count','app_direct_callers','evidence'])
    unknown.sort(key=lambda r:(not r['app_direct_call_count'],-r['app_direct_call_count'],r['generation'],r['id']))
    csvwrite(OUT/'jni-unknown.csv',unknown,['generation','id','app_direct_call_count','app_direct_callers','candidate_compiled_tables','defer_reason','evidence'])
    csvwrite(OUT/'jni-blockers.csv',blockers,['generation','method','status','app_direct_callers','candidate_compiled_tables','reason','matrix_evidence'])
    dump(HERE/'jni-results.json',current)
    # Source version is framework-specific: it must not be inferred from ART's version.
    version={'root':str(AOSP),
        'head':subprocess.check_output(['git','-C',str(AOSP),'rev-parse','HEAD'],text=True).strip(),
        'tags':subprocess.check_output(['git','-C',str(AOSP),'tag','--points-at','HEAD'],text=True).splitlines(),
        'scope':['core/jni','libs/hwui/jni','media/jni','opengl/jni','bms/src/adapter/framework'],
        'basis':'Local frozen source slice. Each registered row additionally requires a matching compiled ELF table/function and STT_FILE basename; tag alone proves no implementation.',
        'remote_access':'ssh hw248 denied by sandbox; no network fetch used'}
    dump(OUT/'evidence/aosp-provenance.json',version)
    dump(OUT/'jni-summary.json',summary)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
