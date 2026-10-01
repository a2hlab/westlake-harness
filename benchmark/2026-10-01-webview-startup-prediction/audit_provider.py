"""Inspect exact candidate bytecode and older PID-bound fatal calibrations offline."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

import scan_webview as scan

ROOT = scan.ROOT
sys.path.insert(0, str(ROOT/'scripts/lab'))
import first_fatal


def selected_dex(path, owners, tool):
    output = {}
    classes = {}
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix='wv-provider-') as temporary:
        for member in archive.namelist():
            if not re.fullmatch(r'classes\d*\.dex', member):
                continue
            dex = Path(temporary)/member
            dex.write_bytes(archive.read(member))
            selected = []
            current = None
            with tempfile.TemporaryFile() as errors:
                process = subprocess.Popen([tool, '-d', str(dex)], stdout=subprocess.PIPE, stderr=errors, text=True, errors='replace')
                for number, line in enumerate(process.stdout, 1):
                    if "Class descriptor  : '" in line:
                        current = line.split("'")[1]
                    if current in owners:
                        selected.append(line)
                process.stdout.close()
                if process.wait():
                    raise ValueError('Runtime DEX parse failed')
            parsed_classes, methods = scan.parse_dex(selected, member)
            classes.update(parsed_classes)
            for identifier, method in methods.items():
                output[identifier] = dict(dex=member, coordinate_scope='selected-class dump lines, not whole-DEX lines',
                    descriptor=method['descriptor'], instructions=method['body'])
    return dict(classes=classes, methods=output)


def calibrations(workspaces):
    root = workspaces/'westlake-harness-t4/benchmark/2026-10-01-cv2-hilog'
    output = {}
    for path in sorted(root.glob('*/*/*/*/hilog.txt')):
        record = json.loads((path.parent/'record.json').read_text())
        if record['package'] not in scan.PACKAGES:
            continue
        record, events, pids, reports, disappeared, binding = first_fatal.load_run(path.parent)
        result = first_fatal.analyze(events, pids, reports, disappeared)
        relevant = [event for event in events if event['pid'] in pids and
                    re.match(r'^(?:\[stderr\]\s*)?(?:at |Caused by:)', event['message'].strip())]
        output[record['key']] = dict(source=str(path.relative_to(workspaces)), binding=binding,
            first_fatal=result, app_frames=[event for event in relevant if record['package'] in event['message']],
            provider_frames=[event for event in relevant if any(name in event['message'] for name in ['WebViewFactory.getProvider', 'WebView.<init>', 'enableSlowWholeDocumentDraw'])],
            limits='Later U7 diagnostic calibration, not original cv2 signed observation and not a U8 result')
    if len(output) != 7:
        raise ValueError('Incomplete diagnostic calibrations')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workspaces', type=Path, default=Path(os.environ.get('WORKSPACES', ROOT.parent)))
    args = parser.parse_args()
    candidate = args.workspaces/'westlake-generation-u8-j9-t7e'
    bundle = json.loads((candidate/'bundle.json').read_text())
    runtime = candidate/bundle['runtime_jar']['source']
    if scan.b10.digest(runtime.read_bytes()) != bundle['runtime_jar']['sha256']:
        raise ValueError('Candidate runtime SHA mismatch')
    framework = candidate/'native/payload/android/framework/framework.jar'
    expected = ROOT/'benchmark/2026-10-01-u7-prospective/v1/expected-run.json'
    tool = args.workspaces/'westlake-harness/scripts/lab/artifact_identity.py'
    identity = subprocess.run([sys.executable, str(tool), '--expected', str(expected), str(framework)], capture_output=True, text=True)
    if identity.returncode:
        raise ValueError('Unchanged framework identity rejected: '+identity.stdout)
    dexdump = str(Path.home()/'Library/Android/sdk/build-tools/37.0.0/dexdump')
    runtime_dex = selected_dex(runtime, {'Ladapter/activity/WebViewProviderFix;', 'Ladapter/activity/WebViewProviderFix$ZeroHandler;', 'Ladapter/activity/B7BindFixes;'}, dexdump)
    framework_dex = selected_dex(framework, {'Landroid/webkit/WebView;', 'Landroid/webkit/WebViewFactory;', 'Landroid/webkit/WebSettings;', 'Landroid/webkit/WebViewProvider;', 'Landroid/webkit/WebViewFactoryProvider;'}, dexdump)
    source = 'benchmark/2026-10-01-j8-t7e-reproducible/src/WebViewProviderFix.java'
    source_commit = '9c77495c3e00575bccc5bad04cb118ecfcd0fb4d'
    payload = subprocess.check_output(['git', 'show', source_commit+':'+source], cwd=ROOT)
    output = dict(schema='webview-provider-byte-evidence-v1', candidate_runtime=dict(sha256=scan.b10.digest(runtime.read_bytes()),
        expected_sha256=bundle['runtime_jar']['sha256'], board_target=bundle['runtime_jar']['target'],
        bundle_sha256=scan.b10.digest((candidate/'bundle.json').read_bytes()), status='candidate-matches-U8-plan; not already deployed'),
        unchanged_framework=dict(sha256=scan.b10.digest(framework.read_bytes()), artifact_identity_exit=identity.returncode,
            stdout=identity.stdout.replace(str(args.workspaces), '$WORKSPACES'), tool_sha256=scan.b10.digest(tool.read_bytes())),
        runtime=runtime_dex, framework=framework_dex,
        source=dict(path=source, commit=source_commit, sha256=scan.b10.digest(payload),
            lines=[dict(line=number,text=line) for number,line in enumerate(payload.decode().splitlines(),1) if 42 <= number <= 86]),
        calibrations=calibrations(args.workspaces),
        audit_dependencies={str(path.relative_to(ROOT)):scan.b10.digest(path.read_bytes()) for path in [Path(__file__),Path(first_fatal.__file__)]})
    args.output.write_text(json.dumps(output,sort_keys=True,indent=2)+'\n')
    print('candidate',output['candidate_runtime']['sha256'][:12], 'framework DEPLOYED',len(output['calibrations']),'calibrations')


if __name__ == '__main__':
    main()
