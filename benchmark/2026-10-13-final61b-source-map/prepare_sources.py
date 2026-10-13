#!/usr/bin/env python3
"""Original source-files mapping; local-only, always disabled, no transport."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get('WORKSPACES', str(HERE.parents[2])))
MAIN = WS / 'westlake-harness'
V1 = MAIN / 'benchmark/2026-10-12-v1-seal-execution/seal-final-20261013'
F28 = MAIN / 'benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-f28'
REAL = MAIN / 'benchmark/2026-10-12-exact-realization'
SERIAL = '61b0657200000000000000000324012c'
COMPILER_SHA = '58ee3bf945eae2ed69b3b689813a389bc44a3c4786ebda570c2ae724f61b4acb'
MAP_SHA = '79365a800eea63085009231d4d0cf53376037b29990d797b2794f4c1c77542f9'
V1_SHA = '7f5b6f996482149ffd958bcdf55981cdc8ac6e69cb17738a2984153421f72780'
REFERENCE_SHA = 'bf6fbbefc3248ce94416cdac615ef7d784272212e6f0114c434da4079fe975a9'

def need(ok, message):
    if not ok: raise ValueError(message)

def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def expand(path): return Path(str(path).replace('$WORKSPACES', str(WS)))
def portable(path):
    path = Path(path).resolve()
    return '$WORKSPACES/' + str(path.relative_to(WS.resolve())) if path.is_relative_to(WS.resolve()) else str(path)
def pin(path): return dict(path=portable(path), sha256=sha(path))
def checked(ref):
    need(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'typed pin required')
    path = expand(ref['path']); need(path.is_file() and sha(path) == ref['sha256'], 'source SHA drift: ' + str(path))
    return path
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def save(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def inventory(plan, planpath):
    need(sha(V1 / 'source-files.json') == MAP_SHA and sha(V1 / 'seal.json') == V1_SHA, 'original source map/seal pins')
    seal = read(V1 / 'seal.json'); original = read(V1 / 'source-files.json')
    groups = copy.deepcopy(seal['files'])
    files = {target: digest for members in groups.values() for target, digest in members.items()}
    need(len(files) == len(original) == 811 and set(files) == set(original), 'original811 complete file source set')
    mapping = {}
    for target, ref in original.items():
        path = checked(ref); need(ref['sha256'] == files[target], 'original sealed source content differs')
        mapping[target] = pin(path)
    need(len(plan['members']) == 11 and len(plan['binds']) == 7, 'full11 placements/7 binds')
    members = {row['target']: row for row in plan['members']}
    dynamic_controls = {target for target in members if Path(target).name in ('binds.tsv', 'worker.sh')}
    need(len(dynamic_controls) == 2, 'exact two metadata-dependent controls')
    for target, row in members.items():
        # In static mode these two historical-reference bytes MUST NOT become61b expected bytes.
        src = planpath.parent / row['source'].removeprefix('$PACKAGE/') if row['source'].startswith('$PACKAGE/') else expand(row['source'])
        need(src.is_file() and sha(src) == row['sha256'], 'f28 source bytes differ: ' + target)
        mapping[target] = pin(src)
        for entries in groups.values():
            if target in entries: entries[target] = row['sha256']
        groups['overlays'][target] = row['sha256']
    for row in plan['binds']:
        need(row['source'] in mapping and mapping[row['source']]['sha256'] == row['sha256'], 'bind source alias differs')
        mapping[row['target']] = copy.deepcopy(mapping[row['source']])
        for entries in groups.values():
            if row['target'] in entries: entries[row['target']] = row['sha256']
        groups['overlays'][row['target']] = row['sha256']
    files = {target: digest for members in groups.values() for target, digest in members.items()}
    need(set(mapping) == set(files) and len(files) == 824, 'complete824, no APK/source_files mixing')
    baseline = read(MAIN / 'benchmark/2026-10-03-u14-stage-a-plan/inputs/recovery-61b.json')['expected']
    shared = {'/system/android/framework/oh-adapter-runtime.jar', '/system/android/lib64/libandroid.so',
              '/system/android/lib64/liboh_adapter_bridge.so', '/system/android/lib64/liboh_android_runtime.so'}
    need(len(baseline) == 319 and all(t in files for t in baseline) and
         {t for t,h in baseline.items() if files[t] != h} == shared, 'original319315keep+4replace')
    packages = copy.deepcopy(seal['packages'])
    packages.append(dict(package='com.Unity3d.BoatAttackDay', version_code=1, version_name='0.9',
                         apk_path='/data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/base.apk',
                         apk_sha256='8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444'))
    apk = {row['apk_path']: row['apk_sha256'] for row in packages}
    need(len(packages) == len(apk) == 130 and not set(apk) & set(files) and len(set(files) | set(apk)) == 954,
         'complete130 packages and954 union; no exclusions')
    run = [target for target in mapping if target.endswith('/run.sh')]
    need(len(run) == 1, 'one original RouteB run.sh')
    return seal, groups, mapping, packages, dynamic_controls, run[0]

def build(out, composition=None, composition_sha=None):
    need(not out.exists(), 'fresh output required')
    need(bool(composition) == bool(composition_sha), 'composition/path full SHA paired')
    original_request = read(V1 / 'request.61b.sealed.json')
    source_provenance = None
    if composition is None:
        planpath = F28 / 'board61b/provider/r4-reference/plan.disabled.json'
        need(sha(planpath) == REFERENCE_SHA, 'exact reviewed artifact-reference plan')
        plan = read(planpath)
    else:
        need(sha(composition) == composition_sha, 'independent composition SHA differs')
        producer_path = F28 / 'selfcheck/compile_selfcheck.py'
        need(sha(producer_path) == COMPILER_SHA, 'exact landed MAIN compiler')
        producer = load(producer_path, 'final61b_source_producer')
        view, binary, doc = producer.verified(composition)
        qpath = producer.pin(doc['request'], Path(composition).parent); q = producer.read(qpath)
        need(doc['serial'] == q['serial'] == SERIAL, 'actual61b composition required; no5cd/5ea source credit')
        planpath = checked(q['placement_plan']); plan = read(planpath)
        source_provenance = dict(composition=pin(composition), base=q['base'], compiler=pin(producer_path))
    seal, groups, mapping, packages, controls, run = inventory(plan, planpath)
    fixture = copy.deepcopy(mapping)  # Reviewed artifact-reference bytes only, never actual61b table/worker.
    unknown = []
    dynamic = None
    if composition is None:
        for target in sorted(controls):
            mapping[target] = None
            unknown.append(dict(target=target, kind='actual61b-plan-control',
                                needs='fresh actual61b BMS UID and all7 target mode/uid/gid/label, exact T4 table/worker derivation'))
        mapping[run] = None
        unknown.append(dict(target=run, kind='newboot-independent-running-files',
                            needs='actual new boot plus independently bookended host owner/birth/WMS; original realization window CLI'))
    else:
        # Producer verified the original raw source. Derive run bytes through its unchanged original helper.
        realization = producer.pin(q['base']['realization'], qpath.parent)
        proof = binary.original.realization.verify(realization)
        if q.get('running_parameter_evidence') is not None:
            obs = q['running_parameter_evidence']; obsbase = qpath.parent; boot = q['current_boot']
        else:
            observed = producer.pin(q['base']['observation'], qpath.parent)
            obs = producer.read(observed)['parameter_evidence']; obsbase = observed.parent
            boot = producer.read(producer.pin(q['base']['selfcheck'], qpath.parent))['current_boot']
        _, dynamic = binary.original.realization.running_files(proof, obs, obsbase, boot)
        raw = (proof['package'] / 'runtime/run.sh').read_bytes()
        rendered, _ = binary.original.realization.exact_numeric(raw, rb'^export WL_PARENT_ID=([0-9]+)$',
                                        dynamic['parameter_evidence']['window_id'], 'window_id')
        need(hashlib.sha256(rendered).hexdigest() == dynamic['sha256'] and dynamic['target'] == run, 'original run derivation differs')
        candidate = producer.read(producer.pin(doc['seal_candidate'], Path(composition).parent))
        groups = candidate['files']; packages = candidate['packages']
        expected = {target: digest for entries in groups.values() for target, digest in entries.items()}
        need(set(expected) == set(mapping), 'producer complete824 source membership differs')
        for target, ref in mapping.items():
            if target != run: need(ref['sha256'] == expected[target], 'source vs admitted expected SHA: ' + target)
        need(expected[run] == dynamic['sha256'], 'producer run SHA is not independently derived')
    out.mkdir(parents=True)
    if dynamic is not None:
        (out / 'run.sh').write_bytes(rendered); mapping[run] = pin(out / 'run.sh'); save(out / 'run-derivation.json', dynamic)
    save(out / 'source-files.pending.json', mapping)
    save(out / 'source-files.reference-only.json', fixture)
    save(out / 'file-groups.reference-only.json', groups)
    save(out / 'packages.expected.json', packages)
    request = copy.deepcopy(original_request)
    request.update(source_identity=None, source_seal=None, user_approval=None, parameter_evidence=None,
                   source_parameter_evidence=None, source_files=mapping, execution_enabled=False)
    request['parameters'] = dict(request['parameters'], boot_id=None, window_id=None)
    save(out / 'realization.request.pending.json', request)
    save(out / 'snapshot.pending.json', dict(schema='demo-seal-snapshot/v1', serial=SERIAL, mode='pending-not-observed',
            boot_before=None, boot_after=None, file_inventory_complete=False, package_inventory_complete=False,
            files={}, errors=['PENDING actual complete sameboard snapshot/raw fingerprints/APK hashes/nonfile inventories']))
    save(out / 'overlays.pending.json', dict(schema='demo-overlays/v1', seal_stage='v2', items=seal['overlay_deployments'],
                  status='PENDING actual RouteB/Boat full954 capture and independent overlay admission'))
    result = dict(status='DISABLED_SOURCE_MAPPING_NOT_OBSERVED', serial=SERIAL, device_calls=0, execution_enabled=False,
           source_files=824, packages=130, unique_objects=954, static_gaps=[], unknown=unknown,
           source_provenance=source_provenance, original_v1_map=pin(V1 / 'source-files.json'), original_v1_seal=pin(V1 / 'seal.json'),
           reference_plan=pin(planpath), source_files_pin=pin(out / 'source-files.pending.json'),
           original_programs={name:pin(path) for name,path in {'build_seal':MAIN/'benchmark/2026-10-09-demo-baseline/t5/build_seal.py',
               'realization':REAL/'realization.py','sameboard':REAL/'sameboard.py','observations':REAL/'observations.py','seal_checks':REAL/'seal_checks.py'}.items()},
           pending=['61b user unseal/actual install capture and Boat UID','actual plan/table/worker' if composition is None else 'actual candidate deployment',
               'newboot/host-WMS full raw receipt','actual full954 snapshot/raw fingerprints/130APK/nonfile inventories',
               'independent actual Boat overlay admission','outer signoff'],
           notes=['824 file source pins only;130 packages retained via original APK/nonfile chain.',
                  'Reference-only files are historical artifact schema fixtures, not actual61b metadata/boot/installation.',
                  'No5cd full128 added.5ea is current f28 full128 owner.'])
    save(out / 'gaps.json', result); return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--composition',type=Path);parser.add_argument('--composition-sha256')
    args=parser.parse_args()
    try: result=build(args.out,args.composition,args.composition_sha256)
    except (ValueError,KeyError,TypeError,OSError) as error:
        print('REFUSED: '+str(error),file=sys.stderr);return 2
    print(json.dumps(dict(status=result['status'],static_gaps=len(result['static_gaps']),unknown=len(result['unknown']),
                         file_sources=result['source_files'],APK=result['packages'],unique=result['unique_objects'],device_calls=0)))
    return 0

if __name__=='__main__': raise SystemExit(main())
