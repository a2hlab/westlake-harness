#!/usr/bin/env python3
"""Build temporary J3-based A/B probes, reusing the accepted B7 helper+smali recipe.

Run in a2hlab-b5-java via dockbuild. Production J3/J5, APKs and frozen sources untouched.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_SHA = '75c2068ca9818ea8a61cd2d7e258ef70b36fb426c87036f2f8e2c472d47e6697'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(args):
    subprocess.run([str(a) for a in args], check=True)


def instrument(tree):
    scheduler = tree / 'adapter/activity/AppSchedulerBridge.smali'
    text = scheduler.read_text()
    pat = r'(    invoke-static \{(v\d+)\}, Ladapter/activity/B7BindFixes;->apply\(Landroid/content/pm/ApplicationInfo;\)V)'
    assert len(re.findall(pat, text)) == 1, 'B7 apply call is not unique'
    text = re.sub(pat, lambda m: m[1] + '\n\n    invoke-static {' + m[2] + '}, Ladapter/diagnostics/U4Probe;->beforeBind(Ljava/lang/Object;)V', text)
    pat = r'(    invoke-static \{\}, Ladapter/activity/ActivityClientControllerAdapter;->getInstance\(\)Ladapter/activity/ActivityClientControllerAdapter;\n\n    move-result-object (v\d+)\n)'
    assert len(re.findall(pat, text)) == 1, 'launch controller acquisition not unique'
    text = re.sub(pat, lambda m: m[1] + '\n    invoke-static/range {' + m[2] + ' .. ' + m[2] + '}, Ladapter/diagnostics/U4Probe;->controller(Ljava/lang/Object;)Ljava/lang/Object;\n\n    move-result-object ' + m[2] + '\n\n    check-cast ' + m[2] + ', Landroid/app/IActivityClientController;\n', text)
    scheduler.write_text(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base', type=Path, required=True)
    ap.add_argument('--inputs', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    root = HERE.parents[2]
    run(['python3', root / 'scripts/lab/check_frozen.py', '--source-root', root])
    assert sha(a.base) == BASE_SHA, 'only pinned J3 is supported; J5 needs a fresh audit'
    a.out.mkdir(parents=True, exist_ok=False)
    cp = ':'.join(str(p) for p in sorted(a.inputs.glob('*.jar')) if p.name not in ('android.jar', 'd8.jar') and not p.name.startswith('baseline'))
    with zipfile.ZipFile(a.base) as z:
        assert len([n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n)]) == 1
        (a.out / 'base.dex').write_bytes(z.read('classes.dex'))
    original = a.out / 'original'
    run(['java', '-cp', cp, 'org.jf.baksmali.Main', 'disassemble', a.out / 'base.dex', '-o', original])
    norm = lambda x: re.sub(rb'(?m)^(\.field [^\n]*:Z) = false$', rb'\1', x)
    before = {str(p.relative_to(original)): norm(p.read_bytes()) for p in original.rglob('*.smali')}
    result = {'base_sha256': BASE_SHA, 'scope': 'diagnostic only; not U4', 'variants': {},
              'source_sha256': sha(HERE / 'U4Probe.java'),
              'inputs': {p.name: sha(p) for p in sorted(a.inputs.glob('*.jar'))},
              'java_version': subprocess.check_output(['java', '-version'], stderr=subprocess.STDOUT, text=True),
              'device_io': False}
    for variant in ['A-observe', 'B-app-theme']:
        out = a.out / variant; out.mkdir()
        tree = out / 'smali'; shutil.copytree(original, tree)
        classes = out / 'classes'; classes.mkdir()
        dex = out / 'helper-dex'; dex.mkdir()
        source = (HERE / 'U4Probe.java').read_text()
        if variant.startswith('B'):
            source = source.replace('CHANGE_APP_THEME = false;', 'CHANGE_APP_THEME = true;')
        src = out / 'U4Probe.java'; src.write_text(source)
        run(['javac', '--release', '8', '-d', classes, src])
        run(['java', '-cp', a.inputs / 'd8.jar', 'com.android.tools.r8.D8', '--release', '--min-api', '22',
             '--output', dex, *classes.rglob('*.class')])
        helpers = out / 'helpers'
        run(['java', '-cp', cp, 'org.jf.baksmali.Main', 'disassemble', dex / 'classes.dex', '-o', helpers])
        for p in helpers.rglob('*.smali'):
            dest = tree / p.relative_to(helpers); assert not dest.exists()
            dest.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, dest)
        instrument(tree)
        run(['java', '-cp', cp, 'org.jf.smali.Main', 'assemble', tree, '-o', out / 'classes.dex'])
        post = out / 'post'
        run(['java', '-cp', cp, 'org.jf.baksmali.Main', 'disassemble', out / 'classes.dex', '-o', post])
        after = {str(p.relative_to(post)): norm(p.read_bytes()) for p in post.rglob('*.smali')}
        changed = sorted(n for n, b in before.items() if after.get(n) != b)
        assert changed == ['adapter/activity/AppSchedulerBridge.smali'], changed
        assert sorted(set(after) - set(before)) == ['adapter/diagnostics/U4Probe.smali']
        jar = out / 'oh-adapter-runtime.jar'
        with zipfile.ZipFile(a.base) as source, zipfile.ZipFile(jar, 'w', zipfile.ZIP_DEFLATED) as dest:
            for item in source.infolist():
                dest.writestr(item, (out / 'classes.dex').read_bytes() if item.filename == 'classes.dex' else source.read(item.filename))
        result['variants'][variant] = {'jar': str(jar), 'sha256': sha(jar), 'changed_existing_classes': changed,
                                       'added_classes': ['adapter/diagnostics/U4Probe.smali']}
    result['device_verification'] = 'unknown'
    (a.out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result['variants'], indent=2))


if __name__ == '__main__':
    main()
