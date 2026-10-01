"""Exact U8 class membership plus whole-DEX references and staged conditional RTA."""

import argparse
from array import array
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import struct
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'harness'))
from westlake_gap import reach

THEME = ROOT/'benchmark/2026-10-01-b10-theme-graphics'
sys.path.insert(0, str(THEME))
import collect as theme_collect

BOOT = ['core-oj', 'core-libart', 'core-icu4j', 'okhttp', 'bouncycastle', 'apache-xml', 'framework', 'oh-adapter-framework', 'adapter-mainline-stubs']
CLASS_REF = re.compile(r'L[^;()\s]+;')
INSTRUCTION = re.compile(r'\|([0-9a-f]{4,}): (.+)')
FIELD = re.compile(r'(L[^ ;]+;)\.([^\s:]+):([^ ]+)\s+// field@')


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def descriptors(text):
    return set(CLASS_REF.findall(text))


def uleb(data, offset):
    result = shift = 0
    while True:
        value = data[offset]
        offset += 1
        result |= (value & 127) << shift
        if value < 128:
            return result, offset
        shift += 7
        if shift > 28:
            raise ValueError('Invalid DEX ULEB')


def dex_metadata(data):
    if data[:4] != b'dex\n' or len(data) < 112:
        raise ValueError('Unsupported or truncated DEX')
    string_count, string_offset, type_count, type_offset, proto_count, proto_offset, field_count, field_offset, method_count, method_offset, class_count, class_offset = struct.unpack_from('<12I', data, 56)
    strings = []
    for index in range(string_count):
        position = struct.unpack_from('<I', data, string_offset+index*4)[0]
        _, position = uleb(data, position)
        strings.append(data[position:data.index(b'\0', position)].replace(b'\xc0\x80', b'\0').decode('utf-8', 'surrogatepass'))
    types = [strings[struct.unpack_from('<I', data, type_offset+index*4)[0]] for index in range(type_count)]

    def type_list(offset):
        return [types[struct.unpack_from('<H', data, offset+4+index*2)[0]] for index in range(struct.unpack_from('<I', data, offset)[0])] if offset else []

    protos = []
    for index in range(proto_count):
        _, return_type, parameters = struct.unpack_from('<3I', data, proto_offset+index*12)
        protos.append('('+''.join(type_list(parameters))+')'+types[return_type])
    method_ids = []
    for index in range(method_count):
        owner, proto, name = struct.unpack_from('<HHI', data, method_offset+index*8)
        method_ids.append((types[owner], strings[name], protos[proto]))
    field_ids = []
    for index in range(field_count):
        owner, field_type, name = struct.unpack_from('<HHI', data, field_offset+index*8)
        field_ids.append((types[owner], strings[name], types[field_type]))
    classes = {}
    for index in range(class_count):
        owner, access, parent, interfaces, _, annotations, class_data, _ = struct.unpack_from('<8I', data, class_offset+index*32)
        node = dict(super=types[parent] if parent != 0xffffffff else '', interfaces=type_list(interfaces), methods=[], fields=[], annotations=bool(annotations), access=access)
        if class_data:
            counts = []
            for _ in range(4):
                count, class_data = uleb(data, class_data)
                counts.append(count)
            for count in counts[:2]:
                field_index = 0
                for _ in range(count):
                    delta, class_data = uleb(data, class_data)
                    flags, class_data = uleb(data, class_data)
                    field_index += delta
                    node['fields'].append(dict(name=field_ids[field_index][1], descriptor=field_ids[field_index][2], flags=flags))
            for count in counts[2:]:
                method_index = 0
                for _ in range(count):
                    delta, class_data = uleb(data, class_data)
                    flags, class_data = uleb(data, class_data)
                    code, class_data = uleb(data, class_data)
                    method_index += delta
                    _, name, descriptor = method_ids[method_index]
                    node['methods'].append(dict(name=name, descriptor=descriptor, flags=flags, code=code))
        classes[types[owner]] = node
    return dict(classes=classes, types=sorted(set(types)), method_ids=method_ids)


def jar_index(path, label):
    classes = {}
    dexes = []
    with zipfile.ZipFile(path) as archive:
        for member in sorted(archive.namelist()):
            if not re.fullmatch(r'classes\d*\.dex', member):
                continue
            payload = archive.read(member)
            metadata = dex_metadata(payload)
            for owner, node in metadata['classes'].items():
                classes.setdefault(owner, dict(artifact=label, super=node['super'], interfaces=node['interfaces'], methods=[method['name']+method['descriptor'] for method in node['methods']]))
            dexes.append(dict(member=member, sha256=sha(payload), classes=len(metadata['classes'])))
    if not dexes:
        raise ValueError('No DEX in boot input: '+label)
    return classes, dexes


def identity(workspaces):
    package = workspaces/'westlake-generation-u8-j9-t7e'
    bundle_path = package/'bundle.json'
    bundle = json.loads(bundle_path.read_text())
    baseline_path = ROOT/'benchmark/2026-10-01-u7-prospective/v1/expected-run.json'
    baseline = json.loads(baseline_path.read_text())
    expected = {**baseline['runtime_files'], **baseline['boot_files']}
    members = [*bundle['boot_group']['members'], bundle['runtime_jar']]
    for member in members:
        expected[member['target']] = member['sha256']
    receipt_path = workspaces/'westlake-harness-u7-executor/benchmark/2026-10-01-u8-rollout/landing/5cd/final.json'
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('match') is not True or receipt['fingerprints']['runtime']['sha256_12'] != 'e953c0921536' or receipt['fingerprints']['boot']['sha256_12'] != '4db882a81732':
        raise ValueError('U8 deployment receipt mismatch')
    selected = {}
    for name in BOOT+['oh-adapter-runtime']:
        target = '/system/android/framework/'+name+'.jar'
        changed = next((member for member in members if member['target']==target), None)
        path = package/changed['source'] if changed else package/'native/payload/android/framework'/Path(target).name
        if sha(path.read_bytes()) != expected[target]:
            raise ValueError('Jar byte drift: '+name)
        selected[name] = path
    selected['libart'] = package/'native/payload/android/lib64/libart.so'
    tool = workspaces/'westlake-harness/scripts/lab/artifact_identity.py'
    with tempfile.TemporaryDirectory(prefix='libart-identity-') as temporary:
        expected_path = Path(temporary)/'expected-u8.json'
        expected_path.write_text(json.dumps(expected))
        process = subprocess.run([sys.executable, str(tool), '--expected', str(expected_path), *map(str, selected.values())], capture_output=True, text=True)
    if process.returncode:
        raise ValueError('artifact_identity rejected input: '+process.stdout)
    runtime = {}
    jars = []
    for name in BOOT:
        classes, dexes = jar_index(selected[name], name+'.jar')
        for owner, node in classes.items():
            runtime.setdefault(owner, node)
        jars.append(dict(name=name+'.jar', path=str(selected[name].relative_to(workspaces)), sha256=sha(selected[name].read_bytes()), classes=len(classes), dex=dexes))
    auxiliary, aux_dex = jar_index(selected['oh-adapter-runtime'], 'oh-adapter-runtime.jar')
    evidence = dict(artifact_identity_exit=process.returncode, artifact_identity_stdout=process.stdout.replace(str(workspaces), '$WORKSPACES'),
        tool_sha256=sha(tool.read_bytes()), bundle_sha256=sha(bundle_path.read_bytes()), baseline_expected_sha256=sha(baseline_path.read_bytes()),
        expected_u8_sha256=sha(json.dumps(expected, sort_keys=True).encode()), receipt_path=str(receipt_path.relative_to(workspaces)), receipt_sha256=sha(receipt_path.read_bytes()),
        state=dict(RUNTIME='e953c0921536', BOOTIMAGE='4db882a81732'), jars=jars,
        auxiliary=dict(name='oh-adapter-runtime.jar', sha256=sha(selected['oh-adapter-runtime'].read_bytes()), classes=len(auxiliary), dex=aux_dex, scope='separate runtime loader; not a tenth boot jar'),
        libart_sha256=sha(selected['libart'].read_bytes()), reference_rule='U8 package reference files describe U7 baseline; target membership overlays bundle boot group and runtime jar before artifact_identity')
    return runtime, auxiliary, evidence


def manifest(text, selected_launcher=None):
    stack = []
    roots = []
    for line in text.splitlines():
        stripped = line.lstrip()
        depth = len(line)-len(stripped)
        if stripped.startswith('E: '):
            while stack and stack[-1]['depth'] >= depth:
                stack.pop()
            node = dict(tag=stripped.split()[1], depth=depth, attrs={}, children=[])
            (stack[-1]['children'] if stack else roots).append(node)
            stack.append(node)
        elif stripped.startswith('A: ') and stack:
            field, value = stripped[3:].split('=', 1)
            stack[-1]['attrs'][field.split('(')[0].rsplit(':', 1)[-1]] = value.split('"')[1] if value.startswith('"') else value.split()[0]
    root = next(node for node in roots if node['tag']=='manifest')
    app = next(node for node in root['children'] if node['tag']=='application')
    package = root['attrs']['package']
    qualify = lambda name: package+name if name.startswith('.') else name if '.' in name else package+'.'+name
    components = []
    launchers = []
    for node in app['children']:
        if node['tag'] not in {'activity', 'activity-alias', 'provider', 'service', 'receiver'} or not node['attrs'].get('name'):
            continue
        if node['attrs'].get('enabled') in {'false', '0', '0x00000000'}:
            continue
        name = qualify(node['attrs'].get('targetActivity', node['attrs']['name']))
        components.append(dict(name=name, kind='activity' if node['tag']=='activity-alias' else node['tag'], process=node['attrs'].get('process') if node['attrs'].get('process') not in {None, package} else None,
            meta_data={child['attrs'].get('name', ''):child['attrs'].get('value', '') for child in node['children'] if child['tag']=='meta-data'}))
        for child in node['children']:
            actions = {item['attrs'].get('name') for item in child['children'] if item['tag']=='action'}
            categories = {item['attrs'].get('name') for item in child['children'] if item['tag']=='category'}
            if 'android.intent.action.MAIN' in actions and 'android.intent.category.LAUNCHER' in categories:
                launchers.append(name)
    return dict(package=package, application_class=qualify(app['attrs']['name']) if app['attrs'].get('name') else None,
        app_component_factory=qualify(app['attrs']['appComponentFactory']) if app['attrs'].get('appComponentFactory') else None,
        main_activities=[selected_launcher] if selected_launcher else sorted(set(launchers)), components=components,
        application_meta_data={child['attrs'].get('name', ''):child['attrs'].get('value', '') for child in app['children'] if child['tag']=='meta-data'})


def prepare_graph(metadata):
    graph = reach.Graph()
    sites = []
    for dex_name, dex in metadata:
        for owner, node in dex['classes'].items():
            cid = graph.cls(owner)
            if cid in graph.defined:
                raise ValueError('Duplicate app DEX definition')
            graph.defined.add(cid)
            if node['super']:
                graph.supers[cid] = graph.cls(node['super'])
            graph.ifaces[cid] = [graph.cls(parent) for parent in node['interfaces']]
            for parent in [node['super'], *node['interfaces']]:
                if parent:
                    sites.append(dict(owner=owner, caller=None, dex=dex_name, reference=parent, kind='superclass' if parent==node['super'] else 'interface', offset=None))
            for field in node['fields']:
                sites.append(dict(owner=owner, caller=None, dex=dex_name, reference=field['descriptor'], member=field['name'], kind='field-declaration', offset=None))
            for method in node['methods']:
                mid = graph.meth(cid, graph.sig(method['name']+method['descriptor']))
                graph.cls_methods[cid][graph.m_sig[mid]] = mid
                graph.m_flags[mid] = int(bool(method['flags'] & 8)) | (2 if method['flags'] & 256 else 0) | (4 if method['code'] else 0)
                sites.append(dict(owner=owner, caller=graph.name(mid), dex=dex_name, reference=method['descriptor'], kind='method-declaration', offset=None))
    return graph, sites


def parse_code(lines, dex_name, graph, sites, absent, component_names):
    owner = name = current = None
    in_methods = False
    components = {'L'+name.replace('.', '/')+';' for name in component_names}
    clinit = graph.sig('<clinit>()V')
    for number, line in enumerate(lines, 1):
        if "Class descriptor  : '" in line:
            owner = line.split("'")[1]
            current = None
            in_methods = False
        elif line.startswith(('  Direct methods', '  Virtual methods')):
            in_methods = True
        elif in_methods and re.match(r'    #\d+\s+: \(in ', line):
            current = name = None
        elif in_methods and line.startswith('      name'):
            name = line.split("'")[1]
        elif in_methods and name and line.startswith('      type'):
            current = graph.meth(graph.cls(owner), graph.sig(name+line.split("'")[1]))
        elif current is not None and (instruction := INSTRUCTION.search(line)):
            offset, body = instruction.groups()
            opcode = body.split()[0]
            call = theme_collect.CALL.search(body) if opcode.startswith('invoke-') else None
            field = FIELD.search(body) if opcode.startswith(('iget', 'iput', 'sget', 'sput')) else None
            reference = ''
            if call:
                target_owner, target_name, descriptor = call.groups()
                target = graph.meth(graph.cls(target_owner), graph.sig(target_name+descriptor))
                graph.calls.setdefault(current, array('I')).append(target*2+int(opcode.startswith(('invoke-virtual', 'invoke-interface'))))
                if opcode.startswith('invoke-static'):
                    graph.calls[current].append(graph.meth(graph.cls(target_owner), clinit)*2)
                reference = target_owner+'->'+target_name+descriptor
            elif field:
                target_owner, target_name, descriptor = field.groups()
                reference = target_owner+'->'+target_name+':'+descriptor
                if opcode.startswith(('sget', 'sput')):
                    graph.calls.setdefault(current, array('I')).append(graph.meth(graph.cls(target_owner), clinit)*2)
            elif '// type@' in body:
                reference = body.split('//')[0]
                target_owner = next(iter(descriptors(reference)), None)
                if target_owner and opcode=='new-instance':
                    graph.news.setdefault(current, array('I')).append(graph.cls(target_owner))
                    graph.calls.setdefault(current, array('I')).append(graph.meth(graph.cls(target_owner), clinit)*2)
                if target_owner in components and opcode=='const-class':
                    graph.comps.setdefault(current, array('I')).append(graph.cls(target_owner))
            missing = sorted(descriptors(reference) & absent)
            if missing:
                sites.append(dict(owner=owner, caller=graph.name(current), dex=dex_name, reference=reference, kind='instruction', opcode=opcode,
                                  offset=offset, line=number, instruction=body, missing=missing))


class ReachabilityBudgetExceeded(Exception):
    pass


def stages(graph, facts, runtime, budget_seconds=60):
    result = reach.Reachability(graph, dict(classes=runtime))
    result.budget_truncated = False
    result.budget_seconds = budget_seconds
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)

    def budget_expired(signum, frame):
        raise ReachabilityBudgetExceeded()

    signal.signal(signal.SIGALRM, budget_expired)
    signal.setitimer(signal.ITIMER_REAL, budget_seconds)
    try:
        run_stages(graph, facts, result)
    except ReachabilityBudgetExceeded:
        result.budget_truncated = True
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        signal.signal(signal.SIGALRM, previous_handler)
    return result


def run_stages(graph, facts, result):
    descriptor = lambda name: 'L'+name.replace('.', '/')+';'
    stage_zero = [facts.get('application_class'), facts.get('app_component_factory'), *[node['name'] for node in facts['components'] if node['kind']=='provider' and not node['process']]]
    for value in [*facts.get('application_meta_data', {}).keys(), *facts.get('application_meta_data', {}).values()]:
        if descriptor(value) in graph.cls_ids:
            stage_zero.append(value)
    for stage, names in [(0, stage_zero), (1, facts['main_activities'])]:
        result.current = stage
        for name in filter(None, names):
            result.start_component(descriptor(name))
        result.run()
    result.current = 2
    while result.pending_components:
        batch, result.pending_components = result.pending_components, set()
        for cid in batch:
            result.start_component(graph.cls_names[cid])
        result.run()
    result.current = 3
    for node in facts['components']:
        if node['kind']=='activity':
            result.start_component(descriptor(node['name']))
    result.run()


def classify_sites(sites, graph, reached, absent):
    output = []
    owner_anchors = {}
    for mid, stage in enumerate(reached.stage):
        owner = graph.cls_names[graph.m_cls[mid]]
        if stage != reach.UNREACHED and (owner not in owner_anchors or stage < owner_anchors[owner][0]):
            owner_anchors[owner] = (stage, mid)
    for site in sites:
        missing = site.get('missing', sorted(descriptors(site['reference']) & absent))
        if not missing:
            continue
        mid = None
        if site['caller']:
            owner, signature = site['caller'].split('->', 1)
            mid = graph.meth_ids.get((graph.cls_ids.get(owner), graph.sig_ids.get(signature)))
        stage = reached.stage[mid] if mid is not None else reached.instantiated.get(graph.cls_ids.get(site['owner']), reach.UNREACHED)
        if mid is None and site['owner'] in owner_anchors:
            anchored_stage, anchor = owner_anchors[site['owner']]
            stage = min(stage, anchored_stage)
            mid = anchor
        tier = 'startup-chain-candidate' if stage in {0, 1} else 'startup-or-later-transition-candidate' if stage==2 else 'later-component-candidate' if stage==3 else 'unanchored-not-proved-later'
        output.append(dict(site, missing=missing, stage=int(stage), tier=tier, anchor_method=graph.name(mid) if mid is not None and stage != reach.UNREACHED else None, path=reached.explain(mid) if mid is not None and stage != reach.UNREACHED else [],
            certainty='conditional static exposure; lazy verifier resolution, branches, reflection and callbacks are not execution proof'))
    return output


def inspect(entry, tools, runtime, auxiliary):
    apk = Path(entry['path'])
    payload = apk.read_bytes()
    if sha(payload) != entry['apk_sha256']:
        raise ValueError('APK SHA drift: '+entry['key'])
    xml = subprocess.check_output([tools['aapt2'], 'dump', 'xmltree', str(apk), '--file', 'AndroidManifest.xml'], text=True)
    facts = manifest(xml, entry.get('launch_activity'))
    if facts['package'] != entry['package']:
        raise ValueError('Package drift: '+entry['key'])
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix='libart-app-') as temporary:
        metadata = []
        inventory = []
        all_types = set()
        for member in sorted(archive.namelist()):
            if not re.fullmatch(r'classes\d*\.dex', member):
                continue
            data = archive.read(member)
            dex = dex_metadata(data)
            metadata.append((member, dex))
            inventory.append(dict(member=member, sha256=sha(data), classes=len(dex['classes'])))
            all_types.update(owner for value in dex['types'] for owner in descriptors(value))
        graph, sites = prepare_graph(metadata)
        app_classes = {graph.cls_names[cid] for cid in graph.defined}
        absent = all_types-set(runtime)-app_classes
        for member, _ in metadata:
            path = Path(temporary)/member
            path.write_bytes(archive.read(member))
            with tempfile.TemporaryFile() as errors:
                process = subprocess.Popen([tools['dexdump'], '-d', str(path)], stdout=subprocess.PIPE, stderr=errors, text=True, errors='replace')
                parse_code(process.stdout, member, graph, sites, absent, [node['name'] for node in facts['components']])
                process.stdout.close()
                if process.wait():
                    raise ValueError('DEX disassembly failed: '+entry['key'])
        reached = stages(graph, facts, runtime)
        witnesses = classify_sites(sites, graph, reached, absent)
        referenced = {owner for site in witnesses for owner in site['missing']}
        return dict(key=entry['key'], package=entry['package'], apk_sha256=entry['apk_sha256'], cohort=entry['cohort'], dex=inventory,
            manifest=facts, manifest_sha256=sha(xml.encode()), defined_classes=len(app_classes), methods=len(graph.m_cls),
            absent_boot_and_app=sorted(absent), runtime_jar_only=sorted(absent & set(auxiliary)),
            absent_from_all_indexed_loaders=sorted(absent-set(auxiliary)), type_pool_only_without_site=sorted(absent-referenced),
            sites=witnesses, site_tiers=dict(Counter(site['tier'] for site in witnesses)),
            reachability=dict(mode='existing staged RTA; explicit process and launcher roots, later named/declared Activity components', deferred_user_callbacks=reached.deferred_user_input,
                budget_seconds=reached.budget_seconds, budget_truncated=reached.budget_truncated,
                limitation='Not-reached is unknown, not later-only. Runtime graph/callback lookup, computed reflection, layout inflation and dynamic modules remain incomplete; stage2 routing is conditional, not first-frame timing.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspaces', type=Path, default=Path(os.environ.get('WORKSPACES', ROOT.parent)))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--keys', nargs='*')
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    runtime, auxiliary, evidence = identity(args.workspaces)
    entries = theme_collect.inputs(args.workspaces)
    if args.keys:
        entries = [entry for entry in entries if entry['key'] in args.keys]
    tools = {name:str(Path.home()/'Library/Android/sdk/build-tools/37.0.0'/name) for name in ['aapt2', 'dexdump']}
    apps = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(inspect, entry, tools, runtime, auxiliary) for entry in entries]
        for future in as_completed(futures):
            app = future.result()
            apps.append(app)
            print('SCANNED', len(apps), app['key'], len(app['absent_boot_and_app']), app['site_tiers'], flush=True)
    output = dict(schema='b10-libart-class-facts-v1', identity=evidence, apps=sorted(apps,key=lambda app:app['key']), boot_classes=len(runtime), auxiliary_classes=len(auxiliary),
        tools={name:sha(Path(path).read_bytes()) for name, path in tools.items()},
        scanner_dependencies={str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in [Path(__file__), Path(reach.__file__), THEME/'collect.py', THEME/'rules.py']})
    args.output.write_text(json.dumps(output, sort_keys=True)+'\n')


if __name__ == '__main__':
    main()
