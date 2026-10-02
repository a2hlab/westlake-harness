#!/usr/bin/env python3
"""Attribute every U14-vs-846 difference to a source file and a class: a) intended, b) missing source, c) unknown.

    attribute.py [--out difflist-v3.csv]          # env U14_GEN / U14_DIFF / U14_FN03 select another build

Inputs: diff-v3/strings-846-vs-u14.txt (deployed_strings_diff), diff-v3/abi-diff-846-vs-u14.json (abi_diff --calls),
diff-v3/needed-undefined.txt (all from diffs.sh). Source trees searched:
  U14   the exported master bms/src/adapter + the oh61-v7 snapshot window cohort + the fn03 cohort (what was compiled)
  LOCAL every local copy of the bridge sources (bms-deploy .work generations, cc-wiki B1 private tree, real-work,
        00.Workspace, bms-deploy benchmark source sets) -- to tell "the source exists somewhere" from "nowhere"
A string ADDED is attributed to the U14 file holding it; a string DROPPED is looked up in LOCAL (found -> which file;
not found -> b, missing source). Binary-noise strings (mostly non-text: jump tables, PNG/eh_frame bytes, readelf
labels) are classed `layout`. Symbols (removed/added exports, drift, call diffs, undefined) are attributed by their
class/function name to the U14 file that defines it, or to the LOCAL file for removed ones.
Classes (rules, in order):
  a  intended: display_manager framework copy (OH-DISPLAY-EVENT / DisplayManagerProjectionProxy / RegisterDisplayListener),
     master ability_scheduler_adapter.cpp manifest orientation (APK-ORIENTATION, incl. its WindowSessionProperty calls),
     master package-manager/core changes, strict-link symbol versioning
  b  846 behaviour the compiled window cohort lacks, with the restore action in `action`:
       R1 focus bridge (WindowCallbackBridge)       -> port from real-work session_stage_adapter.cpp 0765bc53
       R2 root BLAST + createSession null-BBQ refusal -> port from 0765bc53 + oh_window_manager_client.cpp 0b816fe6
       R3 process-published RSSurfaceNode holder (publish / cross-copy acquire / destroySession unsetenv)
                                                     -> in no local tree: rewrite
  c  unknown / needs a decision: anything else (app-specific strings; fn03 skew if a non-matching fn03 is compiled)
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
import os as _os
GEN = Path(_os.environ.get('U14_GEN', str(lab_paths.inputs() / 'generations/u14-bridge-v3')))
DIFF = Path(_os.environ.get('U14_DIFF', str(HERE / 'diff-v3')))
_FW = GEN / 'src/bms/src/adapter/framework'
_SNAP = lab_paths.inputs() / 'sources/oh61-v7-b2133b5b-f6a498d1/framework'
# exactly what the hardened recipe compiled: master framework/{core,activity,surface,broadcast,contentprovider,
# package-manager,native-compat} + master's display_manager_adapter_jni.cpp + the snapshot's window/jni and activity/core
U14 = [_FW / d for d in ('core', 'activity/jni', 'surface', 'broadcast', 'contentprovider', 'package-manager', 'native-compat')] + \
      [_FW / 'window/jni/display_manager_adapter_jni.cpp', _SNAP / 'window/jni', Path(_os.environ.get('U14_FN03', str(lab_paths.inputs() / 'sources/fn03-core-846-recon-v1')))]
LOCAL = [WS / 'westlake-harness-bms-deploy/bms/src/.work', WS / '_cc-wiki-b1-src/adapter',
         WS / '01.OH61AOSP16/real-work/src/adapter', WS / '00.Workspace/src/adapter',
         WS / 'westlake-harness-bms-deploy/benchmark']
EXT = ('*.cpp', '*.cc', '*.c', '*.h')


_CORPUS = {}


def corpus(roots):
    """Bridge-relevant source files under roots, read once: framework/{window,activity,surface,core,package-manager}
    jni/core/src dirs, oh_window_manager_client / session_stage / fn03 / display_manager files wherever they live."""
    key = tuple(str(r) for r in roots)
    if key in _CORPUS:
        return _CORPUS[key]
    files = {}
    pat = re.compile(r'framework/(window|activity|surface|core|package-manager|broadcast|contentprovider|native-compat)/|'
                     r'oh_window_manager_client|session_stage_adapter|fn03_lifecycle_core|display_manager_adapter_jni|'
                     r'window_callback_adapter')
    for r in roots:
        if not r.exists():
            continue
        if r.is_file():
            files[str(r)] = r.read_text(errors='replace')
            continue
        for dirpath, dirnames, filenames in os.walk(r):
            dirnames[:] = [d for d in dirnames if d not in ('local_oh_headers', 'oh', 'third_party', 'out', 'obj', '.git', 'node_modules')]
            for f in filenames:
                if f.endswith(('.cpp', '.cc', '.c', '.h')):
                    full = os.path.join(dirpath, f)
                    if pat.search(full):
                        try:
                            files[full] = open(full, errors='replace').read()
                        except OSError:
                            pass
    _CORPUS[key] = files
    return files


def grep(needle, roots):
    return sorted(f for f, text in corpus(roots).items() if needle in text)


def short(p):
    return p.replace(str(WS), '$WORKSPACES')


def is_noise(s):
    if 'bad_array_new_length' in s and not s.startswith('St20'):
        return True
    text = sum(1 for c in s if c.isalnum() or c in ' _:%/()[]{}.,=-<>\'"')
    return s.startswith('[ ') and re.match(r'\[\s*[0-9a-f]+\]', s) or sum(1 for c in s if c == '.') > 0.3 * len(s) or text < 0.8 * len(s)


def s_is_jni_object_sig(t):
    return t.strip() == '()Ljava/lang/Object;'


def classify(item, files_u14, files_local):
    t = item
    if re.search(r'OH-DISPLAY-EVENT|OH_DisplayEvent|DisplayManagerProjectionProxy|dispatchDisplayEvent|RegisterDisplayListener|IDisplayListener', t):
        return 'a', 'display_manager_adapter_jni.cpp: framework copy (script excludes the oh61 one on purpose)'
    if re.search(r'__android_log_(print|set_logger)', t):
        return 'a', 'strict link against board libc.so (ld-musl) gives versioned @LIBC references'
    if s_is_jni_object_sig(t):
        return 'b', 'R2: JNI signature of WeakReference.get used by the 846 EnableRootBlast -> port from 0765bc53'
    if 'WindowSessionProperty' in t:
        return 'a', 'master ability_scheduler_adapter.cpp APK-ORIENTATION: builds a WindowSessionProperty for the parent MainSession (not the window client)'
    if re.search(r'getRSSurfaceNode\(int\)|process-published|RS_SURFACE_NODE_HOLDER|publishProcessWindowTarget|destroySession|unsetenv|RSSurfaceNode>, std', t):
        return 'b', 'R3 process-published RSSurfaceNode holder (846 window client; in no local tree) -> rewrite'
    if re.search(r'EnableRootBlast|mUseBLASTAdapter|mViewAncestor|WeakReference|null-BBQ|root BLAST|createSession', t):
        return 'b', 'R2 root BLAST + null-BBQ refusal (846) -> port from real-work session_stage_adapter.cpp 0765bc53 / oh_window_manager_client.cpp 0b816fe6:495-500'
    if re.search(r'InheritedParentFocus|InheritsParentFocus|callFocusBridge|FocusBridge|WindowCallbackBridge', t):
        return 'b', 'R1 focus bridge (846: OH focus -> WindowCallbackBridge.onUpdateFocusStatus -> ViewRootImpl focus) -> port from 0765bc53'
    if 'OH_CLEAN_REPLAY' in t:
        return 'c', 'fn03 lifecycle core version skew'
    if re.search(r'getRSSurfaceNode: (unknown sessionId|sessionId=%d has no RSSurfaceNode)', t):
        return 'b', 'R3: the snapshot getRSSurfaceNode has no process-published fallback -> rewrite'
    if 'CapybaraAdventure' in t or 'CapybaraLetterbox' in t:
        return 'c', 'app-specific hard-coded package in master ability_scheduler_adapter.cpp; Java peer absent from the U13 jars'
    if re.search(r'APK-ORIENTATION|ManifestOrientationProjection|resolveOhOrientation|ISession>|CallStaticIntMethod|ScheduleAbilityTransaction', t):
        return 'a', 'master ability_scheduler_adapter.cpp (manifest orientation -> MainSession); Java peer ManifestOrientationProjection absent from the U13 jars -> logs and no-ops'
    if 'onUpdateFocus' in t or 'UpdateFocus' in t or 'SetActive' in t:
        return 'b', 'R1 focus bridge: the snapshot routes focus to SessionStageBridge.onUpdateFocus (Java: log only); 846 calls WindowCallbackBridge.onUpdateFocusStatus -> dispatchWindowFocusChanged -> port from 0765bc53'
    if 'fn03::' in t or re.search(r'ACTIVITY_GENERATION|FIRST_FRAME_|LIFECYCLE_REQUEST|OH_TERMINAL_FACT|RETIRE|SOURCE_STATE_MISMATCH|TRANSITION_IN_FLIGHT|ACTIVITY_NOT_REGISTERED', t):
        return 'c', 'fn03 lifecycle core: the snapshot (dd57a00b) is NEWER than the 846 build here (retire/generation API) and OLDER elsewhere (846 OH_CLEAN_REPLAY) -> a different fn03 version than the one deployed'
    if any('package-manager' in f for f in files_u14) or 'package_info' in t or 'PackageInfo' in t:
        return 'a', 'master package-manager sources (cx-bms) newer than 846'
    return 'c', 'needs a decision'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'difflist-v3.csv'))
    a = ap.parse_args()
    rows = []
    for line in (DIFF / 'strings-846-vs-u14.txt').read_text().splitlines():
        m = re.match(r'^(DROPPED|ADDED)\s+(.*)$', line)
        if not m:
            continue
        kind, lit = m.group(1), m.group(2)
        s = eval(lit) if lit[:1] in '\'"' else lit
        if is_noise(s):
            rows.append({'kind': 'string-' + kind.lower(), 'item': s[:80], 'class': 'layout', 'source': '',
                         'reason': 'non-text bytes / readelf offset label (layout shift)'})
            continue
        probe = re.split(r'%|\\', s)[0].strip()[:60] or s[:60]
        fu = grep(probe, U14) if kind == 'ADDED' else []
        fl = grep(probe, LOCAL) if kind == 'DROPPED' else []
        cls, why = classify(s, fu, fl)
        if kind == 'DROPPED' and fl and cls == 'b':
            why += f'; but found in {len(fl)} local file(s): restorable'
        if kind == 'DROPPED' and not fl:
            why += '; in no local source tree'
        rows.append({'kind': 'string-' + kind.lower(), 'item': s[:120], 'class': cls,
                     'source': ' '.join(short(x) for x in (fu or fl)[:3]), 'reason': why})
    abi = json.loads((DIFF / 'abi-diff-846-vs-u14.json').read_text())
    cxxfilt = subprocess.run(['xcrun', '-f', 'llvm-cxxfilt'], capture_output=True, text=True).stdout.strip() or 'c++filt'

    def dem(sym):
        return subprocess.run([cxxfilt, sym], capture_output=True, text=True).stdout.strip()
    for kind in ('removed', 'added'):
        for sym in abi.get(kind, []):
            d = dem(sym)
            if 'std::__h::' in d.split('(')[0] or d.startswith(('std::', 'construction vtable')):
                cls, why = 'layout', 'container template instantiation / vtable emitted by the compiler'
            else:
                cls, why = classify(d, [], [])
                if cls == 'c' and 'fn03::' in d:
                    why = 'fn03 lifecycle core: snapshot (dd57a00b) differs from the 846 build in both directions'
            rows.append({'kind': 'export-' + kind, 'item': d[:120], 'class': cls, 'source': '', 'reason': why})
    for dr in abi.get('drift', []):
        rows.append({'kind': 'signature-drift', 'item': str(dr.get('function'))[:120], 'class': 'b',
                     'reason': 'R1/R2: SessionStageAdapter is 24 bytes larger in 846 = focusBridgeClass_ + focusBridgeObj_ + inheritsParentFocus_ (0765bc53 header); goes away with the port', 'source': ''})
    for cd in abi.get('call_diffs', []):
        d = (cd.get('demangled') or cd.get('function')) if isinstance(cd, dict) else str(cd)
        if d.startswith('_Z'):
            d = dem(d)
        cls, why = classify(d + ' ' + json.dumps(cd), [], [])
        if cls == 'c' and 'fn03::' in d:
            why = 'fn03 lifecycle core version skew'
        rows.append({'kind': 'call-set', 'item': d[:120], 'class': cls, 'source': '', 'reason': why})
    for line in (DIFF / 'needed-undefined.txt').read_text().splitlines():
        m = re.match(r'^([-+])\s+(\S+)', line)
        if m:
            d = dem(m.group(2))
            cls, why = classify(d, [], [])
            rows.append({'kind': 'undefined' + m.group(1), 'item': d[:120], 'class': cls, 'source': '', 'reason': why})
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['kind', 'class', 'item', 'source', 'reason'])
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    c = Counter((r['class'], r['kind']) for r in rows)
    for k, v in sorted(c.items()):
        print(k, v)
    for r in rows:
        if r['class'] == 'c':
            print('  c:', r['kind'], '|', r['item'][:90], '|', r['source'][:120])
    return 0


if __name__ == '__main__':
    sys.exit(main())
