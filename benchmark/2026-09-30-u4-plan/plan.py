#!/usr/bin/env python3
"""Offline U4 predictions / command rendering. Never executes a subprocess or device IO."""
import argparse
import csv
import hashlib
import json
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import lab_paths


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def predictions():
    plan = read(HERE / 'shards.json')
    evidence = {r['key']: r for r in read(HERE / 'inputs/j3-evidence.json')}
    walls = {r['key']: r for r in read(HERE / 'inputs/j3-per-key.json')}
    clusters = read(HERE / 'inputs/clusters.json')
    implemented = {'N3-namespace', 'N3-eglimpl', 'N3-jna-symbol', 'N3-property', 'N3-opensles'}
    rows = []
    for key in sorted(plan['expected_keys']):
        e = evidence[key]
        cs = [c for c in clusters if key in c['keys']]
        category = '不变'
        checkpoint = 'Preserve J3 t20 UI' if e['lit'] else 'Current first wall remains; no implemented repair in this candidate'
        condition = 'Identical APK, clean install, same platform and frozen behavior'
        if any(c['cluster_id'] in implemented for c in cs):
            category = '过墙'
            checkpoint = next(c['cluster_id'] for c in cs if c['cluster_id'] in implemented)
            condition = 'Candidate consumer resolves audited symbols in its actual owner namespace; later APIs/UI unknown'
        special = {
            'fd-tutanota': ('不变', 'WebView support remains unavailable in delivered J5 dbce2eee', 'Exact WebViewUpdateServiceAdapter class absent in J5/boot union; provider APK also missing. Conditional unlock only after Java/native contract + real provider closure are delivered'),
            'noice': ('解锁', 'MediaRouter.registerClientAsUser; conditional first-page candidate', 'J5 retains J4 media_router implementation; later TLS/SSLSockets may still fail'),
            'newpipe': ('过墙', 'PlayerService: Platform signature not found', 'Already lit; J5 retains J4 platform signature. Do not count another light or promise playback'),
            'fd-immich': ('过墙', '__system_property_find/read_callback secondary native failure', 'Earlier unresolved d7.c verifier remains; do not predict first-screen unlock'),
            'vlc': ('过墙', 'Secondary libGLESv2 visibility only', 'Onboarding/Transparent Context mismatch remains; no theme repair included'),
        }
        if key in special:
            category, checkpoint, condition = special[key]
        if key in {'fd-seal', 'subwaysurfers', 'toutiao'}:
            category = '过墙'
            checkpoint = 'Host input assembly / install attempt (separate input revision)'
            condition = 'Use input-recovery receipt + exact sidecars; device extractor exceptions still require verification. Not a native/JAR benefit'
        if key in {'termux', 'fd-AppManager', 'fd-mobile', 'fd-uhabits'}:
            checkpoint = 'No explicit first fatal; observation only, no new repair of this wall'
            condition = 'N3b retains N2 graphics; do not recount earlier 32df as new. Termux caller and VLC context probes are separate'
        if key == 'fd-noice':
            checkpoint = 'Preserve already-lit welcome screen; SSLSockets background wall remains'
        slot = next(s['name'] for s in plan['shards'] if key in s['keys'])
        rows.append(dict(key=key, shard=slot, package=e['package'], baseline_lit=e['lit'],
                         prediction=category, checkpoint=checkpoint, condition=condition,
                         predicted_new_light=None, baseline_apk_sha256=e['apk_sha256'],
                         candidate_apk_sha256=plan['expected_apk_sha256'][key],
                         apk_changed=e['apk_sha256'] != plan['expected_apk_sha256'][key],
                         current_cluster=walls.get(key, {}).get('cluster_id', 'already-lit-protection'),
                         source_log=e['log'], source_log_sha256=e['log_sha256'],
                         first_blocker=walls.get(key, {}).get('first_blocker'),
                         first_fatal=walls.get(key, {}).get('first_fatal')))
    return rows


def commands(plan, j5, j5_sha, manifest, known_boards, workspaces, run_id):
    """Render future batch commands only. Input completeness is NOT board authorization."""
    failures = []
    slots = plan.get('shards', [])
    flat = [k for s in slots for k in s['keys']]
    if len(slots) != 4 or len(flat) != 66 or len(set(flat)) != 66 or set(flat) != set(plan['expected_keys']):
        failures.append('four disjoint shards must cover exactly the pinned 66 keys')
    serials = [s.get('serial') for s in slots]
    if len(set(serials)) != 4 or any(s not in known_boards for s in serials):
        failures.append('four distinct registered OH serials required; D is currently unassigned')
    if not j5 or not j5_sha or len(j5_sha) != 64 or not Path(j5).is_file() or sha(j5) != j5_sha:
        failures.append('J5 artifact and full matching SHA required')
    if j5_sha == 'dbce2eeada1d40d34d7904936bc09860d6ad30009781444ecd73661ad7e7e223':
        failures.append('delivered J5 lacks WebViewUpdateServiceAdapter required by N3b; cross-layer contract unresolved')
    if not manifest.is_file() or sha(manifest) != plan['cohort_manifest_sha256']:
        failures.append('cohort manifest must match pinned four-shard SHA')
    if not run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in run_id):
        failures.append('run ID must use alphanumeric, dash or underscore')
    if failures:
        raise ValueError('; '.join(failures))
    master = workspaces / 'westlake-harness'
    tools = workspaces / 'westlake-inputs/tools'
    output = []
    for index, slot in enumerate(slots):
        serial = slot['serial']
        argv = ['python3', str(master / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),
                '--manifest', str(manifest), '--execute', '--serial', serial, '--lane', 'cx-t0',
                '--hdc-cmd', str(tools / 'hdc_mac.sh'), '--lock-cmd', 'mac ' + shlex.quote(str(tools / 'board_note.sh')),
                '--keys', ','.join(slot['keys']), '--reinstall', '--hilog', '20', '--shots', '5,20', '--focus-check',
                '--run-id', run_id + '-' + serial, '--out', str(HERE / 'runs')]
        output.append({'slot': slot['name'], 'start_offset_seconds': index * 5, 'serial': serial,
                       'vm_argv': argv, 'mac_command': shlex.join(['orb', '-m', 'a2hlab', 'bash', '-lc', shlex.join(argv)])})
    return {'device_io': False, 'render_only': True, 'authorization': 'not granted by this file',
            'j5_sha256': j5_sha, 'commands': output}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write-predictions', action='store_true')
    ap.add_argument('--commands', action='store_true')
    ap.add_argument('--shards', type=Path, default=HERE / 'shards.json')
    ap.add_argument('--j5', type=Path)
    ap.add_argument('--j5-sha256')
    ap.add_argument('--manifest', type=Path)
    ap.add_argument('--run-id', default='u4')
    args = ap.parse_args()
    if args.write_predictions:
        rows = predictions()
        (HERE / 'predictions.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
        fields = ['key', 'shard', 'baseline_lit', 'prediction', 'checkpoint', 'condition', 'apk_changed']
        with (HERE / 'predictions.csv').open('w') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)
    if args.commands:
        try:
            ws = lab_paths.workspaces()
            plan = read(args.shards)
            manifest = args.manifest or HERE / plan['cohort_manifest']
            result = commands(plan, args.j5, args.j5_sha256, manifest, lab_paths.boards('oh'), ws, args.run_id)
        except (ValueError, OSError) as e:
            print(json.dumps({'device_io': False, 'ready': False, 'reason': str(e)}))
            return 2
        print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
