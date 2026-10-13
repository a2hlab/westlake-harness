#!/usr/bin/env python3
"""Actual original CLI ABI replay over explicitly synthetic source-only fixtures.
No fixture is an observed snapshot, overlay admission, deployment, or signed seal.
"""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import prepare_sources as p

def call(argv, label, out):
    result = subprocess.run(argv, capture_output=True)
    (out / (label + '.stdout.txt')).write_bytes(result.stdout)
    (out / (label + '.stderr.txt')).write_bytes(result.stderr)
    receipt = dict(argv=argv, return_code=result.returncode,
                   stdout_sha256=p.sha(out / (label + '.stdout.txt')),
                   stderr_sha256=p.sha(out / (label + '.stderr.txt')), device_calls=0)
    return receipt

def build(prepared, out):
    p.need(not out.exists(), 'fresh CLI fixture output'); out.mkdir(parents=True)
    groups = p.read(prepared / 'file-groups.reference-only.json')
    sources = p.read(prepared / 'source-files.reference-only.json')
    packages = p.read(prepared / 'packages.expected.json')
    snapshot = p.read(p.V1 / 'capture/snapshot.json')
    snapshot.update(synthetic=True, fixture_only=True,
                    fixture_claim='SOURCE_SCHEMA_ONLY_NO_ACTUAL_F28_OR_NEW61B_BOOT_OBSERVATION',
                    files=groups, packages=packages, apk_hashes={r['apk_path']:r['apk_sha256'] for r in packages})
    snapshot['fingerprint_lines'] = {g:[h+'  '+t for t,h in groups[g].items()] for g in ('runtime','boot')}
    snapshot.pop('expected_fingerprints', None)
    overlay = p.read(p.V1 / 'overlays.json'); overlay.update(seal_stage='v2', synthetic=True, fixture_only=True)
    reference = p.read(p.F28 / 'board61b/provider/r4-reference/plan.disabled.json')
    p.save(out / 'NOT_AN_ADMISSION.json', dict(synthetic=True, fixture_only=True, admitted=False,
                    status='SCHEMA_TYPED_PIN_ONLY_NOT_ACTUAL_ADMISSION',execution_enabled=False))
    for row in overlay['items']:
        if row['id']=='boatattack':
            row.clear(); row.update(id='boatattack',state='active',package='com.Unity3d.BoatAttackDay',
                apk_sha256=next(r['apk_sha256'] for r in packages if r['package']=='com.Unity3d.BoatAttackDay'),
                version_code=1,version_name='0.9',source=p.pin(p.F28/'board61b/provider/r4-reference/plan.disabled.json'),
                rollback=p.pin(p.F28/'board61b/provider/installer.py'),admission=p.pin(out/'NOT_AN_ADMISSION.json'),
                files=[dict(target=r['target'],sha256=r['sha256'],role='candidate_bind' if r in reference['binds'] else 'candidate_placement') for r in reference['members']+reference['binds']])
    p.save(out/'snapshot.SYNTHETIC.fixture.json',snapshot);p.save(out/'overlays.SYNTHETIC.fixture.json',overlay)
    sealpath=out/'seal.UNSIGNED.SYNTHETIC.fixture.json'
    sealargv=[sys.executable,str(p.MAIN/'benchmark/2026-10-09-demo-baseline/t5/build_seal.py'),
         '--snapshot',str(out/'snapshot.SYNTHETIC.fixture.json'),'--overlays',str(out/'overlays.SYNTHETIC.fixture.json'),
         '--manifest',str(p.MAIN/'benchmark/2026-10-09-demo-baseline/demo-manifest.json'),'--out',str(sealpath)]
    reports={'build_seal_fixture':call(sealargv,'build-seal-fixture',out)}
    p.need(reports['build_seal_fixture']['return_code']==0,'original build_seal fixture rejected')
    seal=p.read(sealpath);files={t:h for rows in seal['files'].values() for t,h in rows.items()}
    p.need(len(files)==824 and len(seal['packages'])==130 and len(set(files)|{r['apk_path'] for r in seal['packages']})==954,
           'original CLI lost complete file/package membership')
    request=p.read(p.V1/'request.61b.sealed.json')
    request.update(source_identity=dict(kind='seal',**p.pin(sealpath)),source_seal=p.pin(sealpath),source_files=sources,
           execution_enabled=False,synthetic=True,fixture_only=True,
           fixture_claim='OLD_REAL9F_WMS_FOR_SCHEMA_ABI_ONLY_NOT_NEW_F28_OBSERVATION_OR_61B_UNSEAL')
    p.save(out/'realization.SYNTHETIC.fixture.request.json',request)
    argv=[sys.executable,str(p.REAL/'realization.py'),'compile','--request',str(out/'realization.SYNTHETIC.fixture.request.json'),
          '--out',str(out/'realization.SYNTHETIC.fixture')]
    reports['realization_fixture']=call(argv,'realization-fixture',out)
    p.need(reports['realization_fixture']['return_code']==0,'original realization fixture rejected')
    proof=p.read(out/'realization.SYNTHETIC.fixture/realization.json')
    p.need(len(proof['files'])==824 and proof['execution_enabled'] is False and proof['restore_allowed'] is False
           and proof['signature'] is None,'fixture unexpectedly enabled/signed or reduced')
    reports['build_seal_pending']=call([sys.executable,str(p.MAIN/'benchmark/2026-10-09-demo-baseline/t5/build_seal.py'),
        '--snapshot',str(prepared/'snapshot.pending.json'),'--overlays',str(prepared/'overlays.pending.json'),
        '--manifest',str(p.MAIN/'benchmark/2026-10-09-demo-baseline/demo-manifest.json'),'--out',str(out/'MUST_NOT_EXIST.seal.json')],
        'build-seal-pending',out)
    reports['realization_pending']=call([sys.executable,str(p.REAL/'realization.py'),'compile',
        '--request',str(prepared/'realization.request.pending.json'),'--out',str(out/'MUST_NOT_EXIST.realization')],
        'realization-pending',out)
    p.need(reports['build_seal_pending']['return_code']==reports['realization_pending']['return_code']==2,
           'pending actual inputs did not refuse')
    p.need(not (out/'MUST_NOT_EXIST.seal.json').exists() and not (out/'MUST_NOT_EXIST.realization').exists(),
           'pending made trusted-looking output')
    result=dict(status='CLI_COMPATIBILITY_ONLY_SYNTHETIC_NOT_DEPLOYABLE',synthetic=True,device_calls=0,
                source_files=824,packages=130,total_objects=954,reports=reports,
                actual_runtime_pass=False,actual_newboot=None,actual_overlay_admission=None,signature=None,
                note='Original CLIs support full954 source shape without edits. Fixture oldWMS/reference-table controls are NOT61b candidate evidence. Actual pending requests correctly refuse.')
    p.save(out/'receipt.json',result);return result

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--prepared',type=Path,required=True);a.add_argument('--out',type=Path,required=True);q=a.parse_args()
    try:r=build(q.prepared.resolve(),q.out.resolve())
    except (ValueError,KeyError,TypeError,OSError) as e:print('REFUSED '+str(e),file=sys.stderr);return 2
    print(json.dumps(dict(status=r['status'],cli_rc={k:v['return_code'] for k,v in r['reports'].items()},device_calls=0)));return 0

if __name__=='__main__':raise SystemExit(main())
