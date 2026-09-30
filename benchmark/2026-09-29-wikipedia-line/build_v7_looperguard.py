"""v7 = cc-t3 r17 runtime JAR (8f4774e1) + MainLooperGuard (tagsoup NoSuchMethodError tolerated).

Adds adapter/activity/MainLooperGuard and one call MainLooperGuard.install() in B7BindFixes.apply,
right after SelfUidPackages.install(p0).
Asserts that B7BindFixes is the only existing class that changed.
"""
from pathlib import Path
import hashlib, shutil, subprocess, sys, zipfile

S = Path('/private/tmp/claude-501/-Users-zhaoyue-orca-workspaces-westlake-harness-wiki/'
         '4f14ff30-5859-4fc2-a178-411cb223d271/scratchpad/jars')
DEPS = S / 'deps'
HERE = Path(__file__).resolve().parent
SRC = HERE / 'MainLooperGuard.java'
BASE = S / 'r17b.jar'
BASE_SHA = '8f4774e16cf798ae'  # prefix check below
OUT = S / 'v7-looperguard.jar'
BUILD = S / 'v7-build'

android_jar = DEPS / 'android.jar'
d8_jar = DEPS / 'd8.jar'
smali_cp = ':'.join(str(p) for p in sorted(DEPS.glob('*.jar'))
                    if p.name not in ('android.jar', 'd8.jar') and not p.name.startswith('baseline'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
run = lambda a: subprocess.run([str(x) for x in a], check=True)

assert sha(BASE).startswith(BASE_SHA), 'r17 base changed'
if BUILD.exists():
    shutil.rmtree(BUILD)
BUILD.mkdir(parents=True)
classes = BUILD / 'classes'; classes.mkdir()
dexdir = BUILD / 'dex'; dexdir.mkdir()

run(['javac', '--release', '8', '-cp', android_jar, '-d', classes, SRC])
run(['java', '-cp', d8_jar, 'com.android.tools.r8.D8', '--release', '--min-api', '22',
     '--lib', android_jar, '--output', dexdir, *classes.rglob('*.class')])

with zipfile.ZipFile(BASE) as z:
    (BUILD / 'baseline.dex').write_bytes(z.read('classes.dex'))
base_sm = BUILD / 'base'; new_sm = BUILD / 'new'
run(['java', '-cp', smali_cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'baseline.dex', '-o', base_sm])
run(['java', '-cp', smali_cp, 'org.jf.baksmali.Main', 'disassemble', dexdir / 'classes.dex', '-o', new_sm])
original = {str(p.relative_to(base_sm)): p.read_bytes() for p in base_sm.rglob('*.smali')}

added = []
for p in (new_sm / 'adapter' / 'activity').glob('MainLooperGuard*.smali'):
    rel = str(p.relative_to(new_sm))
    assert rel not in original, 'collision: ' + rel
    shutil.copyfile(p, base_sm / rel)
    added.append(rel)
assert added

b7 = base_sm / 'adapter/activity/B7BindFixes.smali'
text = b7.read_text()
anchor = 'invoke-static {p0}, Ladapter/activity/SelfUidPackages;->install(Landroid/content/pm/ApplicationInfo;)V\n'
assert text.count(anchor) == 1, 'anchor count=' + str(text.count(anchor))
text = text.replace(anchor, anchor + '\n    invoke-static {}, Ladapter/activity/MainLooperGuard;->install()V\n')
b7.write_text(text)

run(['java', '-cp', smali_cp, 'org.jf.smali.Main', 'assemble', base_sm, '-o', BUILD / 'classes.dex'])
post = BUILD / 'post'
run(['java', '-cp', smali_cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'classes.dex', '-o', post])
changed = [n for n, d in original.items() if not (post / n).exists() or (post / n).read_bytes() != d]
if changed != ['adapter/activity/B7BindFixes.smali']:
    print('UNEXPECTED changed:', changed); sys.exit(1)
assert (post / 'adapter/activity/B7BindFixes.smali').read_text().count('MainLooperGuard;->install(') == 1

with zipfile.ZipFile(BASE) as src, zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as dst:
    for item in src.infolist():
        dst.writestr(item, (BUILD / 'classes.dex').read_bytes() if item.filename == 'classes.dex'
                     else src.read(item.filename))
print('base(r17)    :', sha(BASE))
print('output       :', OUT)
print('output_sha256:', sha(OUT))
print('changed      :', changed)
print('added        :', added)
