"""R2 connectivity fix: swap the offline android.net.* stubs in the board's
adapter-mainline-stubs.jar for Westlake's online (single validated WiFi) stubs.

Same baksmali-swap method as benchmark/2026-09-29-bms-link-entry-walls/build.py, but
we REPLACE whole android/net/* classes (Westlake mainline-stub sources) rather than
inject calls. Only the intended classes may change; everything else stays byte-identical.

Root cause proven on 5ea: board CM.getActiveNetwork()/getActiveNetworkInfo() return null
-> Wikipedia ConnectionStateMonitor decides offline -> MainActivity.onGoOffline ->
MainFragment.getCurrentFragment() NPE -> System.exit(1). Westlake's stubs report online.
"""
from pathlib import Path
import hashlib, shutil, subprocess, sys, zipfile

S = Path('/private/tmp/claude-501/-Users-zhaoyue-orca-workspaces-westlake-harness-wiki/'
         '4f14ff30-5859-4fc2-a178-411cb223d271/scratchpad/jars')
DEPS = S / 'deps'
WNET = Path('/Users/zhaoyue/orca/workspaces/vm-copies/westlake-current/'
            'framework/mainline-stubs/java/android/net')
BASE = S / 'mls.jar'
OUT = S / 'mls-online.jar'
BUILD = S / 'mls-build'
CLASSES_TO_SWAP = ['ConnectivityManager', 'Network', 'NetworkInfo',
                   'NetworkCapabilities', 'NetworkRequest', 'LinkProperties']

android_jar = DEPS / 'android.jar'
d8_jar = DEPS / 'd8.jar'
smali_cp = ':'.join(str(p) for p in sorted(DEPS.glob('*.jar'))
                    if p.name not in ('android.jar', 'd8.jar') and not p.name.startswith('baseline'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(args):
    subprocess.run([str(x) for x in args], check=True)


if BUILD.exists():
    shutil.rmtree(BUILD)
BUILD.mkdir(parents=True)
classes = BUILD / 'classes'; classes.mkdir()
dexdir = BUILD / 'helper-dex'; dexdir.mkdir()

srcs = [WNET / (c + '.java') for c in CLASSES_TO_SWAP]
for s in srcs:
    assert s.exists(), s
# android.* sources: compile against android.jar as bootclasspath (NOT --release,
# which enforces platform-module rules and rejects defining android.* packages).
run(['javac', '-source', '8', '-target', '8', '-bootclasspath', android_jar,
     '-cp', android_jar, '-d', classes, '-nowarn', *srcs])
run(['java', '-cp', d8_jar, 'com.android.tools.r8.D8', '--release', '--min-api', '22',
     '--lib', android_jar, '--output', dexdir, *classes.rglob('*.class')])

# baksmali baseline jar and the freshly compiled classes
with zipfile.ZipFile(BASE) as z:
    (BUILD / 'baseline.dex').write_bytes(z.read('classes.dex'))
base_sm = BUILD / 'base-smali'; new_sm = BUILD / 'new-smali'
run(['java', '-cp', smali_cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'baseline.dex', '-o', base_sm])
run(['java', '-cp', smali_cp, 'org.jf.baksmali.Main', 'disassemble', dexdir / 'classes.dex', '-o', new_sm])

original = {str(p.relative_to(base_sm)): p.read_bytes() for p in base_sm.rglob('*.smali')}

# Replace every android/net/* class the compile produced (the 6 classes + their inners).
replaced = []
for p in (new_sm / 'android' / 'net').rglob('*.smali'):
    rel = str(p.relative_to(new_sm))
    dest = base_sm / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)
    replaced.append(rel)

run(['java', '-cp', smali_cp, 'org.jf.smali.Main', 'assemble', base_sm, '-o', BUILD / 'classes.dex'])

# Verify: only android/net/* classes we intended changed; everything else identical.
post = BUILD / 'post'
run(['java', '-cp', smali_cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'classes.dex', '-o', post])
changed = [n for n, d in original.items()
           if not (post / n).exists() or (post / n).read_bytes() != d]
added = sorted(str(p.relative_to(post)) for p in post.rglob('*.smali')
               if str(p.relative_to(post)) not in original)
unexpected = [c for c in changed if not c.startswith('android/net/')]
if unexpected:
    print('UNEXPECTED changed classes:', unexpected); sys.exit(1)

# Repackage: copy the baseline jar, swap only classes.dex.
with zipfile.ZipFile(BASE) as src, zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as dst:
    for item in src.infolist():
        dst.writestr(item, (BUILD / 'classes.dex').read_bytes() if item.filename == 'classes.dex'
                     else src.read(item.filename))

print('baseline_sha256 :', sha(BASE))
print('output          :', OUT)
print('output_sha256   :', sha(OUT))
print('changed_classes :', sorted(changed))
print('added_classes   :', added)
