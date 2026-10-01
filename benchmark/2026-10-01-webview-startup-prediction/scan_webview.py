"""Offline WebView scope scan: exact DEX, subclasses, XML and bounded lifecycle."""

import argparse
from concurrent.futures import ProcessPoolExecutor
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
B10 = ROOT / 'benchmark/2026-10-01-b10-theme-graphics'
sys.path.insert(0, str(B10))
import collect as b10
import rules as lifecycle

PACKAGES = {
    'de.koelle.christian.trickytripper', 'dev.obfusk.jiten_webview',
    'com.caniwebview.android', 'com.stoutner.privacybrowser.standard',
    'com.knirirr.beecount', 'eu.dfdx.jslab', 'com.degeder.yam',
}
WEBVIEW = 'Landroid/webkit/WebView;'
SETTINGS = 'Landroid/webkit/WebSettings;'
FRAGMENT_CALLBACKS = {'onCreate', 'onCreateView', 'onViewCreated', 'onActivityCreated', 'onResume'}


def web_owner(owner, classes):
    chain = set(lifecycle.ancestors(owner, classes))
    return bool(chain & {WEBVIEW, SETTINGS})


def parse_dex(lines, member):
    classes, methods = {}, {}
    owner = name = current = None
    in_methods = False
    for number, line in enumerate(lines, 1):
        if "Class descriptor  : '" in line:
            owner = line.split("'")[1]
            classes[owner] = None
            current = None
            in_methods = False
        elif line.startswith('  Superclass'):
            classes[owner] = line.split("'")[1] if "'" in line else None
        elif line.startswith(('  Direct methods', '  Virtual methods')):
            in_methods = True
        elif in_methods and re.match(r'    #\d+\s+: \(in ', line):
            current = name = None
        elif in_methods and line.startswith('      name'):
            name = line.split("'")[1]
        elif in_methods and name and line.startswith('      type'):
            descriptor = line.split("'")[1]
            current = dict(owner=owner, name=name, descriptor=descriptor, dex=member,
                           line=number, branches=0, callees=set(), body=[], calls=[])
            methods[owner+'->'+name+descriptor] = current
        elif current is not None:
            instruction = re.search(r'\|([0-9a-f]{4,}): (.+)', line)
            if not instruction:
                continue
            offset, body = instruction.groups()
            opcode = body.split()[0]
            current['branches'] += int(opcode.startswith(('if-', 'packed-switch', 'sparse-switch')))
            witness = dict(line=number, offset=offset, instruction=body)
            current['body'].append(witness)
            call = b10.CALL.search(body) if opcode.startswith('invoke-') else None
            if call:
                target_owner, target_name, descriptor = call.groups()
                target = target_owner+'->'+target_name+descriptor
                current['callees'].add(target)
                current['calls'].append(dict(witness, owner=target_owner, name=target_name,
                                              descriptor=descriptor, target=target))
    return classes, methods


def resource_layouts(text):
    resource = name = None
    output = {}
    for number, line in enumerate(text.splitlines(), 1):
        header = re.match(r'\s*resource (0x[0-9a-f]+) ([\w:]+)/(\S+)', line)
        if header:
            resource = header[1] if header[2].split(':')[-1] == 'layout' else None
            name = header[3]
        elif resource:
            match = re.search(r'\(([^)]*)\) \(file\) (res/\S+\.xml)', line)
            if match:
                output.setdefault(resource, []).append(dict(name=name, member=match[2], config=match[1], line=number))
    return output


def layout_mentions(body, layout_ids):
    output = []
    for witness in body:
        for literal in re.findall(r'(?:0x|#)(7f[0-9a-f]{6})\b', witness['instruction']):
            resource = '0x'+literal
            if resource in layout_ids:
                output.append(dict(witness, resource=resource))
    return output


def inspect(entry, tools):
    apk = Path(entry['path'])
    if b10.digest(apk.read_bytes()) != entry['apk_sha256']:
        raise ValueError('APK hash mismatch: '+entry['key'])
    xml = subprocess.check_output([tools['aapt2'], 'dump', 'xmltree', str(apk), '--file', 'AndroidManifest.xml'], text=True)
    manifest = b10.manifest(xml)
    if manifest['package'] != entry['package']:
        raise ValueError('Package mismatch: '+entry['key'])
    resources = subprocess.check_output([tools['aapt2'], 'dump', 'resources', str(apk)], text=True, errors='replace')
    layout_map = resource_layouts(resources)
    classes, methods, dexes = {}, {}, []
    layouts = []
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix='wv-dex-') as temporary:
        for member in sorted(archive.namelist()):
            if not re.fullmatch(r'classes\d*\.dex', member):
                continue
            data = archive.read(member)
            path = Path(temporary)/member
            path.write_bytes(data)
            with tempfile.TemporaryFile() as errors:
                process = subprocess.Popen([tools['dexdump'], '-d', str(path)], stdout=subprocess.PIPE, stderr=errors, text=True, errors='replace')
                parsed_classes, parsed_methods = parse_dex(process.stdout, member)
                process.stdout.close()
                if process.wait():
                    raise ValueError('DEX parse failure: '+entry['key'])
            if classes.keys() & parsed_classes.keys():
                raise ValueError('Duplicate DEX class: '+entry['key'])
            classes.update(parsed_classes)
            methods.update(parsed_methods)
            dexes.append(dict(member=member, sha256=b10.digest(data)))
        subclasses = {owner.strip('L;').replace('/', '.') for owner in classes if WEBVIEW in lifecycle.ancestors(owner, classes)}
        for resource, variants in layout_map.items():
            for variant in variants:
                data = archive.read(variant['member'])
                names = ['WebView', *sorted(subclasses)]
                if not any(name.encode() in data or name.encode('utf-16le') in data for name in names):
                    continue
                dump = subprocess.check_output([tools['aapt2'], 'dump', 'xmltree', str(apk), '--file', variant['member']], text=True, errors='replace')
                tags = [dict(line=number, text=line.strip()) for number, line in enumerate(dump.splitlines(), 1)
                        if any(name in line for name in names)]
                if tags:
                    layouts.append(dict(resource=resource, **variant, sha256=b10.digest(data), tags=tags, xml=dump))
    contexts, caps = {}, {}
    startup = set(manifest['launchers']) | set(manifest['early_owners'])
    for activity in sorted(startup | {row['target'] for row in manifest['activities'] if row['enabled']}):
        contexts[activity], caps[activity] = lifecycle.reach(lifecycle.roots(activity, classes, methods), classes, methods)
    sites, anchors, bodies = [], [], {}
    layout_ids = {row['resource'] for row in layouts}
    startup_roots = {root for activity in startup for root in lifecycle.roots(activity, classes, methods)}
    for identifier, method in methods.items():
        active = [dict(activity=activity, tier='startup-chain' if activity in startup else 'later-activity-lifecycle', **visited[identifier])
                  for activity, visited in contexts.items() if identifier in visited]
        calls = [call for call in method['calls'] if web_owner(call['owner'], classes)]
        layout_refs = layout_mentions(method['body'], layout_ids)
        fragment = method['name'] in FRAGMENT_CALLBACKS and any('Fragment;' in ancestor for ancestor in lifecycle.ancestors(method['owner'], classes))
        for call in calls:
            sites.append(dict(method=identifier, dex=method['dex'], contexts=active, fragment_callback=fragment, **call))
        if layout_refs:
            anchors.append(dict(method=identifier, dex=method['dex'], contexts=active, fragment_callback=fragment,
                                resources=layout_refs, inflation_calls=[call for call in method['calls'] if call['name'] in {'inflate', 'setContentView'}],
                                limits='Same-method resource literal; not general argument/data-flow proof'))
        if calls or layout_refs or identifier in startup_roots:
            bodies[identifier] = dict(dex=method['dex'], line=method['line'], instructions=method['body'])
    application_prefix = 'L'+entry['package'].replace('.', '/')+'/'
    callbacks = {identifier: dict(dex=method['dex'], line=method['line'], instructions=method['body'])
                 for identifier, method in methods.items() if method['owner'].startswith(application_prefix)
                 and (method['name'] in {'onOptionsItemSelected', 'onCreateOptionsMenu', 'onClick'} or
                      method['name'] in FRAGMENT_CALLBACKS and 'Fragment;' in ' '.join(lifecycle.ancestors(method['owner'], classes)))}
    bodies.update(callbacks)
    return dict(key=entry['key'], package=entry['package'], apk_sha256=entry['apk_sha256'], apk_name=apk.name,
                dex=dexes, manifest=manifest, manifest_dump=xml, layouts=layouts, webview_sites=sites,
                layout_anchors=anchors, method_bodies=bodies, capped_contexts=[key for key, capped in caps.items() if capped],
                counts=dict(classes=len(classes), methods=len(methods), webview_sites=len(sites)),
                limits='Exact calls plus bounded inherited lifecycle; XML/Fragment dispatch and branch outcomes require separate witnesses')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workspaces', type=Path, default=Path(os.environ.get('WORKSPACES', ROOT.parent)))
    args = parser.parse_args()
    entries = [row for row in b10.inputs(args.workspaces) if row['package'] in PACKAGES]
    if {row['package'] for row in entries} != PACKAGES or len(entries) != 7:
        raise ValueError('Incomplete seven-key cohort')
    tools = {name: str(Path.home()/'Library/Android/sdk/build-tools/37.0.0'/name) for name in ['aapt2', 'dexdump']}
    with ProcessPoolExecutor(max_workers=3) as pool:
        apps = list(pool.map(inspect, entries, [tools]*len(entries)))
    result = dict(schema='webview-startup-facts-v1', apps=apps,
                  tools={name:b10.digest(Path(path).read_bytes()) for name, path in tools.items()},
                  scanner_dependencies={str(path.relative_to(ROOT)):b10.digest(path.read_bytes()) for path in [Path(__file__),B10/'collect.py',B10/'rules.py']})
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2)+'\n')
    print('scanned', len(apps), 'DEX', sum(len(app['dex']) for app in apps))


if __name__ == '__main__':
    main()
