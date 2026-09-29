"""v5 = v4 runtime JAR (2fbfd8bc) + BigStackMain: ActivityThread.main on a 32 MiB thread.

Adds adapter/activity/BigStackMain and rewrites the single Method.invoke of ActivityThread.main in
AppSpawnXInit.invokeStaticMain into BigStackMain.invoke (same register list, no move-result).
Asserts that AppSpawnXInit is the only existing class that changed.
"""
from pathlib import Path
import hashlib, shutil, subprocess, sys, zipfile

S = Path('/private/tmp/claude-501/-Users-zhaoyue-orca-workspaces-westlake-harness-wiki/'
         '4f14ff30-5859-4fc2-a178-411cb223d271/scratchpad/jars')
DEPS = S / 'deps'
HERE = Path(__file__).resolve().parent
SRC = HERE / 'BigStackMain.java'
BASE = S / 'r14-onlinecm.jar'
BASE_SHA = '2fbfd8bc9c73b73ecfe42c7813ee3f121a30ab474e5398d24a79f09ac7eaf45f'
OUT = S / 'v5-bigstack.jar'
BUILD = S / 'v5-build'

android_jar = DEPS / 'android.jar'
d8_jar = DEPS / 'd8.jar'
smali_cp = ':'.join(str(p) for p in sorted(DEPS.glob('*.jar'))
                    if p.name not in ('android.jar', 'd8.jar') and not p.name.startswith('baseline'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
run = lambda a: subprocess.run([str(x) for x in a], check=True)

assert sha(BASE) == BASE_SHA, 'v4 base changed'
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
for p in (new_sm / 'adapter' / 'activity').glob('BigStackMain*.smali'):
    rel = str(p.relative_to(new_sm))
    assert rel not in original, 'collision: ' + rel
    shutil.copyfile(p, base_sm / rel)
    added.append(rel)
assert added

init = base_sm / 'com/android/internal/os/AppSpawnXInit.smali'
text = init.read_text()
start = text.index('.method private static invokeStaticMain(Ljava/lang/String;)V')
end = text.index('.end method', start)
body = text[start:end]
old = ('invoke-virtual {p0, v0, v1}, Ljava/lang/reflect/Method;->invoke('
       'Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;')
new = ('invoke-static {p0, v0, v1}, Ladapter/activity/BigStackMain;->invoke('
       'Ljava/lang/reflect/Method;Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;')
assert body.count(old) == 1, 'invoke site count=' + str(body.count(old))
assert 'J_invokeStaticMain_BEFORE_main_invoke' in body
init.write_text(text[:start] + body.replace(old, new) + text[end:])

run(['java', '-cp', smali_cp, 'org.jf.smali.Main', 'assemble', base_sm, '-o', BUILD / 'classes.dex'])
post = BUILD / 'post'
run(['java', '-cp', smali_cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'classes.dex', '-o', post])
changed = [n for n, d in original.items() if not (post / n).exists() or (post / n).read_bytes() != d]
if changed != ['com/android/internal/os/AppSpawnXInit.smali']:
    print('UNEXPECTED changed:', changed); sys.exit(1)
assert (post / 'com/android/internal/os/AppSpawnXInit.smali').read_text().count('BigStackMain;->invoke(') == 1

with zipfile.ZipFile(BASE) as src, zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as dst:
    for item in src.infolist():
        dst.writestr(item, (BUILD / 'classes.dex').read_bytes() if item.filename == 'classes.dex'
                     else src.read(item.filename))
print('base(v4)     :', BASE_SHA)
print('output       :', OUT)
print('output_sha256:', sha(OUT))
print('changed      :', changed)
print('added        :', added)
