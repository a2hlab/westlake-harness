"""Same-board f28 complete planned identity; read-only runtime gate, never a seal signer."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get('WORKSPACES', str(HERE.parents[5])))
MAIN = WS / 'westlake-harness'
SERIAL = '61b0657200000000000000000324012c'
BASE = MAIN / 'benchmark/2026-10-03-u14-stage-a-plan/inputs/recovery-61b.json'
UPSTREAM = MAIN / 'benchmark/2026-10-09-demo-baseline/t3/verify_identity.py'
LEGACY = WS / 'westlake-harness-bms/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/identity-r4/candidate_identity.py'
LEGACY_SHA = '9cdea3d175c2aa8b17b7f9039b2d98cfc91d6034288f3fea61bd3f84224c8c18'
READER_SHA = '929ca2058a55700f93697d00095153224422cfb5a74cfb08d9a5cf3baee17cc3'
V1_SHA = '7f5b6f996482149ffd958bcdf55981cdc8ac6e69cb17738a2984153421f72780'
MANIFEST = MAIN / 'benchmark/2026-10-09-demo-baseline/demo-manifest.json'
TIERS = MAIN / 'benchmark/2026-10-09-demo-baseline/t4/shot-tiers.json'
BASE_SMOKE = MAIN / 'benchmark/2026-10-03-u13-stage-b/61b/smoke-61b.json'
MANIFEST_SHA = '7a2627326cb536bc8b0ee35587827999f448f827a91e22bdc663809767d82933'
TIERS_SHA = '0cbe939161fcf3ca1d4c53933016feb36f75ca8226205110da9ee3129d6c07b2'
BASE_SMOKE_SHA = 'a5ef612db23dd69f64db3239335b888b6d289710d3d29fa32bada72580c6a0e1'
SELFCHECK_COMPILER_SHA = '58ee3bf945eae2ed69b3b689813a389bc44a3c4786ebda570c2ae724f61b4acb'
SCHEMA = 'boat-routeb-present-f28-candidate-identity/v1'
RUNTIME = '/system/android/lib64/liboh_android_runtime.so'
F28 = 'f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0'
META = ('mode', 'uid', 'gid', 'label')
BOAT_APK = '/data/app/el1/bundle/public/com.Unity3d.BoatAttackDay/android/base.apk'
BOAT_SHA = '8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444'
ROUTEB = '/system/etc/init/01_westlake_u13_toutiao.cfg'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def expand(path):
    return Path(os.path.expandvars(str(path).replace('$WORKSPACES', str(WS))))


def portable(path):
    path = Path(path).resolve()
    if path.is_relative_to(WS.resolve()):
        return '$WORKSPACES/' + str(path.relative_to(WS.resolve()))
    return str(path)


def pin(path):
    return {'path': portable(path), 'sha256': sha(path)}


def pinned(ref):
    need(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'typed independent pin required')
    need(isinstance(ref['path'], str) and re.fullmatch('[0-9a-f]{64}', str(ref['sha256'])), 'full pin required')
    path = expand(ref['path'])
    need(path.is_file() and sha(path) == ref['sha256'], 'source pin drift: ' + str(path))
    return path


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def legacy():
    need(sha(LEGACY) == LEGACY_SHA, 'original identity helper drift')
    return module(LEGACY, 'original_identity_helpers_61b')


def shared_changes():
    rows = dict(legacy().CHANGES)
    rows[RUNTIME] = F28
    return rows


def valid_rows(rows):
    legacy().valid_rows(rows)


def parts(rows):
    return legacy().parts(rows)


def fp(rows):
    return legacy().fp(rows)


def parse_hashes(text):
    return legacy().parse_hashes(text)


def generation(doc):
    keys = ('serial', 'expected', 'presence_metadata', 'directory_metadata', 'placement_plan',
            'provider_freeze', 'planned_selfcheck', 'baseline', 'v1_seal', 'programs',
            'manifest', 'tiers', 'boat_uid', 'synthetic', 'smoke', 'baseline_smoke',
            'selfcheck_composition', 'parameter_derivation', 'base_source')
    return hashlib.sha256(json.dumps({k: doc[k] for k in keys}, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def freeze_programs(freeze_ref, programs):
    path = pinned(freeze_ref)
    frozen = read(path)
    need(frozen.get('files'), 'provider author freeze required')
    roots = [path.parent, *path.parents]
    for name in ('provider_executor', 'provider_contract', 'provider_compiler', 'boat_identity'):
        actual = pinned(programs[name]).resolve()
        matched = [row for row in frozen['files']
                   if row['sha256'] == sha(actual) and
                   any((root / row['path']).resolve() == actual for root in roots)]
        need(len(matched) == 1, 'program is not in exact provider freeze: ' + name)
    for row in frozen['files']:
        candidates = [root / row['path'] for root in roots if (root / row['path']).is_file()]
        need(any(sha(candidate) == row['sha256'] for candidate in candidates), 'provider freeze member drift')


def canonical_composition(doc):
    """Consume the one T4 producer and its unchanged original admission chain."""
    compiler = pinned(doc['programs']['selfcheck_compiler'])
    need(sha(compiler) == SELFCHECK_COMPILER_SHA, 'exact T4 handoff selfcheck compiler interface pin')
    producer = module(compiler, 'canonical_t4_selfcheck_consumer')
    composition = pinned(doc['selfcheck_composition'])
    view, binary, admitted = producer.verified(composition)
    need(admitted['serial'] == doc['serial'] == SERIAL and
         admitted['compiler'] == doc['programs']['selfcheck_compiler'] and
         admitted['planned_selfcheck'] == doc['planned_selfcheck'], 'canonical composition binding')
    request_path = producer.pin(admitted['request'], composition.parent)
    request = producer.read(request_path)
    need(request['serial'] == SERIAL and request['v1_seal'] == doc['v1_seal'] and
         request['placement_plan'] == doc['placement_plan'] and
         request['provider_freeze'] == doc['provider_freeze'], 'canonical source/actual plan binding')
    for role, name in [('executor', 'provider_executor'), ('contract', 'provider_contract'), ('identity', 'boat_identity')]:
        need(producer.pin(request['programs'][role], request_path.parent).resolve() ==
             pinned(doc['programs'][name]).resolve(), 'canonical provider program binding')
    need(request['base'] == doc['base_source'], 'independent actual same-board R5 source binding')
    # verified() already admitted the complete raw R5 source. Re-pin its
    # unchanged result and extract that same940, without replaying another union.
    checked = producer.read(producer.pin(request['base']['selfcheck'], request_path.parent))
    original = {row['target']: row['actual'] for row in checked['checks']}
    view = dict(view, identity_base_expected=original)
    return view


def intended(doc):
    """Validate T4's one union against its exact plan; never generate a rival seal."""
    need(doc['serial'] == SERIAL, 'same-board only; no 5ea absence substitution')
    need(doc['baseline'] == pin(BASE), 'original complete319 source pin')
    base = read(pinned(doc['baseline']))['expected']
    need(len(base) == 319, 'original319 membership required')
    valid_rows(base)
    need(doc['v1_seal']['sha256'] == V1_SHA, 'preserved original v1 identity required')
    seal = read(pinned(doc['v1_seal']))
    # V1 seal is artifact provenance; actual940 comes only from admitted same-board R5.
    view = canonical_composition(doc)
    original = view['identity_base_expected']
    need(len(original) == 940 and all(original.get(t) == h for t, h in base.items()), 'complete actual same-board v1/319 source')
    plan = read(pinned(doc['placement_plan']))
    need(plan['serial'] == SERIAL and type(plan.get('synthetic', False)) is bool, 'actual same-board plan scope')
    freeze_programs(doc['provider_freeze'], doc['programs'])
    executor = module(pinned(doc['programs']['provider_executor']), 'exact_boat_executor_61b')
    need(plan['candidate_contract'] == doc['programs']['provider_contract'] and
         plan['boat_identity_program'] == doc['programs']['boat_identity'], 'provider helper binding')
    executor.validate(plan, executor.core_for(plan))
    need(doc['synthetic'] is plan.get('synthetic', False), 'synthetic provenance must propagate')
    need(doc['boat_uid'] == plan['boat_uid'], 'exact actual BMS UID binding')
    contract = module(pinned(doc['programs']['provider_contract']), 'exact_boat_contract_61b')
    route = contract.protected()
    need(len(route) == 488 and ROUTEB in route, 'all existing RouteB487 plus HAP required')
    boat = {row['target']: row['sha256'] for row in plan['members'] + plan['binds']}
    need(len(plan['members']) == 11 and len(plan['binds']) == 7 and len(boat) == 18, 'exact11/7/18 Boat scope')
    changes = shared_changes()
    need({target: boat[target] for target in changes} == changes, 'exact four shared replacements')
    expected = dict(original)
    expected.update(boat)
    need(BOAT_APK not in original, 'Boat is a new package, not a v1 receipt')
    expected[BOAT_APK] = BOAT_SHA
    need(len(expected) == 954, 'complete954 expected objects required')
    dynamic = None
    if not doc['synthetic'] or doc.get('selfcheck_composition') is not None:
        dynamic = view.get('v2_parameter_derivation')
        if dynamic is not None:
            need(dynamic['schema'] == 'exact-running-realization/v1' and
                 dynamic['target'] in route and dynamic['target'].endswith('/run.sh') and
                 dynamic['device_write_operations'] == 0, 'only original independently observed running_files derivation')
            expected[dynamic['target']] = dynamic['sha256']
    need(doc.get('parameter_derivation') == dynamic, 'independent parameter derivation receipt binding')
    need(all(expected.get(t) == (dynamic['sha256'] if dynamic and t == dynamic['target'] else h)
             for t, h in route.items()), 'RouteB realization differs; exact independent rebind required')
    need(all(expected.get(t) == changes.get(t, h) for t, h in base.items()), '319 reduced or changed beyond four')
    planned = read(pinned(doc['planned_selfcheck']))
    need(planned.get('status') == 'EXPECTED_UNION_NOT_OBSERVED' and planned.get('signed') is False,
         'T4 planned union is not an observed selfcheck/signature')
    need(planned['inputs'] == {'v1_seal': doc['v1_seal']['sha256'], 'plan': doc['placement_plan']['sha256']},
         'planned selfcheck source/plan drift')
    need(planned['all_expected_sha256'] == expected, 'full planned selfcheck differs; no exclusions')
    valid_rows(expected)
    presence = {}
    for row in plan['preserved']:
        value = row['before']
        need(value['exists'] is True, 'preserved absence forbidden')
        presence[row['target']] = {key: value[key] for key in META}
    for row in plan['members'] + plan['binds']:
        presence[row['target']] = {key: row['after'][key] for key in META}
    need(len(presence) == 507 and all(t in expected for t in presence), 'complete presence metadata')
    directories = {row['target']: row['after'] for row in plan['directory_prerequisites'] + plan['directories']}
    need(len(directories) == 5, 'three RouteB and two Boat directory guards')
    return base, expected, presence, directories


def validate(doc):
    need(doc['schema'] == SCHEMA and doc['execution_enabled'] is False, 'disabled proof schema')
    need(type(doc['synthetic']) is bool and doc.get('absent_files') == [], 'no serial-specific absence exemptions')
    base, expected, presence, directories = intended(doc)
    need(doc['replacements'] == {target: {'before': base[target], 'after': digest}
                                for target, digest in shared_changes().items()}, 'exact315keep+4replace declaration')
    need(doc['inventory'] == {'original': 319, 'keep': 315, 'replace': 4, 'route_b_plus_hap': 488,
                             'boat_targets': 18, 'sha_objects': 954, 'presence_objects': 507}, 'complete inventory declaration')
    need(doc['expected'] == expected and doc['presence_metadata'] == presence and
         doc['directory_metadata'] == directories, 'complete identity or metadata differs')
    runtime, boot = parts({target: expected[target] for target in base})
    need(doc['fingerprints'] == {'runtime_sha256': fp(runtime), 'boot_sha256': fp(boot)}, 'full fingerprint drift')
    need(doc['generation_sha256'] == generation(doc), 'generation digest drift')
    for ref in doc['programs'].values():
        pinned(ref)
    need(doc['programs']['identity'] == pin(HERE / 'candidate_identity.py') and
         doc['programs']['presence_reader'] == pin(HERE / 'presence_reader.py'), 'local gate/helper self-pin')
    need(doc['programs']['reader'] == pin(UPSTREAM) and sha(UPSTREAM) == READER_SHA, 'original Reader pin')
    need(doc['programs']['legacy_helpers'] == pin(LEGACY) and sha(LEGACY) == LEGACY_SHA, 'original helper pin')
    need(doc['manifest'] == pin(MANIFEST) and doc['tiers'] == pin(TIERS) and
         sha(MANIFEST) == MANIFEST_SHA and sha(TIERS) == TIERS_SHA, 'original128 manifest/tier pins')
    need(doc['baseline_smoke'] == pin(BASE_SMOKE) and sha(BASE_SMOKE) == BASE_SMOKE_SHA, 'original smoke groups/predicates source pin')
    need(doc['programs']['compiler'] == pin(HERE / 'compile_candidate.py'), 'local compiler self-pin')
    smoke = read(pinned(doc['smoke']))
    old_smoke = read(pinned(doc['baseline_smoke']))
    wanted = json.loads(json.dumps(old_smoke))
    need(old_smoke['expect'] == {'runtime_fp': '452447a4a0ba', 'boot_fp': 'ee927db88a67'}, 'original smoke fingerprints')
    for target, digest in old_smoke['probe']['files'].items():
        need(base.get(target) == digest, 'original smoke probe SHA')
    wanted['expect'] = {'runtime_fp': fp(runtime)[:12], 'boot_fp': fp(boot)[:12]}
    wanted['probe']['files'] = {target: expected[target] for target in old_smoke['probe']['files']}
    wanted['probe']['files'].update(shared_changes())
    need(smoke == wanted, 'original smoke groups/predicates must remain unchanged')
    return expected


def load_proof(path, digest):
    need(sha(path) == digest, 'independent proof pin differs')
    doc = read(path)
    validate(doc)
    return doc


def validate_round_inputs(proof, manifest, tiers, install_index):
    need(pin(manifest) == proof['manifest'] and pin(tiers) == proof['tiers'], 'original128/tier source binding')
    apps = [row for row in read(manifest)['apps'] if row.get('install') is not False]
    shots = read(tiers)['apps']
    need(len(apps) == 128 and len({r['key'] for r in apps}) == 128, 'exact128 members')
    need({str(t): sum(r['screenshot_seconds'] == t for r in shots) for t in (10, 20)} == {'10': 121, '20': 7},
         'original121t10+7t20 tiers')
    index = read(install_index)
    for app in apps:
        item = index.get(app['key'], {})
        need(item.get('serial', SERIAL) == SERIAL and item.get('success') is True and
             item.get('apk_sha256') == app['apk_sha256'], 'same-board installed index identity: ' + app['key'])
        record = read(pinned({'path': item['record'], 'sha256': item['record_sha256']}))
        need(proof['synthetic'] or not record.get('synthetic', False), 'synthetic record cannot authorize actual round')
        need(record.get('serial') == SERIAL and record.get('key') == app['key'] and
             record.get('package') == app['package'] and record.get('apk_sha256') == app['apk_sha256'] and
             record.get('install', {}).get('return_code') == 0 and
             record.get('install', {}).get('success_text') is True, 'actual same-board install record: ' + app['key'])


def validate_round_bindings(proof, config):
    need(not proof['synthetic'], 'synthetic identity cannot execute')
    need(config['serial'] == SERIAL and config['bindings']['manifest'] == proof['manifest'] and
         config['bindings']['tiers'] == proof['tiers'], 'round canonical128 binding')
    need(len(config['windows']) == 8, 'original eight bounded windows')
    validate_round_inputs(proof, pinned(config['bindings']['manifest']), pinned(config['bindings']['tiers']),
                          pinned(config['bindings']['install_index']))


def check(reader, proof, out, boot_before):
    """Original full SHA/runtime/boot/parent/version/postboot checks, plus presence/UID."""
    expected = validate(proof)
    need(not proof['synthetic'], 'synthetic identity cannot read a device')
    def shell(command):
        rc, text = reader.shell(command)
        need(rc == 0, 'read rc nonzero: ' + command)
        return text
    before = shell('cat /proc/sys/kernel/random/boot_id')
    need(before != boot_before, 'not a post-reboot round')
    if proof.get('parameter_derivation') is not None:
        need(before == proof['parameter_derivation']['current_boot'], 'independent WID receipt is from another boot')
    reader.verify_metadata(proof['presence_metadata'], proof['directory_metadata'])
    identity = module(pinned(proof['programs']['boat_identity']), 'boat_uid_gate_61b')
    need(identity.parse(reader.bundle()) == proof['boat_uid'], 'actual Boat BMS UID drift')
    actual = {}
    paths = list(expected)
    for i in range(0, len(paths), 24):
        group = paths[i:i + 24]
        got = parse_hashes(shell('sha256sum ' + ' '.join(group)))
        need(set(got) == set(group), 'missing/unexpected SHA rows')
        actual.update(got)
    diff = {p: {'expected': h, 'actual': actual.get(p)} for p, h in expected.items() if actual.get(p) != h}
    runtime_command = 'sha256sum /system/bin/appspawn-x /system/android/framework/oh-adapter-runtime.jar /system/android/lib64/*.so /system/lib64/westlake/route-a/*/*.so ' + ' '.join('/system/lib64/' + d + n for d in ('', 'platformsdk/') for n in ('libbms.z.so', 'libapk_installer.so', 'libinstalls.z.so')) + ' 2>/dev/null'
    boot_command = 'sha256sum /system/android/framework/arm64/* ' + ' '.join('/system/android/framework/' + n + '.jar' for n in ('core-oj', 'core-libart', 'core-icu4j', 'okhttp', 'bouncycastle', 'apache-xml', 'adapter-mainline-stubs', 'framework', 'oh-adapter-framework')) + ' 2>/dev/null'
    base = read(pinned(proof['baseline']))['expected']
    expected_runtime, expected_boot = parts({p: expected[p] for p in base})
    for name, command, rows in [('runtime', runtime_command, expected_runtime), ('boot', boot_command, expected_boot)]:
        got = parse_hashes(shell(command))
        need(got == rows, 'full ' + name + ' membership/hash differs')
        (out / (name + '-fingerprint.txt')).write_text('\n'.join(sorted(h + '  ' + p for p, h in got.items())) + '\n')
    ps = shell('ps -A -o PID,PPID,UID,NAME')
    parents = []
    for line in ps.splitlines():
        words = line.split()
        if len(words) >= 4 and all(x.isdigit() for x in words[:3]) and words[1:4] == ['1', '0', 'appspawn-x']:
            if shell('readlink /proc/' + words[0] + '/exe').split(' (deleted)')[0].strip() == '/system/bin/appspawn-x':
                parents.append(words[0])
    storage = shell('df -k /data')
    version = shell('param get const.ohos.fullname')
    after = shell('cat /proc/sys/kernel/random/boot_id')
    result = {'serial': proof['serial'], 'synthetic': False,
              'status': 'ACTUAL_READONLY_IDENTITY_NOT_UI_SIGNOFF',
              'passed': not diff and before == after and bool(before) and len(parents) == 1 and
              version in ('OpenHarmony-6.1.0.31', 'OpenHarmony 6.1.0.31'), 'diff': diff,
              'boot_before': before, 'boot_after': after, 'parent_pids': parents, 'storage': storage,
              'system_version': version, 'original_319_members': 319, 'candidate_paths': len(expected),
              'generation_sha256': proof['generation_sha256'], 'remote_writes': 0,
              'scope': 'same-board global/Boat/complete RouteB487+HAP+all original v1 objects; UI remains separate',
              'absent_targets': []}
    (out / 'identity.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--round', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    config = read(args.round / 'round.json')
    binding = config['bindings']['candidate_proof']
    proof = load_proof(pinned(binding), binding['sha256'])
    need(config['serial'] == SERIAL and not proof['synthetic'], 'actual same-board round required')
    reader_module = module(pinned(proof['programs']['reader']), 'original_readonly_reader_61b')
    helper = module(pinned(proof['programs']['presence_reader']), 'strict_presence_reader_61b')
    args.out.mkdir(parents=True, exist_ok=False)
    reader = helper.with_presence(reader_module.Reader)(args.out, SERIAL)
    result = check(reader, proof, args.out, config['boot_before_reboot'])
    if not result['passed']:
        return 1
    mark = args.round / 'observed-post-reboot-boot.json'
    if mark.exists():
        need(read(mark)['boot_id'] == result['boot_after'], 'boot changed across windows')
    else:
        with mark.open('x') as stream:
            json.dump({'boot_id': result['boot_after']}, stream)
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
