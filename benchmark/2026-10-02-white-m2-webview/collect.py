#!/usr/bin/env python3
import base64
import datetime
import gzip
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get('WORKSPACES', REPO.parent))
MASTER = WS / 'westlake-harness'
BASE = WS / 'westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3'
KEYS = ['cv2-ca-vaults-randomlydie', 'cv2-com-degeder-yam',
        'cv2-com-paultirk-yatoo', 'cv2-dev-obfusk-jiten-webview',
        'cv2-timur-webrtc-check', 'cv2-com-caniwebview-android']
LINE = re.compile(r'^(\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+([^:]+):\s?(.*)$')
SELECT = re.compile(r'J8-WEBVIEW|J10[e-g]-WEB|B8-WEBVIEW|HTML_COMPAT|html_compat|WebView|Capacitor|CookieManager|ServiceWorker|VRT.*(?:TextView|Button)|main_threw|FATAL EXCEPTION|System.exit')


def portable(value):
    text = str(value)
    for root, token in [(REPO, '$REPO'), (WS, '$WORKSPACES')]:
        prefix = str(root)
        if text == prefix or text.startswith(prefix + '/'):
            return token + text[len(prefix):]
    return text


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def command(name, argv):
    result = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (HERE / 'evidence' / name).write_text(result.stdout.replace(str(WS) + '/', '$WORKSPACES/'))
    if result.returncode:
        raise RuntimeError((argv, result.returncode))


def dex_scan(jar, targets=None):
    tool = Path.home() / 'Library/Android/sdk/build-tools/37.0.0/dexdump'
    lines = []
    dex_hashes = {}
    with zipfile.ZipFile(jar) as archive, tempfile.TemporaryDirectory() as scratch:
        for member in archive.namelist():
            if not re.fullmatch(r'classes\d*\.dex', member):
                continue
            data = archive.read(member)
            dex_hashes[member] = hashlib.sha256(data).hexdigest()
            path = Path(scratch) / member
            path.write_bytes(data)
            process = subprocess.Popen([str(tool), '-d', str(path)], text=True,
                stdout=subprocess.PIPE, errors='replace')
            owner = method = ''
            for number, text in enumerate(process.stdout, 1):
                if "Class descriptor  : '" in text:
                    owner, method = text.split("'")[1], ''
                elif re.match(r'    #\d+\s+: \(in ', text):
                    method = ''
                elif text.startswith('      name'):
                    method = text.split("'")[1]
                selected = (owner in targets and method in targets[owner]) if targets else bool(re.search(
                    r'android/webkit/.*(?:loadUrl|loadData|evaluateJavascript|addJavascriptInterface|setJavaScriptEnabled|setWebViewClient|setWebChromeClient)|const-string.*(?:https?://|file:///|caniwebview.local)', text))
                if selected:
                    lines.append({'dex': member, 'owner': owner, 'method': method,
                        'line': number, 'text': text.rstrip()})
            assert process.wait() == 0
    return {'file': portable(jar), 'sha256': sha(jar), 'dex_hashes': dex_hashes,
        'tool_sha256': sha(tool), 'lines': lines}


def run_key(key, signed, apk):
    run = Path(signed['t20'].replace('$WORKSPACES', str(WS))).parent
    record = json.loads((run / 'record.json').read_text())
    parsed = []
    pids = set()
    bind = []
    for number, text in enumerate((run / 'hilog.txt').read_text(errors='replace').splitlines(), 1):
        match = LINE.match(text)
        if not match:
            continue
        time_text, pid, tid, level, tag, message = match.groups()
        epoch = datetime.datetime.strptime('2026-' + time_text, '%Y-%m-%d %H:%M:%S.%f').replace(
            tzinfo=datetime.timezone(datetime.timedelta(hours=8))).timestamp()
        parsed.append((number, text, int(pid), int(tid), epoch))
        if 'nativeOnScheduleLaunchApplication ENTRY bundle=' + record['package'] + ' ' in text:
            pids.add(int(pid))
            bind.append(epoch)
    assert bind, key
    t20 = next(float(item['remote_stat'].split()[1]) for item in record['screenshots']
        if Path(item['path']).name == 't20.jpeg' and item.get('remote_stat'))
    cutoff = min(t20, max(item[4] for item in parsed))
    events = [{'line': number, 'pid': pid, 'tid': tid, 'text': text}
        for number, text, pid, tid, epoch in parsed
        if pid in pids and min(bind) - 3 <= epoch <= cutoff and SELECT.search(text)]
    maps = []
    inputs = [run / 'record.json', run / 'hilog.txt', run / 't20.jpeg']
    for path in sorted(run.glob('maps-*.txt')):
        if not any(path.stem.endswith('-' + str(pid)) for pid in pids):
            continue
        inputs.append(path)
        maps += [{'file': portable(path), 'line': number, 'text': text}
            for number, text in enumerate(path.read_text(errors='replace').splitlines(), 1)
            if re.search(r'/[^/ ]*(?:webview|chromium|html_compat)[^/ ]*\.so', text, re.I)]
    pins = []
    for name in ['runtime-fingerprint.txt', 'boot-image-fingerprint.txt']:
        path = run.parent / name
        inputs.append(path)
        pins += [{'file': portable(path), 'line': number, 'text': text}
            for number, text in enumerate(path.read_text().splitlines(), 1)
            if any(text.endswith('/' + part) for part in ['oh-adapter-runtime.jar', 'framework.jar', 'liboh_android_runtime.so'])]
    path = Path(apk['apk'].replace('$WORKSPACES', str(WS)))
    assert sha(path) == apk['apk_sha256']
    assert sha(run / 't20.jpeg') == signed['t20_sha256']
    calls = dex_scan(path)
    with zipfile.ZipFile(path) as archive:
        assets = [name for name in archive.namelist() if name.startswith('assets/')
            and re.search(r'\.(html?|js|css)$', name)]
        native = [name for name in archive.namelist() if name.startswith('lib/') and name.endswith('.so')]
    save('evidence/' + key + '-calls.json', calls)
    (HERE / 'evidence' / (key + '-hilog.txt')).write_text(''.join(
        str(item['line']) + ': ' + item['text'] + '\n' for item in events))
    return {'key': key, 'signed': signed, 'run': portable(run), 'app_pids': sorted(pids),
        'coverage': {'hilog_end_to_t20_gap_seconds': t20 - cutoff},
        'events': events, 'maps': maps, 'pins': pins,
        'inputs': [{'path': portable(path), 'sha256': sha(path)} for path in inputs],
        'apk': apk, 'native_entries': native, 'html_js_css_assets': assets,
        'prediction': {'first_fatal_moves': 0, 'renderer_content_wall_moves':
            'conditional' if key != KEYS[-1] else 'negative-control',
            'next_wall': 'unknown: provider closure, JS bridge, networking or WebRTC permissions',
            'html_compat_restoration_moves': 0}}


def main():
    (HERE / 'evidence').mkdir(exist_ok=True)
    reference_path = MASTER / 'benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference/sources.json'
    reference = json.loads(reference_path.read_text())
    manifest_path = MASTER / 'benchmark/2026-10-01-corpus-v2/apk-scan-v1/input-manifest.json.gz.b64'
    apks = {row['key']: row for row in json.loads(gzip.decompress(base64.b64decode(manifest_path.read_bytes())))['apps']}
    rows = [run_key(key, reference['keys'][key], apks[key]) for key in KEYS]
    runtime_jar = BASE / 'bundle/framework/oh-adapter-runtime.jar'
    framework = BASE / 'bundle/native/payload/android/framework/framework.jar'
    native = BASE / 'bundle/native/payload/android/lib64/liboh_android_runtime.so'
    command('artifact-identity.txt', ['python3', str(MASTER / 'scripts/lab/artifact_identity.py'),
        str(runtime_jar), str(framework), str(native), '--expected', str(BASE / 'bundle/expected-per-board.json')])
    command('whois-html.txt', ['python3', str(MASTER / 'scripts/lab/deployed_whois.py'),
        'libwestlake_html_compat.so', '--generation', str(BASE)])
    command('native-publication.txt', ['llvm-objdump', '-d', '--demangle',
        '--start-address=0x1f65f8', '--stop-address=0x1f7014', str(native)])
    targets = {'Ladapter/activity/WebViewProviderFix;': ['install'],
        'Ladapter/activity/WebViewProviderFix$ZeroHandler;': ['invoke'],
        'Ladapter/activity/J10eWebView;': ['install'],
        'Ladapter/activity/J10eWebView$ProviderInstance;': ['invoke'],
        'Ladapter/activity/B7BindFixes;': ['loadWestlakeNativeLibs'],
        'Ladapter/core/WestlakeWebViewInstall;': ['install', 'isAvailable'],
        'Ladapter/core/WebViewPackageFallback;': ['isAvailable'],
        'Ladapter/compat/HtmlCompatFallback;': ['install']}
    save('evidence/runtime-methods.json', dex_scan(runtime_jar, targets))
    save('evidence/framework-methods.json', dex_scan(framework, {
        'Landroid/webkit/WebViewFactory;': ['getProvider'],
        'Landroid/webkit/WebView;': ['loadUrl', 'evaluateJavascript']}))
    source_inputs = [
        (MASTER / 'benchmark/2026-10-01-j8-t7e-reproducible/src/WebViewProviderFix.java', [(25, 100)]),
        (MASTER / 'benchmark/2026-10-01-j10-freeze-draft/sources/J10eWebView.java', [(74, 198)]),
        (WS / 'westlake-harness-bms-deploy/benchmark/2026-09-30-n3b-webview/src/webview_publication.cpp', [(90, 245), (294, 321)]),
        (WS / 'vm-copies/westlake-current/framework/activity/jni/activity_task_manager_adapter.cpp', [(419, 570), (740, 820)]),
        (WS / 'westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/java/android/webkit/WebViewFactory.java', [(321, 360)])]
    sources = []
    for path, ranges in source_inputs:
        texts = path.read_text(errors='replace').splitlines()
        sources.append({'file': portable(path), 'sha256': sha(path),
            'qualification': 'reference source; deployed DEX/native bytes remain authoritative',
            'lines': [{'line': number, 'text': texts[number - 1]}
                for first, last in ranges for number in range(first, min(last, len(texts)) + 1)]})
    save('evidence/source-excerpts.json', sources)
    board_path = MASTER / '.octos/boards/app-lighting.md'
    board_lines = board_path.read_text(errors='replace').splitlines()
    pause = [{'file': portable(board_path), 'line': number,
        'raw_line_sha256': hashlib.sha256(board_lines[number - 1].encode()).hexdigest(),
        'text': board_lines[number - 1].replace(str(WS) + '/', '$WORKSPACES/')}
        for number in [2011, 2765, 2770, 2784]]
    save('evidence/html-pause.json', pause)
    package_path = BASE / 'bundle/native/package.json'
    package = json.loads(package_path.read_text())
    result = {'schema': 1, 'execution_enabled': False, 'rows': rows,
        'reference': {'path': portable(reference_path), 'sha256': sha(reference_path),
            'outer_signoff_sha256': reference['signoff_sha256']},
        'components': {'effective_runtime': portable(runtime_jar), 'effective_runtime_sha256': sha(runtime_jar),
            'stale_native_payload_runtime_sha256': sha(BASE / 'bundle/native/payload/android/framework/oh-adapter-runtime.jar'),
            'framework_sha256': sha(framework), 'native_runtime_sha256': sha(native),
            'native_package_sha256': sha(package_path), 'webview_related_package_entries':
                [row for row in package['files'] if re.search(r'webview|chromium|html_compat|jnigraphics', json.dumps(row), re.I)]},
        'verdict': {'same_zero_provider': 6, 'white_or_black': 5, 'lit_native_chrome_control': 1,
            'first_fatal_moves': 0, 'conditional_renderer_content_wall_upper_bound': 5,
            'html_compat_restoration_moves': 0, 'measured_new_lit': 0}}
    save('results.json', result)


if __name__ == '__main__':
    main()
