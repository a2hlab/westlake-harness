"""Whole-member native API exposure with exact APK/sidecar identity and ABI scope."""

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
THEME = ROOT/'benchmark/2026-10-01-b10-theme-graphics'
sys.path.insert(0,str(THEME))
import collect
sys.path.insert(0,str(ROOT/'benchmark/2026-09-29-static-wall-prediction'))
ELF_SPEC = importlib.util.spec_from_file_location('b10_registration_elf',ROOT/'benchmark/2026-09-29-static-wall-prediction/rules85.py')
elf = importlib.util.module_from_spec(ELF_SPEC)
ELF_SPEC.loader.exec_module(elf)

API = re.compile(r'^(?:AAsset(?:Manager)?_|AndroidBitmap_|ANativeWindow_|AHardwareBuffer_|ASurfaceTexture_|ASurfaceControl_|ASurfaceTransaction_|AInputEvent_|AMotionEvent_|AKeyEvent_|ALooper_|AChoreographer_|ASensor(?:Manager|EventQueue)?_|AConfiguration_|AImage_|AImageReader_)\w+$')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(data, pin):
    if sha(data) != pin:
        raise ValueError('Native input SHA drift')


def exposure(data, parsed):
    imports = [dict(symbol=item['name'].split('@')[0],kind='weak-import' if item['weak'] else 'strong-import') for item in parsed['imports'] if API.fullmatch(item['name'].split('@')[0])]
    imported = {item['symbol'] for item in imports}
    dynamic = any(item['name'].split('@')[0] in {'dlsym','dlvsym','OHOS_dlsym'} for item in parsed['imports'])
    literals = []
    for match in re.finditer(rb'(?:(?<=\x00)|^)([A-Za-z_][A-Za-z_0-9]{3,160})\x00',data):
        name = match[1].decode('ascii')
        if API.fullmatch(name) and name not in imported:
            literals.append(dict(symbol=name,kind='literal-lookup-candidate' if dynamic else 'literal-only-unknown-use',file_offset=match.start(1)))
    return imports+literals


def member(name, data, pin=None):
    if pin:
        verify(data,pin)
    parsed = elf.elf_info(data)
    valid = parsed['header']=='valid-ELF64-AArch64'
    return dict(member=name,sha256=sha(data),bytes=len(data),header=parsed['header'],symbol_status=parsed.get('symbol_status'),
        scope='AArch64 inventory' if valid else 'unsupported-or-invalid-not-clean',needed=parsed['needed'],
        API_evidence=exposure(data,parsed) if valid else [],errors=parsed.get('errors',[]),execution_proved=False)


def inspect(entry):
    path = Path(entry['path'])
    payload = path.read_bytes()
    verify(payload,entry['apk_sha256'])
    libraries = []
    embedded = {}
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith('.so'):
                continue
            data = archive.read(name)
            parsed = member('APK!/'+name,data)
            libraries.append(parsed)
            embedded[name] = parsed
    metadata_path = path.parent/'app-input.json'
    metadata_sha = None
    missing = []
    if entry['cohort']=='u7-66' and metadata_path.is_file():
        metadata_payload = metadata_path.read_bytes()
        metadata_sha = sha(metadata_payload)
        metadata = json.loads(metadata_payload)
        if metadata['apk_sha256'] != entry['apk_sha256'] or metadata['application']['package'] != entry['package']:
            raise ValueError('Native metadata APK/package drift: '+entry['key'])
        for name, value in sorted(metadata['native_libraries'].items()):
            sidecar = path.parent/name
            if sidecar.is_file():
                data = sidecar.read_bytes()
                verify(data,value['sha256'])
                if name in embedded and embedded[name]['sha256']==value['sha256']:
                    embedded[name]['also_SHA_matched_sidecar'] = name
                else:
                    libraries.append(member('sidecar/'+name,data,value['sha256']))
            elif name in embedded and embedded[name]['sha256']==value['sha256']:
                embedded[name]['metadata_source'] = 'APK member; no physical sidecar'
            else:
                missing.append(dict(member=name,expected_sha256=value['sha256'],status='missing-sidecar-unverified'))
    return dict(key=entry['key'],package=entry['package'],apk_sha256=entry['apk_sha256'],cohort=entry['cohort'],
        metadata_sha256=metadata_sha,libraries=libraries,missing_sidecars=missing,
        limits='Imports and exact literals only; packed/decrypted/native-downloaded modules and computed dlsym names remain unknown. Current sidecar metadata is pinned separately, not claimed identical to a historical freeze.')


def summarize(apps):
    if len(apps)!=166 or len({row['key'] for row in apps})!=166:
        raise ValueError('Incomplete/duplicate 166 native cohort')
    symbols = defaultdict(lambda:dict(keys=set(),evidence=[]))
    for app in apps:
        for library in app['libraries']:
            for item in library['API_evidence']:
                group = symbols[item['symbol']]
                group['keys'].add(app['key'])
                group['evidence'].append(dict(key=app['key'],member=library['member'],member_sha256=library['sha256'],**item))
    rows = [dict(symbol=name,affected_keys=len(group['keys']),keys=sorted(group['keys']),evidence=group['evidence'],causal=False) for name,group in symbols.items()]
    rows.sort(key=lambda row:(-row['affected_keys'],row['symbol']))
    return dict(schema='b10-registration-consumers-v1',keys=166,apps=sorted(apps,key=lambda row:row['key']),API_groups=rows,
        libraries=sum(len(app['libraries']) for app in apps),AArch64_libraries=sum(library['header']=='valid-ELF64-AArch64' for app in apps for library in app['libraries']),
        keys_with_API_exposure=sorted({key for row in rows for key in row['keys']}),
        missing_sidecar_keys=sorted(app['key'] for app in apps if app['missing_sidecars']),
        scope='Reference counts, not execution/fatal/unlock counts; owners depend on actual runtime namespace')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspaces',type=Path,default=Path(os.environ.get('WORKSPACES',ROOT.parent)))
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    entries = collect.inputs(args.workspaces)
    with ProcessPoolExecutor(max_workers=3) as pool:
        apps = []
        for app in pool.map(inspect,entries):
            apps.append(app)
            print('NATIVE',len(apps),app['key'],len(app['libraries']),flush=True)
    result = summarize(apps)
    result['dependencies'] = {str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in [Path(__file__),Path(elf.__file__),THEME/'collect.py']}
    args.output.write_text(json.dumps(result,sort_keys=True)+'\n')


if __name__=='__main__':
    main()
