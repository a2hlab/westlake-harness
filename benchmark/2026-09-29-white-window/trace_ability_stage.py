#!/usr/bin/env python3
"""Reproduce #62 static evidence locally; never opens a device or writes inputs."""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402
OUT = HERE / 'evidence/ability-stage'
JAR = lab_paths.workspaces() / 'vm-copies/b5-runtime-jar/oh-adapter-runtime.jar'
WORK = lab_paths.workspaces() / 'westlake-harness-bms-deploy/bms/src/.work'
TOOLS = WORK / 'b6-task45/inputs'
BRIDGES = {
    'reply': (WORK / 'b6-task52/baseline-native/liboh_adapter_bridge.so',
              '84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a'),
    # same bytes as the copy first used from a lane's session scratchpad (hash-pinned below)
    'no_reply': (lab_paths.workspaces() / 'westlake-bms-suite/src/adapter/frozen/r45-dynamic-roots/liboh_adapter_bridge.so',
                 '7db99e1b760cf843b1a99db1382a3299f189c8cbca786ec411b7c35a2af6ffb9'),
}
JAR_HASH = '250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146'
ANCHOR = 'Java_adapter_activity_AppSchedulerBridge_nativeNotifyApplicationForegrounded'

def identity(path, expected=None):
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if expected and sha != expected:
        raise ValueError(f'Input hash mismatch: {path}')
    return {'path': str(path), 'sha256': sha, 'bytes': len(raw)}

def command(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout

def excerpt(path, spans):
    lines = path.read_text().splitlines()
    return 'SOURCE ' + str(path) + '\n' + '\n'.join(
        f'{n}: {lines[n-1]}' for a, b in spans for n in range(a, b+1)) + '\n'

def methods(path, wanted):
    lines = path.read_text().splitlines()
    spans = []
    for i, line in enumerate(lines):
        if line.startswith('.method ') and any(name + '(' in line for name in wanted):
            end = next(j for j in range(i+1, len(lines)) if lines[j] == '.end method')
            spans.append((i+1, end+1))
    return spans

def fingerprint(log, candidate, elf):
    pid = log['pid']
    pattern = re.compile(r'OH_RegHook: (.*?) -> fn=([0-9A-Fa-f]+) .*lib=/system/android/lib64/liboh_adapter_bridge.so')
    observed = []
    for i, line in enumerate(Path(log['source']['path']).read_text().splitlines(), 1):
        if not re.match(r'^\d\d-\d\d\s+[\d:.]+\s+' + str(pid) + r'\s', line):
            continue
        m = pattern.search(line)
        if m:
            observed.append({'line': i, 'registration': m[1], 'address': int(m[2], 16), 'text': line})
    anchor = next(r for r in observed if r['registration'].startswith('adapter.activity.AppSchedulerBridge::nativeNotifyApplicationForegrounded('))
    symbol = next(s for s in elf.symbols if s['name'] == ANCHOR)
    base = anchor['address'] - symbol['value']
    entries = collections.defaultdict(list)
    for s in elf.symbols:
        if s['type'] == 2 and s['section'] != 0:
            entries[s['value']].append(s['name'])
    for row in observed:
        offset = row['address'] - base
        row.update(relative_offset=hex(offset), symbols=entries.get(offset, []))
    return {'candidate': candidate, 'inferred_base': hex(base), 'base_page_aligned': base % 4096 == 0,
            'observed_count': len(observed), 'function_entry_matches': sum(bool(r['symbols']) for r in observed),
            'rows': observed, 'deployed_whole_file_hash_verified': False}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jar = identity(JAR, JAR_HASH)
    jar['classes_dex_sha256'] = hashlib.sha256(zipfile.ZipFile(JAR).read('classes.dex')).hexdigest()
    cp_names = ['baksmali-2.5.2.jar', 'dexlib2-2.5.2.jar', 'util-2.5.2.jar',
                'guava-27.1-android.jar', 'jcommander-1.64.jar']
    cp = ':'.join(str(TOOLS / n) for n in cp_names)
    smali = Path('/tmp/task62-smali/reproduce-b5')
    command(['java', '-cp', cp, 'org.jf.baksmali.Main', 'd', str(JAR), '-o', str(smali)])
    bridge_smali = smali / 'adapter/activity/AppSchedulerBridge.smali'
    spans = methods(bridge_smali, ['ensureBindApplication', 'nativeOnScheduleLaunchApplication',
                                 'primeCoroutineStart', 'onScheduleAbilityStage', 'onScheduleAcceptWant',
                                 'notifyForegroundDeferred'])
    (OUT / 'b5-bridge-smali.txt').write_text(excerpt(bridge_smali, spans))
    runnable = smali / 'adapter/activity/AppSchedulerBridge$2.smali'
    (OUT / 'b5-bind-runnable-smali.txt').write_text(excerpt(runnable, [(1, len(runnable.read_text().splitlines()))]))
    spec = importlib.util.spec_from_file_location('elf_evidence', HERE.parent / '2026-09-29-b6-static-diff/compare.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    natives, elfs = {}, {}
    for label, (path, sha) in BRIDGES.items():
        natives[label] = identity(path, sha)
        e = module.ELF(path, sha)
        elfs[label] = e
        selected = [s for s in e.symbols if s['name'].startswith('_ZN10oh_adapter') and s['type'] == 2
                    and any(t in s['name'] for t in ['20ScheduleAbilityStage', '18ScheduleAcceptWant',
                                                     '19addAbilityStageDone', '22scheduleAcceptWantDone'])]
        text = '\n'.join(command(['llvm-objdump', '-d', '--demangle', '--no-show-raw-insn',
                         f'--start-address={s["value"]}', f'--stop-address={s["value"]+s["size"]}', str(path)]) for s in selected)
        (OUT / f'{label}-native.txt').write_text(text)
        natives[label]['functions'] = selected
        vt = next(s for s in e.symbols if s['name'] == '_ZTVN10oh_adapter19AppSchedulerAdapterE')
        sec = e.sections[vt['section']]
        offset = sec['offset'] + vt['value'] - sec['addr']
        points = [i+16 for i in range(0, vt['size'], 8) if struct.unpack_from('<q', e.data, offset+i)[0] == -120]
        natives[label]['scheduler_secondary_address_points'] = points
        natives[label]['callback_slots'] = [dict(vtable_offset=hex(r['offset']-vt['value']), symbol=r['symbol'])
            for r in e.relocs if vt['value'] <= r['offset'] < vt['value']+vt['size']
            and r['symbol'].startswith('_ZThn120_') and any(x in r['symbol'] for x in ['ScheduleAbilityStage', 'ScheduleAcceptWant'])]
    old = json.loads((HERE / 'results.json').read_text())
    prints = []
    for log in [old['baseline'], *old['apps']]:
        key = log.get('key', 'helloworld')
        prints.append({'key': key, 'pid': log['pid'], 'source': identity(Path(log['source']['path'])),
                       'candidates': [fingerprint(log, k, e) for k, e in elfs.items()]})
        a = log['stages']['attach']['first']['line']
        b = log['stages']['bind_main']['first']['line'] + 30
        (OUT / f'{key}-dispatch-context.txt').write_text(excerpt(Path(log['source']['path']), [(a, b)]))
    source_ranges = {
        'framework/activity/jni/app_scheduler_adapter.cpp': [(333, 369), (409, 439), (448, 460), (838, 851)],
        'framework/activity/jni/oh_app_mgr_client.cpp': [(76, 115), (142, 155), (164, 191)],
        'framework/activity/jni/oh_app_mgr_client.h': [(76, 106), (113, 124)],
        'framework/activity/jni/app_scheduler_adapter.h': [(20, 36), (81, 89), (108, 115)],
        'framework/activity/jni/oh_ability_manager_client.cpp': [(845, 860)],
        'framework/appspawn-x/src/appspawnx_runtime.cpp': [(700, 728)],
        'framework/activity/java/AppSchedulerBridge.java': [(97, 119), (270, 282), (325, 329), (1889, 1900)],
    }
    sources = []
    for rel, ranges in source_ranges.items():
        path = REPO / 'bms/src/adapter' / rel
        sources.append(identity(path))
        (OUT / (path.name + '.txt')).write_text(excerpt(path, ranges))
    platform = WORK / 'b6-latest/platform-link/libapp_manager.z.so'
    platform_id = identity(platform, '6ae44a9ca22305a58e78eb93b3cc118abe51a585ffa3a7c98b6dd380f5ff4cc7')
    (OUT / 'platform-dispatch.txt').write_text(command(['llvm-objdump', '-d', '--demangle',
        '--no-show-raw-insn', '--start-address=0xf3318', '--stop-address=0xf35f0', str(platform)]))
    data = {'task': 62, 'base_commit': 'fc84d838', 'jar': jar, 'smali': [identity(bridge_smali), identity(runnable)],
            'baksmali_classpath': [identity(TOOLS / n) for n in cp_names], 'native_inputs': natives,
            'source_inputs': sources, 'platform_input': platform_id, 'fingerprints': prints,
            'r2': {'static_control_flow': 'verified', 'historical_native_layout_attribution': 'partially',
                   'full_hash_in_each_historical_pid': 'unverified', 'repair_on_device': 'unverified'}}
    (HERE / 'ability-stage-results.json').write_text(json.dumps(data, indent=2) + '\n')
    for item in prints:
        print(item['key'], [(c['candidate'], c['function_entry_matches'], c['observed_count'], c['base_page_aligned']) for c in item['candidates']])

if __name__ == '__main__':
    main()
