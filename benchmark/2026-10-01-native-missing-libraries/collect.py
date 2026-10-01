"""Read-only U8 ELF, DEX and PID evidence collection; print JSON to stdout."""

import base64
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KEYS = {'fd-im-vector-app', 'burgerking', 'mindustry', 'cv2-com-chessclock-android'}
PINS = {
    'alias': '50b9ab6af637c8573736a595417f6177d5845d21fc48da5b8e1299a078b1e48d',
    'zlib': 'ab0820c6a33c58f2b5aa6d7b5f967f0eae42319baa2d7a42b779d1583f8a14fc',
    'android_audio': '5891f899c2b21dcb24fa2f4cb3db78fbb34597740600c096dd8f633b831c5347',
    'oh_audio': '05d8ac90dbced47c8b47275a5d978bc922d4d8f6f84cd3df1b456633ae6d1100',
    'runtime': '216b68fbb3a40b5ac7a90b726f6d8184fa7cdba848ccde56c809abd400a660df',
    'nativeloader': 'fb9dc9372c9d9f1f38f9bc5b218a1a21a3a96ba63c87e2e0bfc0396dd102e159',
    'app_loader': 'eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c',
    'framework': '3e106350d882cd1f2f6d71c3cc4e9f124412d16f50a2dcb160007c34e6dde9af',
    'presence_mediandk': '110d02fc4bbb32ed241358c6329f6aa5e4849f021e5b224f9ae2b826f8fa75fb',
}
PLAN_PINS = {
    'LIBZ-PLAN.md': '229e3320b8ec181a2ed34d58068133080dc2ca690e4aa1aeeb71328587ac6dfd',
    'LIBMEDIANDK-PLAN.md': '008ed441020fddf9d3bb1cf7d25f9da56d0a49627e86ed8d010cd1391e616abe',
    'LIBMEDIANDK-PLAN-v2.md': '6be0a463729d3b75f6903a834365eeb28e4e3802bc3c8ef1c2e71febb6307aaf',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(data, expected):
    if sha(data) != expected:
        raise ValueError('SHA256 mismatch; no donor inference allowed')


def dynamic(text):
    return dict(needed=re.findall(r'\(NEEDED\).*?\[([^]]+)\]', text),
                soname=re.findall(r'\(SONAME\).*?\[([^]]+)\]', text))


def symbols(text):
    defined, undefined = {}, set()
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].rstrip(':').isdigit():
            continue
        name = fields[7].split('@')[0]
        if fields[6] == 'UND':
            undefined.add(name)
        elif fields[4] in {'GLOBAL', 'WEAK'} and fields[5] in {'DEFAULT', 'PROTECTED'}:
            defined[name] = dict(type=fields[3], size=int(fields[2]))
    return dict(defined=defined, undefined=sorted(undefined))


def require_coverage(required, exports):
    missing = sorted(set(required) - set(exports))
    if missing:
        raise ValueError('Provider misses exact imports: ' + ', '.join(missing))


def elf(path, expected, readelf):
    data = path.read_bytes()
    verify(data, expected)
    if data[:6] != b'\x7fELF\x02\x01' or int.from_bytes(data[18:20], 'little') != 183:
        raise ValueError('Expected little-endian ELF64 AArch64')
    completed = subprocess.run([readelf, '-d', '--dyn-syms', '--wide', str(path)],
                               capture_output=True, text=True, check=True, timeout=30)
    if completed.stderr.strip():
        raise ValueError('Unexpected readelf stderr')
    return dict(sha256=expected, bytes=len(data), **dynamic(completed.stdout), **symbols(completed.stdout))


def portable(path, workspaces):
    value = str(path)
    return value.replace(str(workspaces), '$WORKSPACES').replace(str(Path.home()), '$HOME')


def collect(workspaces):
    readelf = os.environ.get('LLVM_READELF', '/opt/homebrew/opt/llvm/bin/llvm-readelf')
    generation = workspaces / 'westlake-generation-u8-j9-t7e/native'
    master = workspaces / 'westlake-harness'
    expected = ROOT / 'benchmark/2026-10-01-b10-registration-impact/expected-u8.json'
    artifact_names = {'zlib': 'libshared_libz.z.so', 'android_audio': 'libOpenSLES.so',
                      'runtime': 'liboh_android_runtime.so', 'framework': '../framework/framework.jar',
                      'nativeloader': 'libnativeloader.so', 'app_loader': 'libapp_native_loader.so'}
    identity_paths = [generation / 'payload/android/lib64' / name for name in artifact_names.values()]
    identity = subprocess.run([sys.executable, str(master / 'scripts/lab/artifact_identity.py'),
                              *map(str, identity_paths), '--expected', str(expected)],
                             capture_output=True, text=True, timeout=30)
    if identity.returncode:
        raise ValueError('artifact_identity refused U8 inputs: ' + identity.stdout)
    paths = {label: path for label, path in zip(artifact_names, identity_paths)}
    paths.update(alias=workspaces / '01.OH61AOSP16/real-work/.state/build-oh-component-hw248/m1-route-a-generation-20260825-r109c-zlib-global/route-a-generation/pass1/zlib/libz.so',
                 oh_audio=generation / 'native-checks/system-elf' / PINS['oh_audio'],
                 presence_mediandk=generation / 'payload/zigzag/libmediandk.so')
    providers = {name: dict(path=portable(path, workspaces), **elf(path, PINS[name], readelf))
                 for name, path in paths.items() if name != 'framework'}
    providers['oh_audio']['scope'] = 'U8 native-gates system snapshot, not runtime fingerprint'
    package = json.loads((generation / 'package.json').read_text())
    if any(Path(name).name == 'libz.so' for name in package['files']):
        raise ValueError('U8 alias inventory changed; re-audit absence conclusion')
    plans = []
    for name, pin in PLAN_PINS.items():
        file_path = workspaces / 'westlake-inputs/plans-from-e8903af49' / name
        verify(file_path.read_bytes(), pin)
        original = subprocess.run(['git', '-C', str(master), 'show',
            'e8903af49:benchmark/2026-10-01-native-symbol-clusters/' + name],
            capture_output=True, check=True).stdout
        verify(original, pin)
        plans.append(dict(name=name, sha256=pin, commit='e8903af49', path=portable(file_path, workspaces)))
    cohort_dir = ROOT / 'benchmark/2026-10-01-b10-theme-graphics'
    sys.path.insert(0, str(cohort_dir))
    specification = importlib.util.spec_from_file_location('missing_library_cohort', cohort_dir / 'collect.py')
    cohort = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(cohort)
    entries = {entry['key']: entry for entry in cohort.inputs(workspaces) if entry['key'] in KEYS}
    facts_path = ROOT / 'benchmark/2026-10-01-b10-libart-impact/bitvector-facts.json.gz.b64'
    facts = json.loads(gzip.decompress(base64.b64decode(facts_path.read_bytes())))
    selected = [row for row in facts['rows'] if row['key'] in KEYS]
    rows = []
    wanted_member = {'fd-im-vector-app': 'librealm-jni.so', 'burgerking': 'libmmkv.so', 'mindustry': 'libarc.so'}
    for row in selected:
        entry = entries[row['key']]
        payload = Path(entry['path']).read_bytes()
        verify(payload, entry['apk_sha256'])
        if row['apk_sha256'] != entry['apk_sha256']:
            raise ValueError('Run/APK identity mismatch')
        log_path = workspaces / row['source'] / 'hilog.txt'
        lines = log_path.read_text(errors='replace').splitlines()
        evidence = []
        for number, line in enumerate(lines, 1):
            prefix = re.match(r'^\d\d-\d\d\s+\S+\s+(\d+)\s+(\d+)\s', line)
            if not prefix or int(prefix[1]) not in row['target_pids']:
                continue
            if any(token in line for token in ['main_threw', 'system library is absent', 'MediaPlayer.<clinit>',
                'MediaPlayer::native_init', 'register_android_media_MediaPlayer:', 'libz.so',
                'slCreateEngine', 'libOpenSLES.so: check ns accessible', '[ANL-N2]', '[N4-AUDIO]', '[N2-OWNER]']):
                evidence.append(dict(line=number, pid=int(prefix[1]), tid=int(prefix[2]), text=line))
        consumer = None
        with zipfile.ZipFile(Path(entry['path'])) as archive:
            members = [name for name in archive.namelist() if name.startswith('lib/') and name.endswith('.so')]
            if row['key'] in wanted_member:
                member = 'lib/arm64-v8a/' + wanted_member[row['key']]
                data = archive.read(member)
                with tempfile.TemporaryDirectory() as directory:
                    candidate = Path(directory) / wanted_member[row['key']]
                    candidate.write_bytes(data)
                    consumer = dict(member=member, **elf(candidate, sha(data), readelf))
            elif members:
                raise ValueError('Chessclock native inventory changed')
        rows.append(dict(key=row['key'], package=row['package'], apk_sha256=row['apk_sha256'],
            apk=portable(entry['path'], workspaces), native_consumer=consumer,
            hilog=row['source'] + '/hilog.txt', hilog_sha256=sha(log_path.read_bytes()),
            target_pids=row['target_pids'], evidence=evidence))
    framework = paths['framework']
    verify(framework.read_bytes(), PINS['framework'])
    from androguard.core.dex import DEX
    from loguru import logger
    logger.remove()
    with zipfile.ZipFile(framework) as archive:
        dex_bytes = archive.read('classes2.dex')
    verify(dex_bytes, '93c42bc94d795df0707be98d4ee3e5a729bb4852b88ee357decafc93dfd38cfb')
    media_class = next(clazz for clazz in DEX(dex_bytes).get_classes()
                       if clazz.get_name() == 'Landroid/media/MediaPlayer;')
    method = next(method for method in media_class.get_methods() if method.get_name() == '<clinit>')
    instructions, offset = [], 0
    for instruction in method.get_instructions():
        instructions.append(dict(offset=hex(offset), instruction=instruction.get_name() + ' ' + instruction.get_output()))
        offset += instruction.get_length()
    if 'media_jni' not in str(instructions) or 'native_init' not in str(instructions):
        raise ValueError('MediaPlayer load order changed')
    media = dict(framework_sha256=PINS['framework'], dex_sha256=sha(dex_bytes), instructions=instructions,
                 requested_library='libmedia_jni.so', owner='liboh_android_runtime.so',
                 owner_sha256=PINS['runtime'], JNI_OnLoad_exported='JNI_OnLoad' in providers['runtime']['defined'],
                 implementation='already registered 49/49 STUB methods, not real decoding', mediandk_unlock_proven=False)
    for name, provider in providers.items():
        provider['export_count'] = len(provider['defined'])
        provider['defined'] = {symbol: attributes for symbol, attributes in provider['defined'].items()
            if symbol.startswith(('SL_IID_', 'slCreateEngine', 'westlake_mediandk_', 'crc32', 'compress', 'uncompress',
                                  'inflate', 'deflate', 'zlibVersion')) or 'register_android_media_MediaPlayer' in symbol}
    for row in rows:
        if row['native_consumer']:
            row['native_consumer']['export_count'] = len(row['native_consumer']['defined'])
            row['native_consumer']['defined'] = {}
    return dict(schema_version=1, status='verified-offline-evidence; integration-and-device-pending',
        artifact_identity=dict(exit=identity.returncode, stdout=portable(identity.stdout, workspaces)),
        plans=plans, providers=providers, rows=rows, media=media,
        u8_package_sha256=sha((generation / 'package.json').read_bytes()), u8_alias_paths=[],
        limitations=['Symbol coverage is not audio playback, later-wall absence, or own UI',
                      'Inherited symbol ownership is not N2 same-domain closure proof'])


if __name__ == '__main__':
    print(json.dumps(collect(Path(os.environ.get('WORKSPACES', ROOT.parent))), indent=2))
