"""Read supplied F-Droid index bytes and emit compact selection evidence."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INDEX_SHA = 'e0fde6a3d0882f4ff88b48b594e4cb818e4ad5ed46005007c47d203a2819d330'
GROUP_PATTERNS = {'compose': r'jetpack compose', 'webview': r'webview', 'gl': r'glsl|opengl'}


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def select_version(package):
    signer = package['metadata'].get('preferredSigner')
    eligible = []
    for version in package['versions'].values():
        manifest = version['manifest']
        abis = manifest.get('nativecode', [])
        prerelease = re.search(r'(?:alpha|beta)(?:\d|\W|$)|(?:^|[.\-])rc\d',manifest['versionName'],re.IGNORECASE)
        if version.get('releaseChannels') or version.get('antiFeatures') or prerelease:
            continue
        if signer and signer not in manifest['signer']['sha256']:
            continue
        if abis and 'arm64-v8a' not in abis:
            continue
        if manifest.get('usesSdk', {}).get('minSdkVersion', 1) > 36:
            continue
        eligible.append(version)
    if not eligible:
        raise ValueError('no stable preferred-signer arm64-or-ABI-free version')
    return max(eligible, key=lambda version: version['manifest']['versionCode'])


def collect(index_path, entry_path, existing_path):
    raw = index_path.read_bytes()
    if digest(raw) != INDEX_SHA:
        raise ValueError('index SHA mismatch')
    index = json.loads(raw)
    with zipfile.ZipFile(entry_path) as archive:
        entry_raw = archive.read('entry.json')
    entry = json.loads(entry_raw)
    if entry['index']['sha256'] != INDEX_SHA or entry['index']['size'] != len(raw):
        raise ValueError('entry/index identity mismatch')
    existing_raw = existing_path.read_bytes()
    existing = json.loads(existing_raw)
    excluded_packages = {app['package'] for app in existing['apps'] if app.get('package')}
    resolved = []
    for app in existing['apps']:
        if app.get('package'):
            continue
        metadata_path = Path.home()/'a2hlab/app-inputs'/app['key']/'app-input.json'
        metadata_raw = metadata_path.read_bytes()
        application = json.loads(metadata_raw)['application']
        package_id = application['package']
        excluded_packages.add(package_id)
        resolved.append(dict(key=app['key'],package=package_id,metadata_sha256=digest(metadata_raw),
                             source='HOME/a2hlab/app-inputs/'+app['key']+'/app-input.json'))
    excluded = sorted(excluded_packages)
    seeds = json.loads((HERE/'seeds.json').read_text())
    selected = []
    packages_seen = set()
    hashes_seen = set()
    for group, packages in seeds.items():
        for package_id in packages:
            if package_id in excluded or package_id in packages_seen:
                raise ValueError('existing or duplicate package: '+package_id)
            package = index['packages'][package_id]
            version = select_version(package)
            manifest = version['manifest']
            if group == 'priority' and manifest.get('nativecode'):
                raise ValueError('priority candidate declares nativecode: '+package_id)
            apk_sha = version['file']['sha256']
            if apk_sha in hashes_seen:
                raise ValueError('duplicate selected APK hash')
            metadata = package['metadata']
            description = metadata.get('description', {}).get('en-US', '')
            cue = None
            if group != 'priority':
                match = re.search(GROUP_PATTERNS[group], description, re.IGNORECASE)
                if match is None:
                    raise ValueError('coverage description missing: '+package_id)
                cue = dict(token=match.group(), offset=match.start(), description_sha256=digest(description.encode()))
            selected.append(dict(package=package_id, group=group,
                                 metadata={field:metadata.get(field) for field in ['name','sourceCode','license','categories','preferredSigner']},
                                 version={field:version.get(field) for field in ['file','manifest','src','added']},
                                 coverage_cue=cue,description_sha256=digest(description.encode())))
            packages_seen.add(package_id)
            hashes_seen.add(apk_sha)
    return dict(schema_version=1,index=dict(url='https://f-droid.org/repo/index-v2.json',sha256=INDEX_SHA,
                                          bytes=len(raw),packages=len(index['packages']),timestamp=index['repo']['timestamp']),
                entry=dict(url='https://f-droid.org/repo/entry.jar',sha256=digest(entry_path.read_bytes()),
                           entry_json_sha256=digest(entry_raw),index_reference=entry['index'],
                           signature_verification='not performed by this lane; identity binding only'),
                existing=dict(path='benchmark/2026-09-28-bms-route-deploy/batch/apps.json',sha256=digest(existing_raw),
                              key_count=len(existing['apps']),packages=excluded,resolved_null_packages=resolved),
                repo_address=index['repo']['address'],selected=selected,
                limitations=['No APK bytes examined in this index intake.',
                             'Absence of nativecode is repository manifest evidence, not source language or AndroidX proof.',
                             'Description tokens label coverage intent; they are not DEX reachability evidence.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    workspaces = Path(os.environ.get('WORKSPACES', ROOT.parent))
    parser.add_argument('--index',type=Path,default=workspaces/'westlake-inputs/corpus-v2/fdroid/index-v2.json')
    parser.add_argument('--entry',type=Path,default=workspaces/'westlake-inputs/corpus-v2/fdroid/entry.jar')
    parser.add_argument('--existing',type=Path,default=workspaces/'westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/apps.json')
    args = parser.parse_args()
    print(json.dumps(collect(args.index,args.entry,args.existing),ensure_ascii=False,sort_keys=True,indent=2))
