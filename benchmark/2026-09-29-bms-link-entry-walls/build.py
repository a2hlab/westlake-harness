"""Run via dockbuild (a2hlab-b5-java image): B7 helper merge into 5cd's accepted runtime JAR.

Same method as B5 (alias-entry/build.py): compile the helpers, baksmali the pinned
baseline, add the helper classes, inject exactly one call, reassemble, and prove
that no other existing class changed.
"""
from pathlib import Path
import hashlib, json, re, shutil, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(__file__).resolve().parent
OUT = Path('/home/zhaoyue/a2hlab/build-runs/20260929-oh6.1.0.31-b7')
INPUT = OUT / 'inputs'
BUILD = OUT / ('build-' + (sys.argv[1] if len(sys.argv) > 1 else 'r1'))
BUILD.mkdir(exist_ok=False)
# pr03: 5cd before the #63 generation switch; zigzag: the 5ea/ZigZag candidate generation
# (strict-20260809T160651Z-21101), which already ships User/Storage/Display projection proxies.
BASELINES = {'pr03': ('baseline.jar', '06141543bec26c5036931d8d2d71b0efaa45d5ffd73434557d165cd42672be0d'),
             'zigzag': ('baseline-9161b507.jar', '9161b50756d3ffdfb2a8908ea7ec13f908214688321b2785365977ac40b28dea')}
BASE_NAME = sys.argv[2] if len(sys.argv) > 2 else 'pr03'
BASE_JAR = INPUT / BASELINES[BASE_NAME][0]
BASELINE = BASELINES[BASE_NAME][1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(BASE_JAR) == BASELINE
cp = ':'.join(str(p) for p in sorted(INPUT.glob('*.jar')) if p.name not in ('android.jar', 'd8.jar') and not p.name.startswith('baseline'))


def run(args):
    subprocess.run([str(x) for x in args], check=True)


classes = BUILD / 'classes'; classes.mkdir()
dex = BUILD / 'helper-dex'; dex.mkdir()
src = ROOT / 'bms/src/adapter/framework/activity/java'
helpers_src = [src / 'B7BindFixes.java', src / 'UserManagerProjectionProxy.java',
               # B5 alias fix, verbatim sources (alias-entry/build.py): 5cd never carried the
               # B5 JAR (built on the ZigZag-generation 9161b507), so it rides on this overlay.
               src / 'LaunchActivityAliasProjection.java', src / 'BinaryAndroidManifestOrientation.java']
run(['javac', '--release', '8', '-cp', INPUT / 'android.jar', '-d', classes, *helpers_src])
run(['java', '-cp', INPUT / 'd8.jar', 'com.android.tools.r8.D8', '--release', '--min-api', '22',
     '--lib', INPUT / 'android.jar', '--output', dex, *classes.rglob('*.class')])
with zipfile.ZipFile(BASE_JAR) as z:
    (BUILD / 'baseline.dex').write_bytes(z.read('classes.dex'))
smali, helpers, post = BUILD / 'smali', BUILD / 'helper-smali', BUILD / 'postflight'
run(['java', '-cp', cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'baseline.dex', '-o', smali])
original = {str(p.relative_to(smali)): p.read_bytes() for p in smali.rglob('*.smali')}
run(['java', '-cp', cp, 'org.jf.baksmali.Main', 'disassemble', dex / 'classes.dex', '-o', helpers])
# A helper the baseline already ships (UserManagerProjectionProxy on zigzag) is compiled only so
# B7BindFixes links against it; the baseline's own class is kept.
ALREADY_SHIPPED = {'adapter/activity/UserManagerProjectionProxy.smali',
                   'adapter/activity/UserManagerProjectionProxy$UserBinder.smali'}
for p in helpers.rglob('*.smali'):
    dest = smali / p.relative_to(helpers)
    if str(p.relative_to(helpers)) in original:
        assert str(p.relative_to(helpers)) in ALREADY_SHIPPED, p
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)

# ensureBindApplication: right after "[B43-BIND] resolved ApplicationInfo ..." is printed,
# v10 holds the ApplicationInfo that becomes AppBindData.appInfo.
scheduler = smali / 'adapter/activity/AppSchedulerBridge.smali'
text = scheduler.read_text()
start = text.index('.method private static declared-synchronized ensureBindApplication(')
end = text.index('.end method', start)
body = text[start:end]
anchor = ('invoke-virtual {v8, v0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V\n\n'
          '    .line 201\n')
assert body.count(anchor) == 1, body.count(anchor)
assert 'iget-object v4, v10, Landroid/content/pm/ApplicationInfo;->nativeLibraryDir' in body
call = ('invoke-virtual {v8, v0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V\n\n'
        '    invoke-static {v10}, Ladapter/activity/B7BindFixes;->apply(Landroid/content/pm/ApplicationInfo;)V\n\n'
        '    .line 201\n')
text = text[:start] + body.replace(anchor, call) + text[end:]
# B5: exactly one call after buildActivityInfoFromAbility, same pattern as alias-entry/build.py.
pattern = r'(?m)(^    invoke-static[^\n]*->buildActivityInfoFromAbility\([^\n]+\n\s*\n?    move-result-object ([vp]\d+))'
hits = list(re.finditer(pattern, text)); assert len(hits) == 1, len(hits)
h = hits[0]
text = (text[:h.end()] + '\n\n    invoke-static {' + h[2] +
        '}, Ladapter/activity/LaunchActivityAliasProjection;->apply(Landroid/content/pm/ActivityInfo;)V' + text[h.end():])
scheduler.write_text(text)

run(['java', '-cp', cp, 'org.jf.smali.Main', 'assemble', smali, '-o', BUILD / 'classes.dex'])
run(['java', '-cp', cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'classes.dex', '-o', post])
# smali drops an explicit "= false" static-boolean initializer (the encoded default);
# that is the only round-trip difference tolerated.
norm = lambda b: re.sub(rb'(?m)^(\.field [^\n]*:Z) = false$', rb'\1', b)
changed = [n for n, d in original.items()
           if not (post / n).exists() or norm((post / n).read_bytes()) != norm(d)]
assert changed == ['adapter/activity/AppSchedulerBridge.smali'], changed
post_scheduler = (post / 'adapter/activity/AppSchedulerBridge.smali').read_text()
assert post_scheduler.count('B7BindFixes;->apply(') == 1
assert post_scheduler.count('LaunchActivityAliasProjection;->apply(') == 1
output = BUILD / 'oh-adapter-runtime.jar'
with zipfile.ZipFile(BASE_JAR) as source, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as dest:
    for item in source.infolist():
        dest.writestr(item, (BUILD / 'classes.dex').read_bytes() if item.filename == 'classes.dex'
                      else source.read(item.filename))
result = {
    'baseline': BASE_NAME,
    'baseline_sha256': BASELINE,
    'output': str(output),
    'output_sha256': sha(output),
    'changed_existing_classes': changed,
    'added_classes': sorted(str(p.relative_to(post)) for p in post.rglob('*.smali')
                            if str(p.relative_to(post)) not in original),
    'sources': {str(p.relative_to(ROOT)): sha(p) for p in helpers_src},
    'inputs': {p.name: sha(p) for p in sorted(INPUT.glob('*.jar'))},
}
(REPORT / 'build-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
