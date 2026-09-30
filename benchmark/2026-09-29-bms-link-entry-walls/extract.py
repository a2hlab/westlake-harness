#!/usr/bin/env python3
"""Build results.json and evidence/ excerpts for B7 (#54) from the raw run directories.

Raw runs live in ./runs (gitignored; archived to VM ~/a2hlab/board/b7-54/runs). Every
excerpt line keeps its original line number, and each source file is pinned by SHA-256.
Re-running this script on the same runs reproduces results.json byte for byte.
"""
import hashlib, json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = HERE / 'runs'
EVID = HERE / 'evidence'
SERIAL = '5cd1e3dd00000000000000000923012c'
FINAL = 'b7final3-20260929T123636/' + SERIAL   # unified bms_batch, both fixes live, 16M hilog


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def grab(rel, pattern, pid_of=None, limit=1):
    """First `limit` lines of runs/<rel> matching pattern (optionally only the app child's lines)."""
    path = RUNS / rel
    lines = path.read_text(errors='replace').splitlines()
    rx = re.compile(pattern)
    out = []
    for no, line in enumerate(lines, 1):
        fields = line.split()
        if pid_of and not (len(fields) > 3 and fields[2] == pid_of):
            continue
        if rx.search(line):
            out.append({'line': no, 'text': line[:600]})
            if len(out) >= limit:
                break
    return {'file': 'runs/' + rel, 'sha256': sha(path), 'lines': out}


def child_pid(rel, package):
    text = (RUNS / rel).read_text(errors='replace')
    m = re.search(r'APPSPAWN: \[appspawn_service\.c:\d+\]' + re.escape(package) + r' with pid (\d+) exit', text)
    if m:
        return m.group(1)
    m = re.search(r'^\S+ \S+\s+(\d+)\s+\d+ . C00f00/AppSpawnXJava: \[stderr\] \[B43-BIND\] ensureBindApplication start bundle='
                  + re.escape(package) + r'$', text, re.M)
    return m.group(1) if m else None


def count(rel, pattern):
    return sum(1 for l in (RUNS / rel).read_text(errors='replace').splitlines() if re.search(pattern, l))


APPS = {
    'opencamera': 'net.sourceforge.opencamera', 'fd-android': 'net.thunderbird.android',
    'fd-k9': 'com.fsck.k9', 'fd-libre': 'deckers.thibault.aves.libre', 'fd-saber': 'com.adilhanney.saber',
    'fd-catima': 'me.hackerchick.catima', 'fd-fennec_fdroid': 'org.mozilla.fennec_fdroid'}
REPRO = {  # first reproduction on 5cd (continuous `hilog > file` capture, B7 fixes absent)
    'opencamera': 'repro-20260929T112407-five/opencamera/hilog.txt',
    'fd-android': 'repro-20260929T112311-android/fd-android/hilog.txt',
    'fd-libre': 'repro-20260929T112407-five/fd-libre/hilog.txt',
    'fd-saber': 'repro-20260929T112407-five/fd-saber/hilog.txt',
    'fd-catima': 'repro-20260929T112407-five/fd-catima/hilog.txt',
    'fd-fennec_fdroid': 'repro-20260929T112407-five/fd-fennec_fdroid/hilog.txt'}
FIRST = {
    'opencamera': r'Caused by: java\.lang\.UnsatisfiedLinkError: Unable to create namespace',
    'fd-android': r'J_invokeStaticMain_main_threw: java\.lang\.UnsatisfiedLinkError: No implementation found for long android\.database\.sqlite\.SQLiteConnection\.nativeOpen',
    'fd-k9': r'J_invokeStaticMain_main_threw: java\.lang\.UnsatisfiedLinkError: No implementation found for long android\.database\.sqlite\.SQLiteConnection\.nativeOpen',
    'fd-libre': r'E C00f00/FlutterLoader: java\.util\.concurrent\.ExecutionException: java\.lang\.UnsatisfiedLinkError: path is outside app domain',
    'fd-saber': r'E C00f00/FlutterLoader: java\.util\.concurrent\.ExecutionException: java\.lang\.UnsatisfiedLinkError: path is outside app domain',
    'fd-catima': r'Caused by: java\.lang\.NullPointerException: Attempt to invoke virtual method .boolean android\.os\.UserManager\.isUserUnlockingOrUnlocked',
    'fd-fennec_fdroid': r'Caused by: java\.lang\.NullPointerException: Attempt to invoke virtual method .boolean android\.os\.UserManager\.isUserUnlockingOrUnlocked'}
AFTER_MARKER = {
    'opencamera': r'\[B7\] nativeLibraryDir .* does not exist; using ',
    'fd-catima': r'\[ZZ-USER\] isUserUnlockingOrUnlocked user=\d+ result=true',
    'fd-fennec_fdroid': r'\[ZZ-USER\] isUserUnlockingOrUnlocked user=\d+ result=true'}
NEXT = r'J_invokeStaticMain_main_threw: '
BLOCKED = {
    'fd-android': {
        'class': 'jni-sqlite',
        'blocked_reason': ('liboh_android_runtime.so 9ccf64f8 on 5cd links the weak no-op registrars '
                           '(android_graphics_compat_shim.cpp:66-69: mov w0,wzr; ret) because neither '
                           'real-work compile_oh_android_runtime.sh nor compile_oh_android_runtime_arm64_stage2unity.sh '
                           'lists android_database_*.cpp/sqlite3.c; the real sources exist in bms/ and real-work '
                           '(android_database_SQLiteConnection.cpp:962). Rebuilding the library is not deployable in '
                           'B7: the route-A provider is compiled with -DWLAR_ANDROID_RUNTIME_SHA256_HEX '
                           '(build_route_a_generation_in_container.sh:690) and embeds 9ccf64f8 as text, so a new '
                           'runtime library needs a regenerated provider (route-A provider/sealed manifest are '
                           'forbidden to B7; belongs with the B6 whole-generation rebuild).'),
        'fix_site': 'bms/src/adapter/build/inner/compile_oh_android_runtime*.sh SRCS + route-A generation'},
    'fd-libre': {
        'class': 'flutter-native-load',
        'blocked_reason': ('FlutterJNI.loadLibrary is ReLinker-based (dexdump: "Loading the library normally '
                           'failed: %s" logged through an R8-emptied lambda), so the first System.loadLibrary("flutter") '
                           'failure is never logged; libflutter.so is never mapped (no MUSL-LDSO line). The fallback '
                           'System.load(<dataDir>/app_lib/libflutter.so) is refused by app_native_loader.c '
                           'path_is_in_app_domain, which compares only app_search_paths (domain->app_paths, line 337) '
                           'while AOSP also permits the class-loader permitted path (dataDir); Westlake v3-hbc '
                           'OpenNativeLibrary is a plain dlopen(path, RTLD_NOW) with neither the domain check nor the '
                           'per-thread READY gate. libapp_native_loader.so is a route-A provider dependency '
                           '(verify_route_a_generation.py:693), outside B7.'),
        'fix_site': 'bms/src/adapter/framework/app-native-loader/src/app_native_loader.c (route-A generation)'},
}
BLOCKED['fd-k9'] = dict(BLOCKED['fd-android'])
BLOCKED['fd-saber'] = dict(BLOCKED['fd-libre'])


def main():
    EVID.mkdir(exist_ok=True)
    results = {'task': '#54 B7', 'serial': SERIAL, 'apps': {}}
    for key, pkg in APPS.items():
        rec = {'package': pkg}
        if key == 'fd-k9':
            # Before the installer fix k9 never reached launch on 5cd: record the install wall,
            # then the launch first cause once the B7 installer let it install.
            rec['install_before'] = {
                'install_txt': grab('repro-20260929T112212-k9/fd-k9/install.txt', r'code:9568260'),
                'hilog': grab('k9-install-before-hilog.txt',
                              r'adaptive composition failed|refusing template placeholder|ERR_INSTALL_INTERNAL_ERROR', limit=3)}
            rec['install_after'] = grab(FINAL + '/fd-k9/install.txt', r'install bundle successfully')
            src = FINAL + '/fd-k9/hilog.txt'
        else:
            src = REPRO[key]
        pid = child_pid(src, pkg)
        rec['first_cause'] = grab(src, FIRST[key], pid_of=pid)
        rec['first_cause']['pid'] = pid
        after = FINAL + '/' + key + '/hilog.txt'
        apid = child_pid(after, pkg)
        rec['after_fix'] = {'hilog': 'runs/' + after, 'pid': apid,
                            'original_error_count': count(after, FIRST[key]),
                            'next_stage': grab(after, NEXT, pid_of=apid)['lines']}
        if key in AFTER_MARKER:
            rec['after_fix']['positive_marker'] = grab(after, AFTER_MARKER[key], pid_of=apid)['lines']
            rec['wall'] = 'crossed'
        if key in BLOCKED:
            rec.update(BLOCKED[key]); rec['wall'] = 'blocked'
        rec['lit'] = False
        results['apps'][key] = rec
        excerpt = [f'# {key} ({pkg})', f'# first cause: {rec["first_cause"]["file"]} sha256={rec["first_cause"]["sha256"]}']
        excerpt += [f'{l["line"]}: {l["text"]}' for l in rec['first_cause']['lines']]
        excerpt += [f'# after fixes: {rec["after_fix"]["hilog"]} original_error_count={rec["after_fix"]["original_error_count"]}']
        excerpt += [f'{l["line"]}: {l["text"]}' for l in rec['after_fix'].get('positive_marker', [])]
        excerpt += [f'{l["line"]}: {l["text"]}' for l in rec['after_fix']['next_stage']]
        (EVID / (key + '.txt')).write_text('\n'.join(excerpt) + '\n')
    shots = EVID / 'screens'
    shots.mkdir(exist_ok=True)
    def keep(rel, name):
        (shots / name).write_bytes((RUNS / rel).read_bytes())
        return {'path': 'evidence/screens/' + name, 'sha256': sha(shots / name), 'source': 'runs/' + rel}
    build = json.loads((HERE / 'build-result.json').read_text())
    results['fixes'] = {
        'runtime_jar_overlay': {'baseline_sha256': build['baseline_sha256'], 'output_sha256': build['output_sha256'],
                                'changed_existing_classes': build['changed_existing_classes'],
                                'added_classes': build['added_classes'],
                                'generations': {'r2 a92f8135c70c1a76b462c9a1e71ec8443aaed111c73d812e82f13bea331fc1eb': 'B7 only; used by fix1, b7final*, b7ww',
                                                'r3 ' + build['output_sha256']: 'B5 alias (verbatim) + B7; used by b7r3, b7ww2 (boot 64a531ef)'},
                                'deploy': 'deploy.py apply (bind mount over /system/android/framework/oh-adapter-runtime.jar); rollback: deploy.py rollback',
                                'receipts': sorted('runs/' + str(p.relative_to(RUNS)) for p in RUNS.glob('deploy-*/receipt.json'))},
        'installer': {'baseline_sha256': '675536e8a43ac747cbffc0e130d5681ba7bcf2bd3fd305f3d0d357ca797a793d',
                      'head_rebuild_sha256': '675536e8a43ac747cbffc0e130d5681ba7bcf2bd3fd305f3d0d357ca797a793d',
                      'output_sha256': '1ebf78ab2bbe4573dfbe146b9f99e6b06e3a581fb9d16721c2272bc18e6cdfa5',
                      'raw_sha256': '5520f69e4fd06c8f275ee6dc58096009f1c7e988c9a62d6d7e6b9df5b2f72845',
                      'artifacts': 'VM ~/a2hlab/build-runs/20260929-oh6.1.0.31-b7/installer/',
                      'build_log': 'installer-build-20260929T1156.log',
                      'host_test': 'evidence/installer/host-test-run.log',
                      'receipt': 'runs/installer-apply-20260929T120416/receipt.json',
                      'desktop_after_foundation_restart': keep('installer-apply-20260929T120416/desktop.jpeg', 'installer-black-after-foundation.jpeg'),
                      'desktop_after_reboot': keep('installer-apply-20260929T120416/desktop-after-reboot.jpeg', 'installer-desktop-after-reboot.jpeg'),
                      'rollback': 'deploy_installer.py rollback (backups /data/local/tmp/b7-installer-backup/{0,1}.so)'}}
    hw = 'b7final-20260929T122347/' + SERIAL + '/helloworld'
    hw0 = 'b7hw-legacy-20260929T122237/' + SERIAL + '/helloworld'
    results['no_regression'] = {
        'helloworld': {'with_both_fixes': keep(hw + '/final.jpeg', 'helloworld-both-fixes-t20.jpeg'),
                       'installer_only_no_jar_overlay': keep(hw0 + '/final.jpeg', 'helloworld-installer-only-t20.jpeg'),
                       'record': 'runs/' + hw + '/record.json',
                       'observed_pids': json.loads((RUNS / hw / 'record.json').read_text()).get('observed_pids'),
                       'visual_verdict': 'pending_review'},
        'zigzag_after_switch': {
            'note': ('#63: 5cd switched to the R155 ZigZag candidate generation with reproduce-zigzag-apk quick '
                     '(provider 80c9aee0 + bridge 84695d62 read back from the ZigZag child maps); the reproducer '
                     'installed ZigZag with the B7 installer 1ebf78ab and passed, and HelloWorld with the r4 overlay '
                     '(B5+B7 on 9161b507, 2fae0344) showed its own UI. A ZigZag relaunch with r4 did not count: '
                     'aa force-stop failed and aa start resumed the pre-overlay child (its root JAR read 9161b507). '
                     'Then #63 was paused (#66 generation 6cb40cd6 for all boards); r4 was unmounted.'),
            'reproducer_log': grab('zigzag-quick-5cd-20260929T130910.log', r'install bundle successfully|REPRODUCE_ZIGZAG_APK=PASS', limit=2),
            'zigzag_screen': keep('zigzag-after-switch.jpeg', 'zigzag-r155-candidate-after-switch.jpeg'),
            'helloworld_r4_screen': keep('b7r4hw2-20260929T131445/' + SERIAL + '/helloworld/final.jpeg', 'helloworld-r4-zigzag-generation-t20.jpeg'),
            'zigzag_with_overlay': False},
        'zigzag': {'launched': False,
                   'reason': ('5cd runs the pr03-touch generation (runtime JAR 06141543); ZigZag needs its own '
                              'candidate generation (JAR 9161b507 etc.), and reproduce-zigzag-apk quick would redeploy '
                              'the generation. The B7 JAR overlay is built on 06141543 and cannot be live there; the '
                              'installer change only touches icon classification after both icon readers fail. '
                              'reproduce-zigzag-apk check = PASS (static). Outer loop to decide whether to switch 5cd.')}}
    results['white_window_followup'] = {}
    for run, key, pkg in [('b7ww-20260929T124542', 'ooniprobe', 'org.openobservatory.ooniprobe'),
                          ('b7ww-20260929T124542', 'fd-etar', 'ws.xsoh.etar'),
                          ('b7ww-20260929T124542', 'fd-fluffychat', 'chat.fluffy.fluffychat'),
                          ('b7ww2-20260929T130032', 'burgerking', 'com.emn8.mobilem8.nativeapp.bk'),
                          ('b7ww2-20260929T130032', 'fd-immich', 'app.alextran.immich'),
                          ('b7ww2-20260929T130032', 'fd-kitchenowl', 'com.tombursch.kitchenowl'),
                          ('b7ww2-20260929T130032', 'fd-minetest', 'net.minetest.minetest')]:
        ww = run + '/' + SERIAL
        rel = ww + '/' + key + '/hilog.txt'
        pid = child_pid(rel, pkg)
        results['white_window_followup'][key] = {
            'b7_marker': grab(rel, r'\[B7\] nativeLibraryDir', pid_of=pid)['lines'],
            'bind_failure': grab(rel, r'Caused by: (android\.content\.pm\.PackageManager\$NameNotFoundException|java\.lang\.IllegalArgumentException: Couldn.t find meta-data)', pid_of=pid)['lines'],
            'run': 'runs/' + ww,
            'namespace_error_count': count(rel, r'Unable to create namespace'),
            'observed_pids': json.loads((RUNS / ww / key / 'record.json').read_text()).get('observed_pids')}
    results['white_window_followup']['note'] = (
        'b7ww ran 3 keys before all three boards dropped from hdc (STOP assigned serial detached); '
        'the other 4 ran in b7ww2 after the boards returned (boot 64a531ef, B5+B7 overlay r3). '
        'Namespace class (fd-etar, burgerking) crossed; every app then stops at the androidx.startup '
        'InitializationProvider getProviderInfo NameNotFound (or minetest FileProvider meta-data) = #65 items 1-3.')
    results['apps']['fd-k9']['install_after_hilog'] = grab(
        'k9-install-after-hilog.txt', r'adaptive composition failed|ICONLESS_APK_TEMPLATE_PLACEHOLDER|on finished result is', limit=3)
    results['bridge_84695d62_experiment'] = {
        'run': 'runs/b7bridge84-20260929T130450/' + SERIAL + '/helloworld',
        'lines': grab('b7bridge84-20260929T130450/' + SERIAL + '/helloworld/hilog.txt',
                      r'exact adapter bridge admission failed|WLCGATE:LSP:FAIL_PROVIDER|exit with code', limit=3)['lines'],
        'conclusion': ('provider 6787ea7d pins bridge 7db99e1b and runtime 9ccf64f8; bridge 84695d62 pairs with '
                       'provider 80c9aee0 (ZigZag candidate). Bind mount rolled back.')}
    results['lit_candidates'] = []
    (HERE / 'results.json').write_text(json.dumps(results, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps({k: (v.get('wall'), v['first_cause']['lines'][0]['line'] if v['first_cause']['lines'] else None,
                          v['after_fix']['original_error_count']) for k, v in results['apps'].items()}, indent=1))


if __name__ == '__main__':
    main()
