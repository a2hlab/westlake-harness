"""#31 dynamic probe: while a first-launch click queues on the UI thread, sample
the UI thread stack + RenderThread state to catch nPause/pauseSurface waiting.

Adapted from #25's run25.py for board C and the bisect29a (#14 integrate) stage.
Flow: launch toutiao (handwritten targets, sp20 candidate) -> wait for category
UI (long window, bind ~45s on this board) -> fire the click -> sample stacks
every 2s for up to 60s -> capture the TOUCH21 run line when consumed -> pull
child.stderr + faultlog (A-rule evidence).
"""
import subprocess, pathlib, json, re, time, sys

S = '61b0657200000000000000000324012c'
H = '/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh'
A = pathlib.Path('/home/dspfac/a2hlab/source-closure/verify')
import os
FW = pathlib.Path(os.environ.get(
    'FW31',
    str(pathlib.Path.home() / 'a2hlab/board' / S / 'bisect29a' / 'framework' / 'device-report.json')))
R = pathlib.Path.home() / 'a2hlab/board' / S / 'npause31'
R.mkdir(parents=True, exist_ok=True)
PKG = 'com.ss.android.article.news'

def dev(c, timeout=90):
    p = subprocess.run([H, '-t', S, 'shell', c], capture_output=True, timeout=timeout)
    out = (p.stdout + p.stderr).decode(errors='replace').replace('\r', '')
    return out

def note(name, text):
    (R / name).write_text(text)

# ---- launch -----------------------------------------------------------------
name = sys.argv[1] if len(sys.argv) > 1 else 'npause-probe1'
r = R / name
if r.exists():
    print('run dir exists:', r); sys.exit(1)
# probe_source_app requires --out to be new: do NOT pre-create; only the parent
MANIFEST = pathlib.Path.home() / 'a2hlab/manifest'
cmd = ['python3', str(MANIFEST / 'tools/probe_source_app.py'),
       '--workspace', str(A), '--westlake-source', str(A / 'westlake'),
       '--framework-report', str(FW),
       '--app-input', str(pathlib.Path.home() / 'a2hlab/app-inputs/toutiao'),
       '--app', 'toutiao', '--hdc', H, '--serial', S, '--out', str(r),
       '--host-build', str(A / 'out/signed-host'),
       '--webview-input', str(A / 'out/webview-input-source'),
       '--source-webview-build', str(A / 'out-sp20/webview-candidate'),
       '--runtime-env', 'WL_TOUCH_TRACE=1',
       '--android-native-target', 'libvision_core.so',
       '--android-native-target', 'libc++_shared.so',
       '--android-native-target', 'libsscronet.so',
       '--android-native-net-target', 'libsscronet.so']
with (R / f'{name}-launch.log').open('w') as f:  # outside r: probe requires --out new
    subprocess.run(cmd, cwd=str(MANIFEST),
                   stdout=f, stderr=subprocess.STDOUT, check=True)
d = json.loads((r / 'device-report.json').read_text())
pid = d['child']
log = d['runtime'] + f'/private-tmp/adapter_child_{pid}.stderr'
print('LAUNCHED', name, 'child', pid, flush=True)

# ---- wait for category UI (long window: bind ~45s here) ----------------------
start = time.monotonic()
consented = False
while time.monotonic() - start < 150:
    dev('echo v > /data/local/tmp/noice_tap 2>/dev/null')
    raw = dev('tail -n 900 ' + log)
    if not consented and '"同意"' in raw:
        (r / 'consent-vt.txt').write_text(raw)
        dev('echo c 600 1273 > /data/local/tmp/noice_tap')
        consented = True
    if consented and ('FontTextView' in raw and '"头条"' in raw):
        (r / 'before-vt.txt').write_text(raw)
        break
    time.sleep(2)
else:
    print('NO CATEGORY UI in 150s', flush=True)

# ---- foreground + click + VT-hash consumption criterion ----------------------
# The [TOUCH21] string was touch21-build instrumentation and does not exist on this
# build line; the TOUCHFD-787/788 traces are LOGI and never reach stderr. The build-
# independent criterion: wait for the view tree to go stable, click, then time how
# long until the tree hash changes (the app consumed the click and re-laid-out).
import hashlib
def vt_hash():
    dev('echo v > /data/local/tmp/noice_tap 2>/dev/null')
    time.sleep(0.3)
    raw = dev('tail -n 500 ' + log)
    vts = [l for l in raw.splitlines() if l.startswith('VT ') or 'OH_InputBridge: VT' in l]
    return hashlib.md5(chr(10).join(vts).encode()).hexdigest(), len(vts)

dev('aa start -b org.westlake.imehost -a EntryAbility')
time.sleep(1)
baseline = None
streak = 0
for _ in range(30):
    h, n = vt_hash()
    if h == baseline:
        streak += 1
        if streak >= 3:
            break
    else:
        baseline, streak = h, 0
(r / 'vt-baseline.json').write_text(json.dumps({'hash': baseline, 'stable_polls': streak}))
(r / 'vt-pre.txt').write_text(dev('tail -n 500 ' + log))

click_t0 = time.monotonic()
dev('echo i 309 213 > /data/local/tmp/noice_tap')
samples = []
consumed_at = None
while time.monotonic() - click_t0 < 60:
    h, n = vt_hash()
    t = round(time.monotonic() - click_t0, 1)
    samples.append({'t': t, 'vt_hash': h, 'vt_lines': n, 'changed': h != baseline})
    (r / 'stack-samples.jsonl').write_text('\n'.join(json.dumps(s) for s in samples) + '\n')
    if h != baseline:
        consumed_at = t
        break
    time.sleep(1)

(r / 'summary.json').write_text(json.dumps({
    'name': name, 'child': pid, 'click_consumed_after_s': consumed_at,
    'samples': samples}, indent=1) + '\n')
dev('echo v > /data/local/tmp/noice_tap'); time.sleep(1)
(r / 'after-tail.txt').write_text(dev('tail -n 2000 ' + log))
# A-rule evidence pull (before any cleanup)
raw_log = dev('cat ' + log)
(r / 'child.stderr').write_bytes(raw_log.encode(errors='replace'))
faults = dev(f'find /data/log/faultlog -type f -name "*-{pid}-*" 2>/dev/null')
(r / 'fault-paths.txt').write_text(faults)
print('DONE', name, 'consumed_after_s=', consumed_at, flush=True)

# ---- stop ---------------------------------------------------------------------
for p in (pid, d.get('parent')):
    if p:
        dev(f'kill -9 {p} 2>/dev/null; true')
dev(f'rm -rf {d.get("stage","/nonexistent")} 2>/dev/null; true')
dev(f'rm -rf {d.get("runtime","/nonexistent")} 2>/dev/null; true')
