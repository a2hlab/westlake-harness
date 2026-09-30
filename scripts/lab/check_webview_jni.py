#!/usr/bin/env python3
"""Offline, pinned N3b ↔ runtime-JAR JNI ABI gate (not provider/runtime validation).

Use westlake-inputs/venv/bin/python (androguard 4.1.4 and pyelftools).
Exit 0: exact DEX definitions satisfy the contract; 1: mismatch; 2: invalid input.
"""
import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

NATIVE_SHA = '7c9c6240c7bbaa529460d7acb8e12629e3c9f9151b390a071f1d10a0bd727042'
SOURCE_SHA = 'ba5a3fe23d4a72f0406427e38b51259cc7c8fd0d04a7c78237d9f6d3fccac210'
ROOT = Path(__file__).resolve().parents[2]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def native_contract(source, native):
    from elftools.elf.elffile import ELFFile
    src, binary = Path(source).read_bytes(), Path(native).read_bytes()
    if digest(src) != SOURCE_SHA or digest(binary) != NATIVE_SHA:
        raise ValueError('N3b source/native SHA mismatch; this contract must not silently follow a different generation')
    text = src.decode()
    # This is a deliberately bounded extractor for the pinned TU, not a C++ parser.
    owner = re.search(r'jclass updateClass = env->FindClass\(\s*"([^"]+)"\)', text).group(1)
    lookups = re.findall(r'GetStaticMethodID\(\s*updateClass,\s*"([^"]+)",\s*"([^"]+)"', text)
    if len(lookups) != 2:
        raise ValueError('unexpected native lookup shape')
    requirements = [{'class': 'L' + owner + ';', 'name': n, 'descriptor': d,
                     'static': True, 'native': None, 'direction': 'native_to_java'} for n, d in lookups]
    wrappers = re.findall(r'JNIEXPORT jboolean JNICALL\s+(Java_adapter_core_WestlakeWebViewInstall_\w+)\(JNIEnv\* env, jclass\)', text)
    if len(wrappers) != 2:
        raise ValueError('unexpected JNI wrapper shape')
    elf = ELFFile(io.BytesIO(binary))
    symbols = elf.get_section_by_name('.dynsym')
    exported = {s.name for s in symbols.iter_symbols() if s['st_shndx'] != 'SHN_UNDEF'
                and s['st_info']['bind'] == 'STB_GLOBAL' and s['st_other']['visibility'] == 'STV_DEFAULT'}
    for symbol in wrappers:
        if symbol not in exported:
            raise ValueError('JNI export absent: ' + symbol)
        requirements.append({'class': 'Ladapter/core/WestlakeWebViewInstall;',
                             'name': symbol.removeprefix('Java_adapter_core_WestlakeWebViewInstall_'),
                             'descriptor': '()Z', 'static': True, 'native': True,
                             'direction': 'java_to_native', 'export': symbol})
    for row in requirements[:2]:
        for literal in [owner, row['name'], row['descriptor']]:
            if literal.encode() + b'\0' not in binary:
                raise ValueError('source lookup literal absent in native image: ' + literal)
    return {'source_sha256': digest(src), 'native_sha256': digest(binary), 'requirements': requirements}


def dex_definitions(jars):
    from loguru import logger
    logger.disable('androguard')
    from androguard.core.dex import DEX
    index, inputs = {}, []
    for path in jars:
        path = Path(path).resolve(); data = path.read_bytes()
        jar = {'path': str(path), 'sha256': digest(data), 'dex': []}
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = [i for i in archive.infolist() if re.fullmatch(r'classes(?:[2-9]|[1-9]\d+)?\.dex', i.filename)]
            if not members or len({i.filename for i in members}) != len(members):
                raise ValueError('missing or duplicate classes*.dex members: ' + str(path))
            for member in members:
                blob = archive.read(member)
                dex = DEX(blob)
                count = 0
                for cls in dex.get_classes():
                    methods = [{'name': m.get_name(), 'descriptor': re.sub(r'\s+', '', m.get_descriptor()),
                                'flags': m.get_access_flags(), 'has_code': m.get_code_off() != 0} for m in cls.get_methods()]
                    row = {'class': cls.get_name(), 'superclass': cls.get_superclassname(), 'methods': methods,
                           'jar': str(path), 'dex': member.filename}
                    index.setdefault(row['class'], []).append(row)
                    count += 1
                jar['dex'].append({'member': member.filename, 'sha256': digest(blob), 'defined_classes': count})
        inputs.append(jar)
    return index, inputs


def resolve(index, requirement):
    owner = requirement['class']; current = owner; visited = set(); overloads = []
    while current and current not in visited:
        visited.add(current)
        definitions = index.get(current, [])
        if len(definitions) > 1:
            return {'passed': False, 'reason': 'duplicate_class_definition', 'owner': current}
        if not definitions:
            break
        cls = definitions[0]
        overloads += [dict(m, owner=current) for m in cls['methods'] if m['name'] == requirement['name']]
        matches = [m for m in cls['methods'] if (m['name'], m['descriptor']) == (requirement['name'], requirement['descriptor'])]
        if len(matches) > 1:
            return {'passed': False, 'reason': 'duplicate_method_definition', 'owner': current}
        if matches:
            method = matches[0]; flags = method['flags']
            why = None
            if bool(flags & 0x8) != requirement['static']:
                why = 'static_flag_mismatch'
            elif requirement['native'] is not None and bool(flags & 0x100) != requirement['native']:
                why = 'native_flag_mismatch'
            elif flags & 0x400:
                why = 'abstract_method'
            elif not (flags & 0x100) and not method['has_code']:
                why = 'method_has_no_code'
            return {'passed': why is None, 'reason': why or 'exact_definition', 'owner': current,
                    'jar': cls['jar'], 'dex': cls['dex'], 'flags': flags, 'has_code': method['has_code']}
        # Native declarations must belong to the exported JNI owner. GetStaticMethodID
        # can resolve inherited Java implementations when their definitions are supplied.
        if requirement['direction'] == 'java_to_native':
            break
        current = cls['superclass']
    return {'passed': False, 'reason': 'missing_class_definition' if owner not in index else 'missing_exact_method',
            'owner': owner, 'observed_overloads': overloads}


def check(jars, source, native):
    contract = native_contract(source, native)
    index, inputs = dex_definitions(jars)
    checks = [dict(requirement=r, **resolve(index, r)) for r in contract['requirements']]
    return {'schema': 1, 'device_io': False, 'passed': all(r['passed'] for r in checks),
            'contract': contract, 'jars': inputs, 'checks': checks,
            'scope': 'adapter JNI names/descriptors/static/native flags and ELF exports only',
            'not_proven': ['actual ART ClassLoader resolution', 'provider APK/native closure',
                           'Binder/cache identity', 'pre/post-bind timing', 'WebView rendering',
                           'platform and dynamic-object JNI lookups']}


def main():
    import lab_paths
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--jar', type=Path, action='append', required=True)
    ap.add_argument('--source', type=Path, default=ROOT / 'benchmark/2026-09-30-n3b-webview/src/webview_publication.cpp')
    ap.add_argument('--native', type=Path)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    try:
        native = args.native or lab_paths.workspaces() / 'westlake-generation-n3b-53bb18d1/payload/android/lib64/liboh_android_runtime.so'
        report = check(args.jar, args.source, native)
        rc = 0 if report['passed'] else 1
    except Exception as e:
        # Parser exceptions are invalid input, never a compatibility pass. Keep
        # their type in the machine receipt; KeyboardInterrupt still propagates.
        report = {'device_io': False, 'passed': False, 'input_error': str(e), 'error_type': type(e).__name__}
        rc = 2
    text = json.dumps(report, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(text)
    print(text, end='')
    return rc


if __name__ == '__main__':
    sys.exit(main())
