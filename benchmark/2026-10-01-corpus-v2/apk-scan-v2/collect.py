"""Rescan all DEX members for exact WebView content APIs without prefix pooling."""

import argparse
import collections
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

import rules

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'benchmark/2026-09-29-static-wall-prediction'))
import scan_apps


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def inspect_text(text, dex):
    current = None
    groups = collections.defaultdict(list)
    for number, line in enumerate(text.splitlines(), 1):
        header = scan_apps.HEADER.search(line)
        if header:
            current = header[1]
        instruction = scan_apps.INSN.search(line)
        if not instruction:
            continue
        invoke = scan_apps.INVOKE.search(instruction[2])
        if invoke and rules.webview_content('L'+invoke[3]+';', invoke[4]):
            groups[(invoke[3], invoke[4], invoke[5])].append(dict(dex=dex, method=current,
                offset=instruction[1], line=number, instruction=instruction[2]))
    return [dict(owner='L'+owner+';', name=name, descriptor=descriptor,
                 occurrence_count=len(examples), examples=examples[:3])
            for (owner, name, descriptor), examples in sorted(groups.items())]


def scan_one(arguments):
    row, apks, dexdump = arguments
    apk = Path(apks)/Path(row['apk_url']).name
    payload = apk.read_bytes()
    if digest(payload) != row['sha256']:
        raise ValueError('APK SHA mismatch: '+row['package'])
    dexes, calls = [], []
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix='cv2-v2-dex-') as directory:
        for member in sorted(archive.namelist()):
            if not re.fullmatch(r'classes\d*\.dex', member):
                continue
            data = archive.read(member)
            path = Path(directory)/member
            path.write_bytes(data)
            process = subprocess.run([dexdump, '-d', str(path)], capture_output=True, text=True, errors='replace')
            if process.returncode:
                raise ValueError('DEX parse failed: '+row['package']+'/'+member)
            dexes.append(dict(member=member, sha256=digest(data)))
            calls.extend(inspect_text(process.stdout, member))
    if not dexes:
        raise ValueError('No DEX members: '+row['package'])
    return dict(package=row['package'], apk_sha256=row['sha256'], dex=dexes, webview_content=calls)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apks', type=Path, required=True)
    parser.add_argument('--dexdump', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    selection_path = HERE.parent/'results.json'
    selection = json.loads(selection_path.read_text())
    arguments = [(row, str(args.apks), str(args.dexdump)) for row in selection['rows']]
    with ProcessPoolExecutor(max_workers=3) as pool:
        apps = list(pool.map(scan_one, arguments))
    dependencies = [Path(__file__), HERE/'rules.py', Path(scan_apps.__file__)]
    document = dict(schema='corpus-v2-precise-webview-v2', apps=apps,
        selection_sha256=digest(selection_path.read_bytes()), tool_sha256=digest(args.dexdump.read_bytes()),
        scanner_dependencies={str(path.relative_to(ROOT)):digest(path.read_bytes()) for path in dependencies},
        limitations='Direct WebView-owned content calls only; subclasses reflection branches dispatch and actual execution remain unknown')
    args.output.write_text(json.dumps(document, sort_keys=True, indent=2)+'\n')
    print('scanned', len(apps), 'DEX', sum(len(app['dex']) for app in apps), 'content-apps', sum(bool(app['webview_content']) for app in apps))


if __name__ == '__main__':
    main()
