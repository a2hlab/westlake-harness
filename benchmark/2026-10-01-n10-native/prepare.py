"""Declare a full N10 native package; preserve N8 and the signed U7 inputs."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
from deploy_generation import load_package, validate_upgrade

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
save = lambda p, d: p.write_text(json.dumps(d, indent=2) + '\n')
base = REPO.parent / 'westlake-generation-n8-private-zlib'
u7 = REPO.parent / 'westlake-generation-n4-order-216b68fb'
out = REPO.parent / 'westlake-generation-n10-63b6f8d4'
assert sha(base / 'package.json') == '3dd48299b599c2adebe8cc574649a31d84fabae53b77d5a7df704f4f380b993e'
assert not out.exists()
subprocess.run(['/bin/cp', '-Rc', str(base), str(out)], check=True)
manifest = json.loads((out / 'package.json').read_text())
build = REPO.parent / 'westlake-n10-build'
new = {'libwestlake_android_child.z.so': build / 'child-candidate/libwestlake_android_child.z.so',
       'appspawn-x': build / 'scoped-1/appspawn-x',
       'libapp_native_loader.so': build / 'scoped-1/libapp_native_loader.so',
       'libbionic_compat.so': build / 'bionic-resumed-3/libbionic_compat.so'}
changes = []
for relative, previous in list(manifest['files'].items()):
    name = Path(relative).name
    if name not in new:
        continue
    dest = out / relative
    dest.chmod(dest.stat().st_mode | 0o200)
    shutil.copyfile(new[name], dest)
    digest = sha(dest)
    manifest['files'][relative] = digest
    for target, old in list(manifest['live_hashes'].items()):
        if old == previous and Path(target).name == name:
            manifest['live_hashes'][target] = digest
    changes.append({'file': relative, 'before': previous, 'after': digest})
manifest.update(variant='N10 owner preload and N8 private native domains',
                rollout_ready=False,
                rollout_blocker='Offline candidate: fresh native exceptions and device acceptance pending')
save(out / 'package.json', manifest)
identity = sha(out / 'package.json')
c = out / 'native-checks'
scan = json.loads((c / 'scan-manifest.json').read_text())
for name, source in [('n4-host.c', HERE / 'src/host.c'),
                     ('n10-child.c', HERE / 'src/sealed_child_provider_loader.c'),
                     ('n10-anl.c', HERE / 'flutter/app_native_loader.c')]:
    shutil.copy2(source, c / name)
    scan['sources'][name] = {'path': name, 'sha256': sha(source),
                            'origin': str(source.relative_to(REPO)),
                            'source_sha256': sha(source), 'first_line': 1}
for name, source, artifact in [('child-owner', 'n10-child.c', 'payload/runtime/libwestlake_android_child.z.so'),
                                ('anl-owner', 'n10-anl.c', 'payload/route/libapp_native_loader.so')]:
    scan['profiles'].append({'name': name, 'rule': 'namespace', 'source': source,
                             'identity': {'artifact': artifact}})
for p in scan['profiles']:
    p['identity'].update(package=out.name, manifest_sha256=identity,
                         artifact_sha256=manifest['files'][p['identity']['artifact']])
save(c / 'scan-manifest.json', scan)
side = json.loads((c / 'native-gates.json').read_text())
side['package_manifest_sha256'] = identity
side['initialization']['manifest']['sha256'] = sha(c / 'scan-manifest.json')
side['namespaces']['owner_artifact']['sha256'] = manifest['files']['payload/route/libapp_native_loader.so']
save(c / 'native-gates.json', side)
for name in ['child-build-receipt.json', 'scoped-build-receipt.json', 'child-inputs.json', 'consumer-audit.json', 'bionic-link-receipt.json']:
    shutil.copy2(HERE / name, c / name)
validate_upgrade(load_package(u7), load_package(out))
assert not (out / 'payload/android/lib64/libz.so').exists()
assert manifest['files']['payload/android/lib64/libart.so'] == load_package(u7)['files']['payload/android/lib64/libart.so']
assert manifest['bridge_sha256'] == load_package(u7)['bridge_sha256']
save(HERE / 'package.json', {'package': out.name, 'manifest_sha256': identity,
                            'n8_manifest': sha(base / 'package.json'),
                            'u7_native_manifest': sha(u7 / 'package.json'),
                            'changes_from_n8': changes, 'board_writes': False})
print(out, identity)
