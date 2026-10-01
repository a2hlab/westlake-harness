"""Replay complete APK facts; references stay distinct from predicted fatal walls."""

import argparse
import base64
import collections
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_evidence(path):
    return json.loads(gzip.decompress(base64.b64decode(path.read_text())))


def method_key(value):
    if '->' in value:
        return value
    owner_name, descriptor = value.split(':', 1)
    owner, name = owner_name.rsplit('.', 1)
    return 'L'+owner.replace('.', '/')+';->'+name+descriptor


def validate(selection, facts, runtime, manifest):
    selection_bytes = json.dumps(selection, ensure_ascii=False, sort_keys=True, indent=2).encode()+b'\n'
    if digest(selection_bytes) != facts['selection_sha256']:
        raise ValueError('selection identity drift')
    wanted = {row['package']: row for row in selection['rows']}
    if len(wanted) != 100 or len(facts['apps']) != 100:
        raise ValueError('freeze requires exactly 100 selected scans')
    if len({row['sha256'] for row in selection['rows']}) != 100:
        raise ValueError('duplicate selected APK identities')
    observed = {app['package']: app for app in facts['apps']}
    if len(observed) != 100 or set(observed) != set(wanted):
        raise ValueError('duplicate or missing scan identities')
    admitted = {app['package']: app for app in manifest['apps']}
    if len(manifest['apps']) != 100 or len(admitted) != 100 or set(admitted) != set(wanted):
        raise ValueError('input manifest cohort mismatch')
    for package, row in wanted.items():
        app = observed[package]
        entry = admitted[package]
        if app['status'] != 'scanned' or not app.get('dex'):
            raise ValueError('pending/rejected/incomplete scan: '+package)
        if app['sha256'] != row['sha256'] or entry['apk_sha256'] != row['sha256']:
            raise ValueError('APK pin drift: '+package)
        if set(app['signer']['fingerprints']) != set(row['signer_sha256']):
            raise ValueError('signer mismatch: '+package)
        if set(entry['signer_sha256']) != set(row['signer_sha256']) or entry['version_code'] != row['version_code']:
            raise ValueError('input manifest signer/version drift: '+package)
        if not app['manifest']['launchers'] or app['scanner_dependencies'] != facts['scanner_dependencies']:
            raise ValueError('incomplete or mixed scanner: '+package)
    if not runtime['inputs'] or not runtime['methods']:
        raise ValueError('runtime profile incomplete')
    runtime_bytes = json.dumps(runtime, sort_keys=True).encode()+b'\n'
    if digest(runtime_bytes) != facts['runtime_profile_sha256']:
        raise ValueError('runtime profile drift')
    return wanted, admitted


def predict(row, app, runtime, key):
    reached = set(app['startup']['reached'])
    candidates = {}
    def add(family, layer, evidence, startup=False, certainty='conditional-requirement'):
        item = candidates.setdefault(family, dict(family=family, layer=layer, occurrences=0, startup_occurrences=0,
                                                  certainty=certainty, evidence=[]))
        count = evidence.get('occurrence_count', 1)
        item['occurrences'] += count
        item['startup_occurrences'] += count if startup else 0
        if len(item['evidence']) < 3:
            item['evidence'].append({key:value for key,value in evidence.items() if key != 'examples'})
    for risk in app['risks']:
        add(risk['family'], 'JAR/native-contract', risk, method_key(risk['method']) in reached)
    for call in app['services']:
        add('system-service:'+call['service'], 'JAR/service', call, method_key(call['method']) in reached,
            certainty='API-contract-not-proved-null')
    for call in app['jni_calls']:
        if call['coverage'] in {'missing', 'stub', 'unknown'}:
            add('framework-jni:'+call['coverage'], 'native/JNI', call, method_key(call['method']) in reached,
                certainty='compiled-coverage-status-not-runtime-binding')
    all_exports = {symbol for library in app['libraries'] if library['member'].startswith('lib/arm64-v8a/') for symbol in library['exports']}
    for library in app['libraries']:
        if not library['member'].startswith('lib/arm64-v8a/'):
            continue
        if library.get('symbol_status') != 'parsed':
            add('native-parse-unknown', 'native', dict(member=library['member'], header=library['header']))
        for symbol in library['imports']:
            if symbol['weak']:
                continue
            if symbol['name'] not in runtime['exports'] and symbol['name'] not in all_exports:
                add('native-import-unresolved-in-profile', 'native', dict(member=library['member'], symbol=symbol['name']),
                    certainty='provider-outside-scanned-profile-or-absent; namespace-unknown')
        for name in library['needed']:
            packaged = any(Path(path).name == name for path in runtime['inputs']) or any(Path(item['member']).name == name for item in app['libraries'])
            if not packaged:
                add('native-needed-outside-profile', 'native', dict(member=library['member'], needed=name),
                    certainty='OH-system-provider-and-private-namespace-not-resolved')
    framework_usage = collections.Counter()
    startup_usage = collections.Counter()
    for call in app['framework_calls']:
        owner = call['owner']
        if owner.startswith('Landroidx/compose/'):
            family = 'compose'
        elif owner.startswith('Landroid/webkit/'):
            family = 'webview'
        elif owner.startswith('Landroid/opengl/'):
            family = 'gl'
        elif owner.startswith('Lio/flutter/'):
            family = 'flutter'
        else:
            family = 'unity'
        count = call.get('occurrence_count', 1)
        framework_usage[family] += count
        if call['method'] in reached:
            startup_usage[family] += count
        if family in {'webview', 'gl', 'flutter', 'unity'}:
            add(family+'-startup-or-first-frame', 'window/native', call, call['method'] in reached)
    if framework_usage['compose']:
        add('compose-first-frame-contract', 'JAR/window', app['framework_calls'][0])
    calls = app['startup']['calls']
    jumps = [call for call in calls if call['name'] in {'startActivity', 'startActivityForResult'}]
    for call in jumps:
        add('secondary-activity-window-session', 'window/first-frame', call, True,
            certainty='U7-last-session-risk; target-and-screen-owner-unknown')
    ordered = sorted(candidates.values(), key=lambda item: (-bool(item['startup_occurrences']), -item['startup_occurrences'], item['family']))
    heavy = bool(app['libraries']) or row['group'] in {'compose', 'webview', 'gl'} or any(startup_usage[name] for name in ['compose', 'webview', 'gl', 'flutter', 'unity'])
    unresolved_jni = any(call['coverage'] in {'missing', 'stub'} and method_key(call['method']) in reached for call in app['jni_calls'])
    t20 = 'unknown' if heavy or unresolved_jni else 'own-ui'
    return dict(key=key, package=row['package'], phase=row['group'], apk_sha256=row['sha256'],
                version_name=row['version_name'], version_code=row['version_code'],
                scan_status='complete-APK-evidence', dex_count=len(app['dex']), native_member_count=len(app['libraries']),
                manifest_activity_count=len(app['manifest']['activities']),
                launcher=[entry['target'] for entry in app['manifest']['launchers']],
                profile=dict(definitions=app['features'], invoked=dict(framework_usage), startup_invoked=dict(startup_usage)),
                jni_counts=dict(sum((collections.Counter({call['coverage']:call.get('occurrence_count',1)}) for call in app['jni_calls']), collections.Counter())),
                app_jni_counts=dict(collections.Counter(call['coverage'] for call in app['app_native_candidates'])),
                system_service_counts=dict(sum((collections.Counter({call['service']:call.get('occurrence_count',1)}) for call in app['services']), collections.Counter())),
                first_wall='unknown', first_wall_candidates=ordered,
                first_wall_reason='Static lifecycle/reference ordering cannot establish the first terminating event',
                checkpoint='unknown', t20=t20, confidence='low-static-transfer' if t20=='own-ui' else 'unknown',
                t20_reason='Light native-free DEX/manifest UI hypothesis; registration/virtual dispatch/resources remain unproved' if t20=='own-ui' else 'Native or specialized rendering/known unresolved startup binding needs runtime evidence',
                evidence=dict(file='facts.json.gz.b64', json_pointer='/apps/'+row['package'], sha256=digest(json.dumps(app, sort_keys=True).encode())),
                criteria=dict(first_wall='Target-PID terminating event then causal chain/crash stack via first_fatal.py; non-terminating noise is not first wall',
                              checkpoint='Positive target-PID execution beyond the named candidate API and first-frame operation; absence of an old error is not a crossing',
                              t20='First scheduled t20 screenshot, exact APK/runtime/input identities, outer visual signoff; white/black/launcher is unlit'))


def build(selection, facts, runtime, manifest):
    wanted, admitted = validate(selection, facts, runtime, manifest)
    observed = {app['package']: app for app in facts['apps']}
    rows = [predict(row, observed[row['package']], runtime, admitted[row['package']]['key']) for row in selection['rows']]
    indexes = {app['package']: index for index, app in enumerate(facts['apps'])}
    for row in rows:
        row['evidence']['json_pointer'] = '/apps/'+str(indexes[row['package']])
    return dict(schema_version=1, status='complete-static-prediction-not-measured', runtime=runtime['name'],
                runtime_profile_sha256=facts['runtime_profile_sha256'], selection_sha256=facts['selection_sha256'],
                input_manifest_sha256=digest(json.dumps(manifest, sort_keys=True).encode()),
                scanner_dependencies=facts['scanner_dependencies'], tools=facts['tools'],
                selected_count=100, apk_scanned=100, observed_device_results=False,
                t20_counts=dict(collections.Counter(row['t20'] for row in rows)), rows=rows)


def csv_text(result):
    output = io.StringIO(newline='')
    fields = ['key', 'package', 'phase', 'apk_sha256', 'version_name', 'version_code', 'dex_count', 'native_member_count',
              'first_wall', 'first_wall_candidates', 'checkpoint', 't20', 'confidence', 'criteria']
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    for row in result['rows']:
        record = {field: row[field] for field in fields}
        record['first_wall_candidates'] = ';'.join(item['family'] for item in row['first_wall_candidates'])
        record['criteria'] = json.dumps(row['criteria'], sort_keys=True)
        writer.writerow(record)
    return output.getvalue()


def markdown(result, facts, runtime):
    totals = {name: sum(app.get('raw_counts', {}).get(name, len(app[name])) for app in facts['apps']) for name in ['dex', 'libraries', 'services', 'jni_calls', 'app_native_candidates']}
    lines = ['# Corpus-v2 APK scan v1: U7 baseline', '',
             'The index-only selection did not prove DEX language/UI frameworks, launch manifests, JNI consumers or native dependencies. This version scans all actual APK bytes and records conditional first-wall candidates; it does not convert references into observed crashes or screenshots.', '',
             '## Evidence and identities', '',
             '- Cohort: 100 exact packages and APK SHA/size identities, 100 independent apksigner checks against the indexed signer fingerprints, and 100 LAUNCHER manifests. The original selection files and old apps.json remain unchanged.',
             '- Input manifest: the corrected oc-t4 100-key cv2 manifest, separately pinned in FREEZE.json; compact copy in input-manifest.json.gz.b64. Private APK paths are represented as $WORKSPACES.',
             '- Runtime: U7 T7d + J7b, native N4-order; no N10/J8 overlays. J7b 381110a675fb and T7d stubs d8b2406eb89d. Canonical sigchain/threadguard use route bytes 6d5d5538ff45 / 674d3ef3b9b0, not the different android/lib64 copies in the same native package.',
             '- '+str(len(runtime['inputs']))+' actual runtime SO/JAR inputs are SHA-bound. JNI declarations: '+json.dumps(runtime['jni_counts'], sort_keys=True)+'. Class-attributed compiled tables establish coverage, not successful RegisterNatives or classloader/namespace resolution. No historical approved JNI exceptions are promoted into this profile.',
             '- Deployment-domain correction: '+str(len(runtime.get('excluded_package_only_inputs', {})))+' package-only input paths are excluded and JNI attribution rebuilt against deployed hashes. Package inventory alone does not establish active U7 bytes; bind_runtime.py records the exclusion list and expected-run SHA.',
             '- APK facts: '+json.dumps(totals, sort_keys=True)+'. Full reproducible facts and runtime attribution evidence are compressed text in facts.json.gz.b64 and runtime-profile.json.gz.b64; binary inputs stay outside this repository.', '',
             '## Rules and prediction limits', '',
             '- B10 primitives are reused directly: scan_apps.method_scan (service constants/JNI calls), rules85.inspect_method and elf_info, rules_u5_feedback.dex_family, scan_jni compiled ownership, and the existing trampoline manifest/DEX parser. Exact dependency/tool hashes are pinned.',
             '- scan_risks_v3.inspect_method additionally examines bounded startup invokes for WorkManager/Koin/native-loader/context contracts. This projection has no preceding constant/branch instructions and does not claim the full-APK guard-string or argument-propagation coverage of that scanner.',
             '- Manifest classification retains launch aliases, activity counts, Application and provider classes. Application name comes from the XML tree, not dump badging; the latter omits that class and would undercount early startup roots.',
             '- All DEX instructions are examined. Startup roots include launcher/Application/provider lifecycle methods and in-APK superclass methods, with three exact-target call edges. Virtual dispatch, reflection, native entry and later event callbacks remain unknown; no claim of complete reachability is made.',
             '- compact.py counts the complete scan before retaining up to three original coordinates per family/API and startup membership. Full raw scan byte/SHA identity is recorded; counts are not inferred from the retained example count. Native export projection retains every symbol resolving another packaged-library import.',
             '- Native scan retains every packaged ABI member and all AArch64 ELF imports/exports/DT_NEEDED. An import outside the union is a candidate, not a proved relocation failure: OH system providers and private namespaces remain unverified. App JNI export matches do not prove invocation; dynamically registered declarations remain unknown.',
             '- Compose/WebView/GL classifications record definitions and actual invoke instructions separately, including bounded startup invokes. R8-obfuscated/dynamically loaded frameworks can evade these names.',
             '- First-wall and checkpoint are unknown for all 100. Candidate families are ranked by bounded-startup occurrences, not asserted chronological fatal order. t20 hypotheses: '+json.dumps(result['t20_counts'], sort_keys=True)+'. Native/special-rendering or compiled missing/stub startup binding yields unknown; light native-free UI gets a low-confidence static transfer hypothesis. No app is declared actually lit.',
             '- first_fatal.py must score target-PID termination and causal root; checkpoint needs positive execution; t20 requires the first scheduled identity-bound screenshot and outer visual signoff. Do not deduct benign context from actual terminal events.', '',
             '## Timing and freeze', '',
             'FREEZE.json registers the CSV SHA and actual freeze timestamp. The outer authorized the cv2 run to start before the freeze if scanning was not finished. All three device windows started at 09:24:47 +0800; this version is therefore explicitly late-frozen, not a held-out pre-run forecast. This lane performed no device actions and did not read cv2 hilog/screenshots to derive these predictions. Later scoring must retain that timing qualification.', '',
             '## Per-key predictions', '',
             '| Key | Phase | DEX/native | t20 hypothesis | Startup-ranked first-wall candidates |',
             '|---|---|---|---|---|']
    for row in result['rows']:
        families = [item['family'] for item in row['first_wall_candidates'] if item['startup_occurrences']]
        lines.append('| '+row['key']+' | '+row['phase']+' | '+str(row['dex_count'])+'/'+str(row['native_member_count'])+' | '+row['t20']+' | '+(', '.join(families[:5]) or 'unknown; no exact-target startup candidate')+' |')
    lines.extend(['', '## Replay and handoff', '',
                  '`python3 benchmark/2026-10-01-corpus-v2/apk-scan-v1/test_scan.py -v` exercises identity rejection, both apksigner output formats, Application XML roots, JNI uncertainty, incomplete-freeze refusal and exact artifact replay.',
                  '`report.py --format csv` replays PREDICTIONS.csv without APKs or network. For a new scan, run scan.py --output <scratch> --jobs 3; never overwrite this freeze. validation.json records the exact scoped master overlay and gate exit codes.',
                  'landing-paths.txt lists only this handoff. Shared README/DIGEST additions are exact lines in documentation.json. Input preparation/deployment remains with oc-t4; screenshots remain with the outer.', ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts', type=Path, default=HERE/'facts.json.gz.b64')
    parser.add_argument('--profile', type=Path, default=HERE/'runtime-profile.json.gz.b64')
    parser.add_argument('--manifest', type=Path, default=HERE/'input-manifest.json.gz.b64')
    parser.add_argument('--format', choices=['json', 'csv', 'markdown'], default='json')
    args = parser.parse_args()
    facts, runtime = load_evidence(args.facts), load_evidence(args.profile)
    result = build(json.loads((HERE.parent/'results.json').read_text()), facts, runtime, load_evidence(args.manifest))
    if args.format == 'markdown':
        print(markdown(result, facts, runtime), end='')
    else:
        print(json.dumps(result, indent=2, sort_keys=True) if args.format=='json' else csv_text(result), end='\n' if args.format=='json' else '')


if __name__ == '__main__':
    main()
