#!/usr/bin/env python3
"""G34-DFX-PROVENANCE: offline exact-match table for the crash-reporting and sigchain objects mapped by G34 child 29761.

Reads only fixed local text records (maps, fresh read-only hashes, rollout native-gates, 5ea inventories) and the
content-addressed ELF copies already saved locally; recomputes SHA256 and reads build-id/SONAME with llvm-readelf.
No device, VM, network, debugger, REA or build. Mapping presence does not mean a handler ran; a missing record does
not mean protection fired. Private inputs are named with $HOME; the repo records their SHA and size.
"""
import hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
H = Path.home()
P = H / '.local/share/westlake/commercial-game-20261021'
MAPS = P / 'g34-window01/game-ui-02/child-29761-maps.txt'
FRESH = P / 'g34-fresh-readonly-01'
ROLL = P / 'g34-rollout-01'
N5 = ROOT / 'benchmark/2026-10-01-n5-baseline-gates/inventory.json'
SYSF = ROOT / 'benchmark/2026-09-30-board-inventory/5ea/system-files.txt'
PLAN = ROOT / 'benchmark/2026-10-21-commercial-game/locale-transaction-package/transaction-plan.json'
GEN = '74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac'
STOCK = ['/system/lib64/platformsdk/libdfx_signalhandler.z.so', '/system/lib64/chipset-sdk-sp/libdfx_dumpcatcher.z.so',
         '/system/lib64/chipset-sdk-sp/libfaultloggerd.z.so', '/system/lib64/chipset-sdk-sp/libdfx_procinfo.z.so',
         '/system/lib64/chipset-sdk-sp/libunwinder.z.so', '/system/lib64/chipset-sdk-sp/libbacktrace_local.so']
ROUTE = [f'/system/lib64/westlake/route-a/{GEN}/libsigchain.so', f'/system/lib64/westlake/route-a/{GEN}/libunwindstack.so']
READELF = shutil.which('llvm-readelf') or '/opt/homebrew/bin/llvm-readelf'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def alias(p): return str(p).replace(str(H), '$HOME', 1)
def pin(p): return {'path': alias(p), 'sha256': sha(p), 'bytes': os.path.getsize(p)}

def elf(p):
    notes = subprocess.run([READELF, '-n', str(p)], capture_output=True, text=True, check=True).stdout
    dyn = subprocess.run([READELF, '-d', str(p)], capture_output=True, text=True, check=True).stdout
    bid = next((l.split()[-1] for l in notes.splitlines() if 'Build ID' in l), None)
    son = next((l.split()[-1].strip('[]') for l in dyn.splitlines() if 'SONAME' in l), None)
    return {'sha256': sha(p), 'bytes': os.path.getsize(p), 'build_id': bid, 'soname': son}

def gates(side):
    out = {}
    def walk(o):
        if isinstance(o, dict):
            if o.get('target') in STOCK and 'sha256' in o: out.setdefault(o['target'], set()).add(o['sha256'])
            for v in o.values(): walk(v)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(json.loads((ROLL / side / 'native/native-checks/native-gates.json').read_text()))
    return {k: sorted(v) for k, v in out.items()}

def main():
    maps = {}
    for line in MAPS.read_text().splitlines():
        f = line.split()
        if len(f) >= 6 and f[5] in STOCK + ROUTE: maps.setdefault(f[5], {'device': f[3], 'inode': int(f[4]), 'segments': 0})['segments'] += 1
    n5 = {r['target']: r['sha256'] for r in json.loads(N5.read_text())['rows']}
    sizes = {l.split()[2]: int(l.split()[0]) for l in SYSF.read_text().splitlines() if len(l.split()) == 3}
    fresh = json.loads((FRESH / 'hashes.json').read_text())
    boot = (FRESH / 'identity-boot-before.stdout').read_text().split()[0]
    plan = PLAN.read_text()
    gc, gb = gates('candidate'), gates('baseline')
    rows = []
    for t in STOCK:
        s = n5[t]; copy = ROLL / 'candidate/native/native-checks/system-elf' / s
        e = elf(copy)
        rows.append({'target': t, 'origin': 'stock OH system partition', 'g34_child_maps': maps.get(t),
            'g34_time_device_sha256': None, 'g34_time_device_sha256_status': 'MISSING: no G34-window read of this path; fresh 319-hash set excludes it',
            '5ea_n5_inventory_sha256': s, '5ea_n5_inventory_boot': 'f828d689-82ab-4bc8-8e15-421332d63721 (2026-10-01)',
            'g34_rollout_native_gates_sha256': {'candidate': gc.get(t), 'baseline': gb.get(t)},
            'local_copy': dict(e, path=alias(copy), sha256_matches_inventory=e['sha256'] == s),
            '5ea_system_files_bytes_20260930': sizes.get(t), 'bytes_equal_to_5ea_listing': sizes.get(t) == e['bytes'],
            'source_snapshot': 'MISSING', 'build_log': 'MISSING', 'build_metadata': 'build-id only; no OH image build record bound locally; not bound by version label'})
    for t in ROUTE:
        payload = ROLL / 'candidate/native/payload/route' / t.rsplit('/', 1)[1]
        e = elf(payload); d, p = fresh['direct'].get(t), fresh['parent'].get(t.replace('/system', '/proc/19168/root/system', 1)) or fresh['parent'].get(t)
        rows.append({'target': t, 'origin': f'Westlake route-a generation {GEN[:12]} (pre-existing unified state; not a G34 package mount)',
            'g34_child_maps': maps.get(t), 'g34_time_device_sha256': {'direct': d, 'parent_view': p, 'boot': boot,
            'read_at': 'g34-fresh-readonly-01 23:05:56 (before apply)'},
            'g34_transaction_baseline319_contains': f'"{t}": "{e["sha256"]}"' in plan,
            'local_identical_bytes': dict(e, path=alias(payload), note='G34 rollout payload/route copy; package declares /system/android/lib64 as target; this window did not newly mount/write these two libraries'),
            'device_equals_local': d == p == e['sha256'],
            'source_snapshot': 'MISSING locally', 'build_log': 'MISSING locally',
            'build_metadata': 'build-id only; route-A frozen build inputs are recorded on hw248 only (OPS-RUNBOOK route-A note); not read here'})
    inputs = [pin(MAPS), pin(FRESH / 'hashes.json'), pin(FRESH / 'identity-boot-before.stdout'),
              pin(ROLL / 'candidate/native/native-checks/native-gates.json'), pin(ROLL / 'baseline/native/native-checks/native-gates.json'),
              {'path': str(N5.relative_to(ROOT)), 'sha256': sha(N5), 'bytes': os.path.getsize(N5)},
              {'path': str(SYSF.relative_to(ROOT)), 'sha256': sha(SYSF), 'bytes': os.path.getsize(SYSF)},
              {'path': str(PLAN.relative_to(ROOT)), 'sha256': sha(PLAN), 'bytes': os.path.getsize(PLAN)}]
    out = {'token': 'G34-DFX-PROVENANCE', 'maps_sha256': sha(MAPS), 'rows': rows, 'inputs': inputs,
           'readelf': {'path': alias(READELF), 'sha256': sha(os.path.realpath(READELF))},
           'scope': 'object identity only; mapping is not handler execution; absent records are not protection evidence',
           'device_vm_network_debugger_rea_build': 0}
    (HERE / 'match-table.json').write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps([{'target': r['target'].rsplit('/', 1)[1], 'sha': (r['local_copy'] if 'local_copy' in r else r['local_identical_bytes'])['sha256'][:12],
        'build_id': (r['local_copy'] if 'local_copy' in r else r['local_identical_bytes'])['build_id'],
        'g34_device': (r['g34_time_device_sha256'] or {}).get('direct', 'MISSING')[:12] if r['g34_time_device_sha256'] else 'MISSING'} for r in rows], indent=1))

if __name__ == '__main__':
    main()
