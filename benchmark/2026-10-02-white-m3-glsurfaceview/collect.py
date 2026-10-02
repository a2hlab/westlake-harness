#!/usr/bin/env python3
import datetime
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
WS = Path(os.environ.get('WORKSPACES', str(REPO.parent)))
MASTER = WS / 'westlake-harness'
BASE = WS / 'westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3'
REFERENCE = MASTER / 'benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference/sources.json'
WHITE = ['cv2-com-bytehamster-flowitgame', 'fd-app', 'fd-shatteredpixeldungeon']
CONTROLS = ['cv2-de-markusfisch-android-shadereditor', 'noice']
LINE = re.compile(r'^(\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+([^:]+):\s?(.*)$')
SELECT = re.compile(r'createSession: success|published process window target|oh_wm_set_last_session_local|WMClient.getOhNativeWindow|unknown sessionId|getOhNativeWindow\(sessionId|BBQ\.(create|update:|getSurface:)|S_nativeGetFromBlast|oh_rs_get_child_surface_window|SC.create.*SurfaceView|OH_NWFromSurface|OH_EglHijack|GLSurfaceView:|EGLImpl::_eglCreateWindowSurface|Surface::nativeGetFromBlast|\[WL-OPENGL\]')


def portable(value):
    text = str(value)
    for root, token in [(REPO, '$REPO'), (WS, '$WORKSPACES')]:
        prefix = str(root)
        if text == prefix or text.startswith(prefix + '/'):
            return token + text[len(prefix):]
    return text


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp(text):
    return datetime.datetime.strptime('2026-' + text, '%Y-%m-%d %H:%M:%S.%f').replace(
        tzinfo=datetime.timezone(datetime.timedelta(hours=8))).timestamp()


def summarize(events):
    sessions = []
    children = []
    errors = []
    for event in events:
        text = event['text']
        match = re.search(r'createSession: success, sessionId=(\d+)', text)
        if match:
            sessions.append(int(match[1]))
        match = re.search(r'oh_rs_get_child_surface_window: session=(\d+) .*anw=([0-9A-Fa-f]+)', text)
        if match:
            children.append(dict(event, session=int(match[1]), pointer=match[2]))
        if 'GLSurfaceView: java.lang.IllegalArgumentException: Make sure' in text:
            errors.append(event)
    return {'sessions': sessions, 'children': children, 'gl_errors': errors}


def run_key(key, reference):
    signed = reference[key]
    run = Path(signed['t20'].replace('$WORKSPACES', str(WS))).parent
    record = json.loads((run / 'record.json').read_text())
    raw = (run / 'hilog.txt').read_text(errors='replace').splitlines()
    parsed = []
    pids = set()
    bind = []
    for number, text in enumerate(raw, 1):
        match = LINE.match(text)
        if not match:
            continue
        time_text, pid, tid, level, tag, message = match.groups()
        epoch = timestamp(time_text)
        parsed.append((number, text, int(pid), int(tid), epoch, tag))
        if 'nativeOnScheduleLaunchApplication ENTRY bundle=' + record['package'] + ' ' in text:
            pids.add(int(pid))
            bind.append(epoch)
    assert bind and pids, key
    t20 = next(float(item['remote_stat'].split()[1]) for item in record['screenshots']
               if Path(item['path']).name == 't20.jpeg' and item.get('remote_stat'))
    end = max(item[4] for item in parsed)
    cutoff = min(end, t20)
    start = min(bind) - 3
    events = []
    for number, text, pid, tid, epoch, tag in parsed:
        if pid in pids and start <= epoch <= cutoff and SELECT.search(text) and 'AppSpawnXJava' not in tag:
            events.append({'line': number, 'pid': pid, 'tid': tid, 'text': text})
    summary = summarize(events)
    gl_tids = sorted({item['tid'] for item in summary['gl_errors']})
    summary['gl_tids'] = gl_tids
    summary['gl_thread_from_surface_calls'] = [item for item in events
        if item['tid'] in gl_tids and 'OH_NWFromSurface: [STAGE0] ENTER' in item['text']]
    summary['gl_thread_egl_pointer_calls'] = [item for item in events
        if item['tid'] in gl_tids and 'eglCreateWindowSurface: dpy=' in item['text']]
    summary['last_session_read_instrumented'] = False
    summary['egl_jni_input_pointer_observed'] = False
    maps = []
    inputs = [run / 'record.json', run / 'hilog.txt', run / 't20.jpeg']
    pins = []
    for name in ['runtime-fingerprint.txt', 'boot-image-fingerprint.txt']:
        path = run.parent / name
        inputs.append(path)
        for number, text in enumerate(path.read_text().splitlines(), 1):
            if any(text.endswith('/' + library) for library in
                   ['liboh_android_runtime.so', 'liboh_adapter_bridge.so', 'libandroid.so', 'framework.jar']):
                pins.append({'file': portable(path), 'line': number, 'text': text})
    for pid in sorted(pids):
        path = run / ('maps-t5-' + str(pid) + '.txt')
        if not path.exists():
            continue
        inputs.append(path)
        for number, text in enumerate(path.read_text().splitlines(), 1):
            if re.search(r'liboh_android_runtime\.so|liboh_adapter_bridge\.so|/libandroid\.so', text):
                maps.append({'file': portable(path), 'line': number, 'text': text})
    excerpt = '\n'.join(str(item['line']) + ': ' + item['text'] for item in events) + '\n'
    (HERE / 'evidence' / (key + '-hilog.txt')).write_text(excerpt)
    return {'key': key, 'signed': signed, 'run': portable(run), 'package': record['package'],
            'app_pids': sorted(pids), 'coverage': {'start_epoch': start, 'cutoff_epoch': cutoff,
                't20_epoch': t20, 'hilog_end_epoch': end, 'gap_seconds': t20 - cutoff},
            'inputs': [{'path': portable(path), 'sha256': digest(path)} for path in inputs],
            'events': events, 'summary': summary, 'maps': maps, 'fingerprint_pins': pins,
            'prediction': {'m1_exception_moves': 0,
                'm3_exception_move': 'conditional' if key in WHITE else 'control',
                'next_wall': 'unknown; no GL renderer entry observed after the blocked surface',
                't20_after_repair': 'unknown; existing white signoff is unchanged'}}


def command(name, args):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.replace(str(WS) + '/', '$WORKSPACES/')
    (HERE / 'evidence' / name).write_text(output)
    assert result.returncode == 0, (args, result.returncode)


def framework_methods():
    jar = BASE / 'bundle/native/payload/android/framework/framework.jar'
    tool = Path.home() / 'Library/Android/sdk/build-tools/37.0.0/dexdump'
    blocks = []
    dex_hashes = {}
    targets = {'Lcom/google/android/gles_jni/EGLImpl;': 'eglCreateWindowSurface',
        'Landroid/opengl/GLSurfaceView$DefaultWindowSurfaceFactory;': 'createWindowSurface',
        'Landroid/view/SurfaceView$1;': 'getSurface', 'Landroid/view/SurfaceView;': '<init>'}
    with zipfile.ZipFile(jar) as archive, tempfile.TemporaryDirectory() as scratch:
        for member in archive.namelist():
            if not re.fullmatch(r'classes\d*\.dex', member):
                continue
            data = archive.read(member)
            if not any(owner[1:-1].encode() in data for owner in targets):
                continue
            dex_hashes[member] = hashlib.sha256(data).hexdigest()
            path = Path(scratch) / member
            path.write_bytes(data)
            process = subprocess.Popen([str(tool), '-d', str(path)], text=True,
                stdout=subprocess.PIPE, errors='replace')
            owner = method = ''
            for number, text in enumerate(process.stdout, 1):
                if "Class descriptor  : '" in text:
                    owner = text.split("'")[1]
                    method = ''
                elif re.match(r'    #\d+\s+: \(in ', text):
                    method = ''
                elif text.startswith('      name'):
                    method = text.split("'")[1]
                if owner in targets and method == targets[owner]:
                    if owner == 'Landroid/view/SurfaceView;' and not any(token in text for token in
                            ["name          :", 'new-instance', 'Surface;.<init>', 'mSurface:Landroid/view/Surface;', 'mSurfaceHolder']):
                        continue
                    blocks.append({'dex': member, 'owner': owner, 'line': number, 'text': text.rstrip()})
            assert process.wait() == 0
    result = {'jar': portable(jar), 'jar_sha256': digest(jar), 'dex_hashes': dex_hashes,
        'tool_sha256': digest(tool), 'lines': blocks}
    (HERE / 'evidence/framework-methods.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    (HERE / 'evidence').mkdir(exist_ok=True)
    reference = json.loads(REFERENCE.read_text())['keys']
    rows = [run_key(key, reference) for key in WHITE + CONTROLS]
    libraries = BASE / 'bundle/native/payload/android/lib64'
    runtime = libraries / 'liboh_android_runtime.so'
    bridge = libraries / 'liboh_adapter_bridge.so'
    command('runtime-eglimpl-disassembly.txt', ['llvm-objdump', '-d', '--demangle',
        '--start-address=0x1dd8bc', '--stop-address=0x1ddc30', str(runtime)])
    command('runtime-from-surface-disassembly.txt', ['llvm-objdump', '-d', '--demangle',
        '--start-address=0x1972a8', '--stop-address=0x197524', str(runtime)])
    command('root-from-surface-entry.txt', ['llvm-objdump', '-d',
        '--start-address=0x407fc', '--stop-address=0x40854', str(libraries / 'libandroid.so')])
    command('bridge-child-disassembly.txt', ['llvm-objdump', '-d', '--demangle',
        '--start-address=0xe07e8', '--stop-address=0xe0f58', str(bridge)])
    for library in ['liboh_android_runtime.so', 'liboh_adapter_bridge.so']:
        command('whois-' + library + '.txt', ['python3', str(MASTER / 'scripts/lab/deployed_whois.py'),
            library, '--generation', str(BASE)])
    framework = framework_methods()
    source_specs = [
        (MASTER / 'benchmark/2026-10-01-n5-native/native-checks/egl.cpp', [(29, 60), (315, 340)]),
        (WS / 'westlake-harness-bms-deploy/bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp', [(272, 288), (1242, 1286)]),
        (WS / 'westlake-harness-bms-deploy/bms/src/adapter/framework/window/jni/oh_window_manager_client.cpp', [(96, 127), (1216, 1244), (1283, 1296)]),
        (WS / 'westlake-inputs/aosp-14.0.0_r1-src/frameworks/base/core/jni/com_google_android_gles_jni_EGLImpl.cpp', [(257, 282)])]
    sources = []
    for path, ranges in source_specs:
        lines = path.read_text().splitlines()
        text = '\n'.join(str(number) + ': ' + lines[number - 1]
            for first, last in ranges for number in range(first, last + 1)) + '\n'
        target = HERE / 'evidence' / (path.name + '-source.txt')
        target.write_text(text)
        sources.append({'path': portable(path), 'sha256': digest(path), 'ranges': ranges,
            'excerpt': portable(target), 'qualification': 'reference only; deployed behavior is pinned by ELF disassembly and runtime logs'})
    output = {'schema': 1, 'reference': {'path': portable(REFERENCE), 'sha256': digest(REFERENCE)},
        'framework': {key: value for key, value in framework.items() if key != 'lines'},
        'libraries': [{'path': portable(path), 'sha256': digest(path)} for path in
            [runtime, bridge, libraries / 'libandroid.so']], 'sources': sources, 'rows': rows,
        'conclusion': {'same_as_m1_last_session_overwrite': False,
            'm1_expected_gl_exception_moves': 0, 'm3_conditional_gl_exception_moves': 3,
            'measured_unlocks': 0, 'candidate_built': False,
            'root_status': 'EGL JNI conversion/owner lookup; RTLD_DEFAULT cache miss is the leading inference, not a captured return value'}}
    (HERE / 'results.json').write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({row['key']: {'sessions': row['summary']['sessions'],
        'children': [item['pointer'] for item in row['summary']['children']],
        'gl_errors': len(row['summary']['gl_errors']), 'gl_tid': row['summary']['gl_tids'],
        'gap_seconds': row['coverage']['gap_seconds']} for row in rows}, indent=2))


if __name__ == '__main__':
    main()
