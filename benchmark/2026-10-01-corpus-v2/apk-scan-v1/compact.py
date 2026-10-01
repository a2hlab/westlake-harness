"""Project complete raw scans into counted, coordinate-preserving replay evidence."""

import argparse
import collections
import hashlib
import json
from pathlib import Path

import report
import scan
import scan_risks_v3


def project(app):
    if app['status'] != 'scanned':
        return app
    reached = set(app['startup']['reached'])
    app['raw_counts'] = {name: len(app[name]) for name in ['services', 'jni_calls', 'risks', 'framework_calls', 'app_native_candidates', 'dex', 'libraries']}
    app['raw_counts']['startup_calls'] = len(app['startup']['calls'])
    app['raw_counts']['startup_reached_methods'] = len(reached)
    startup_methods = collections.defaultdict(list)
    for call in app['startup']['calls']:
        startup_methods[(call['method'], call['dex'])].append((call['offset'], call['line'], call['instruction']))
    for (method, dex), instructions in startup_methods.items():
        for requirement in scan_risks_v3.inspect_method(method, dex, instructions):
            requirement['family'] = requirement['kind']
            requirement['projection'] = 'Exact-target startup invoke instructions only; constants/branches not retained, argument unknown'
            app['risks'].append(requirement)
    for name, field in [('services', 'service'), ('jni_calls', 'id'), ('risks', 'family'), ('framework_calls', 'owner')]:
        groups = collections.defaultdict(list)
        for row in app[name]:
            startup = report.method_key(row['method']) in reached
            group = row[field]
            if name == 'framework_calls':
                group = next((prefix for prefix in ['Landroidx/compose/', 'Landroid/webkit/', 'Landroid/opengl/', 'Lio/flutter/', 'Lcom/unity3d/'] if group.startswith(prefix)), group)
            groups[(group, startup)].append(row)
        app[name] = [{**rows[0], 'occurrence_count':len(rows), 'examples':rows[:3]} for rows in groups.values()]
    wanted = {symbol['name'] for library in app['libraries'] for symbol in library['imports']}
    for library in app['libraries']:
        library['all_export_count'] = len(library['exports'])
        library['exports'] = [symbol for symbol in library['exports'] if symbol in wanted]
        library['export_projection'] = 'All import-resolving app exports retained; JNI exports already attributed in app_native_candidates'
    app['startup']['calls'] = [call for call in app['startup']['calls'] if call['name'] in {'startActivity', 'startActivityForResult'}]
    witnessed = {report.method_key(row['method']) for name in ['services', 'jni_calls', 'risks', 'framework_calls'] for row in app[name]}
    app['startup']['reached'] = sorted(reached & witnessed)
    app['evidence_projection'] = 'Complete scan counted by family/API and startup membership; up to three original DEX coordinates per group. Reachability retains witnessed methods, not every intermediate edge.'
    return app


def stream_project(path):
    decoder = json.JSONDecoder()
    with path.open() as source:
        buffer = source.read(16*1024*1024)
        prefix = '{"apps": ['
        if not buffer.startswith(prefix):
            raise ValueError('expected sorted scan document with apps first')
        buffer = buffer[len(prefix):]
        apps = []
        while True:
            buffer = buffer.lstrip()
            if buffer.startswith(','):
                buffer = buffer[1:].lstrip()
            if buffer.startswith(']'):
                suffix = buffer[1:]+source.read()
                suffix = suffix.lstrip()
                if not suffix.startswith(','):
                    raise ValueError('missing scan metadata')
                metadata = json.loads('{'+suffix[1:])
                metadata['apps'] = apps
                return metadata
            try:
                app, offset = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                chunk = source.read(16*1024*1024)
                if not chunk:
                    raise
                buffer += chunk
                continue
            apps.append(project(app))
            buffer = buffer[offset:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--facts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    document = stream_project(args.facts)
    with args.facts.open('rb') as source:
        raw_sha = hashlib.file_digest(source, 'sha256').hexdigest()
    document['raw_scan_document'] = dict(sha256=raw_sha, bytes=args.facts.stat().st_size,
                                         storage='Private scratch; reproducible by scan.py against pinned inputs, not committed')
    relative = 'benchmark/2026-10-01-corpus-v2/apk-scan-v1/compact.py'
    document['scanner_dependencies'][relative] = report.digest(Path(__file__).read_bytes())
    document['scanner_dependencies']['benchmark/2026-09-29-static-wall-prediction/scan_risks_v3.py'] = report.digest((scan.B10/'scan_risks_v3.py').read_bytes())
    for app in document['apps']:
        if app['status'] == 'scanned':
            app['scanner_dependencies'] = document['scanner_dependencies']
    args.output.write_text(json.dumps(document, sort_keys=True)+'\n')
    print('projected', document['counts'], args.output.stat().st_size)


if __name__ == '__main__':
    main()
