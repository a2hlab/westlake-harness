"""R2 connectivity via runtime JAR (no boot-image rebuild).

Take the existing r14 oh-adapter-runtime.jar and add adapter.activity.OnlineConnectivityManager
(+ inner OnlineNetworkInfo/OnlineNetworkCapabilities), then inject one call
`OnlineConnectivityManager.install()` into B7BindFixes.smali right after it calls
B8BindExtras.installServiceStubs(). install() replaces the SystemServiceRegistry "connectivity"
fetcher so getSystemService(CONNECTIVITY_SERVICE) hands out the online subclass.

Compile trick: android.jar's real ConnectivityManager has no accessible no-arg ctor, but the board's
AOT stub does (public <init>()V). So we compile OnlineConnectivityManager against Westlake's
mainline-stub android.net.*.java (public ctors, same lineage as the board classes), and keep ONLY
the adapter/activity/OnlineConnectivityManager* classes in the output dex (android/net/* resolve to
the board's classes at runtime).
"""
from pathlib import Path
import hashlib, shutil, subprocess, sys, zipfile

S = Path('/private/tmp/claude-501/-Users-zhaoyue-orca-workspaces-westlake-harness-wiki/'
         '4f14ff30-5859-4fc2-a178-411cb223d271/scratchpad/jars')
DEPS = S / 'deps'
ONLINE = Path('/private/tmp/claude-501/-Users-zhaoyue-orca-workspaces-westlake-harness-wiki/'
              '4f14ff30-5859-4fc2-a178-411cb223d271/scratchpad/onlinecm/OnlineConnectivityManager.java')
WNET = Path('/Users/zhaoyue/orca/workspaces/vm-copies/westlake-current/'
            'framework/mainline-stubs/java/android/net')
BASE = S / 'r14.jar'
OUT = S / 'r14-onlinecm.jar'
BUILD = S / 'onlinecm-build'

android_jar = DEPS / 'android.jar'
d8_jar = DEPS / 'd8.jar'
smali_cp = ':'.join(str(p) for p in sorted(DEPS.glob('*.jar'))
                    if p.name not in ('android.jar', 'd8.jar') and not p.name.startswith('baseline'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
run = lambda a: subprocess.run([str(x) for x in a], check=True)

if BUILD.exists():
    shutil.rmtree(BUILD)
BUILD.mkdir(parents=True)
classes = BUILD / 'classes'; classes.mkdir()
dexdir = BUILD / 'dex'; dexdir.mkdir()

# Westlake android.net sources provide the superclasses (public ctors) for compilation only.
wl_srcs = [WNET / (c + '.java') for c in
           ('ConnectivityManager', 'Network', 'NetworkInfo', 'NetworkCapabilities', 'NetworkRequest')]
for s in wl_srcs + [ONLINE]:
    assert s.exists(), s
run(['javac', '-source', '8', '-target', '8', '-bootclasspath', android_jar,
     '-cp', android_jar, '-d', classes, '-nowarn', ONLINE, *wl_srcs])

# Keep ONLY adapter/activity/OnlineConnectivityManager* in the output dex.
keep = sorted((classes / 'adapter' / 'activity').glob('OnlineConnectivityManager*.class'))
assert keep, 'no OnlineConnectivityManager classes compiled'
print('compiled ->', [p.name for p in keep])
run(['java', '-cp', d8_jar, 'com.android.tools.r8.D8', '--release', '--min-api', '22',
     '--lib', android_jar, '--output', dexdir, *keep])

# baksmali r14 + the new dex
with zipfile.ZipFile(BASE) as z:
    (BUILD / 'baseline.dex').write_bytes(z.read('classes.dex'))
base_sm = BUILD / 'base'; new_sm = BUILD / 'new'
run(['java', '-cp', smali_cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'baseline.dex', '-o', base_sm])
run(['java', '-cp', smali_cp, 'org.jf.baksmali.Main', 'disassemble', dexdir / 'classes.dex', '-o', new_sm])

original = {str(p.relative_to(base_sm)): p.read_bytes() for p in base_sm.rglob('*.smali')}

# add my classes
added = []
for p in (new_sm / 'adapter' / 'activity').glob('OnlineConnectivityManager*.smali'):
    rel = str(p.relative_to(new_sm))
    assert rel not in original, ('collision: ' + rel)
    (base_sm / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, base_sm / rel)
    added.append(rel)
assert added, 'no OnlineConnectivityManager smali produced'

# inject the install() call into B7BindFixes.smali after installServiceStubs()
b7 = base_sm / 'adapter/activity/B7BindFixes.smali'
text = b7.read_text()
anchor = 'invoke-static {}, Ladapter/activity/B8BindExtras;->installServiceStubs()V\n'
assert text.count(anchor) == 1, ('B7 anchor count=' + str(text.count(anchor)))
inject = anchor + '\n    invoke-static {}, Ladapter/activity/OnlineConnectivityManager;->install()V\n'
b7.write_text(text.replace(anchor, inject))

run(['java', '-cp', smali_cp, 'org.jf.smali.Main', 'assemble', base_sm, '-o', BUILD / 'classes.dex'])

# verify only B7BindFixes changed among existing classes
post = BUILD / 'post'
run(['java', '-cp', smali_cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'classes.dex', '-o', post])
changed = [n for n, d in original.items() if not (post / n).exists() or (post / n).read_bytes() != d]
unexpected = [c for c in changed if c != 'adapter/activity/B7BindFixes.smali']
if unexpected:
    print('UNEXPECTED changed:', unexpected); sys.exit(1)

with zipfile.ZipFile(BASE) as src, zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as dst:
    for item in src.infolist():
        dst.writestr(item, (BUILD / 'classes.dex').read_bytes() if item.filename == 'classes.dex'
                     else src.read(item.filename))

print('baseline(r14):', sha(BASE))
print('output       :', OUT)
print('output_sha256:', sha(OUT))
print('changed      :', changed)
print('added        :', added)
