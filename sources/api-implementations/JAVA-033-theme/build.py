#!/usr/bin/env python3
"""Rebuild the J10d theme overlay from the preserved Java source and pinned J10 input."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', required=True, type=Path)
    p.add_argument('--baseline', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--javac', required=True, type=Path)
    p.add_argument('--java', required=True, type=Path, help='Java 11 or newer for D8')
    a = p.parse_args()
    lock = json.loads((HERE / 'source.lock.json').read_text())
    deps = json.loads((ROOT / lock['input_dependencies_lock']).read_text())
    for source in lock['sources']:
        assert sha(ROOT / source['path']) == source['sha256'], 'source changed'
    assert sha(a.baseline) == lock['baseline_sha256'], 'wrong J10 baseline'
    required = {'android.jar', 'baksmali-2.5.2.jar', 'dexlib2-2.5.2.jar', 'guava-27.1-android.jar',
                'jcommander-1.64.jar', 'util-2.5.2.jar', 'smali-2.5.2.jar',
                'antlr-runtime-3.5.2.jar', 'stringtemplate-3.2.1.jar', 'd8.jar'}
    assert required <= {d['name'] for d in deps['files']}, 'incomplete dependency lock'
    for dep in [d for d in deps['files'] if d['name'] in required]:
        assert sha(a.inputs / dep['name']) == dep['sha256'], 'dependency changed: ' + dep['name']
    a.out.mkdir(parents=True, exist_ok=False)
    receipt = {'schema': 'j10d-source-rebuild/v1', 'commands': [],
               'historical_build_log_recovered': False,
               'toolchain': {k: {'sha256': sha(v.resolve()), 'name': v.name}
                             for k, v in [('javac', a.javac), ('java', a.java)]},
               'baseline_sha256': sha(a.baseline), 'source_lock_sha256': sha(HERE / 'source.lock.json')}

    def portable(value):
        text = str(value)
        for actual, token in [(a.out, '$OUT'), (a.inputs, '$INPUTS'), (a.baseline, '$BASELINE'),
                              (a.javac, '$JAVAC'), (a.java, '$JAVA'), (ROOT, '$REPO')]:
            text = text.replace(str(actual), token)
        return text

    def run(argv):
        argv = [str(x) for x in argv]
        n = len(receipt['commands'])
        out, err = a.out / f'{n:02}.stdout.txt', a.out / f'{n:02}.stderr.txt'
        with out.open('wb') as stdout, err.open('wb') as stderr:
            proc = subprocess.run(argv, stdout=stdout, stderr=stderr)
        receipt['commands'].append({'argv': [portable(x) for x in argv], 'rc': proc.returncode,
                                    'stdout': {'file': out.name, 'sha256': sha(out)},
                                    'stderr': {'file': err.name, 'sha256': sha(err)}})
        assert proc.returncode == 0, 'command failed; raw logs preserved'

    try:
        run([a.javac, '-version'])
        run([a.java, '-version'])
        libs = ['baksmali-2.5.2.jar', 'dexlib2-2.5.2.jar', 'guava-27.1-android.jar',
                'jcommander-1.64.jar', 'util-2.5.2.jar']
        bakcp = ':'.join(str(a.inputs / x) for x in libs)
        smalicp = ':'.join(str(a.inputs / x) for x in
                           ['smali-2.5.2.jar', *libs[1:], 'antlr-runtime-3.5.2.jar', 'stringtemplate-3.2.1.jar'])
        with zipfile.ZipFile(a.baseline) as z:
            (a.out / 'baseline.dex').write_bytes(z.read('classes.dex'))
            manifest = z.read('META-INF/MANIFEST.MF')
        smali = a.out / 'smali'
        run([a.java, '-cp', bakcp, 'org.jf.baksmali.Main', 'disassemble', a.out / 'baseline.dex', '-o', smali])
        classes = a.out / 'classes'
        classes.mkdir()
        # Compile against the exact helper signature. Its implementation is already in J10;
        # this compile-only declaration is never converted to DEX or put in the output JAR.
        decl = a.out / 'compile-only/adapter/activity/ManifestJsonFallback.java'
        decl.parent.mkdir(parents=True)
        decl.write_text('package adapter.activity; final class ManifestJsonFallback {\n'
                        'static int activityTheme(String pkg, String name) throws Exception { return 0; }\n}\n')
        run([a.javac, '-source', '8', '-target', '8', '-cp', a.inputs / 'android.jar',
             '-d', classes, ROOT / lock['sources'][0]['path'], decl])
        dex = a.out / 'unit-dex'
        dex.mkdir()
        # The helper is a compile dependency already present in the J10 baseline.
        run([a.java, '-cp', a.inputs / 'd8.jar', 'com.android.tools.r8.D8', '--min-api', '28',
             '--lib', a.inputs / 'android.jar', '--output', dex, classes / 'adapter/activity/J10dTheme.class'])
        new = a.out / 'unit-smali'
        run([a.java, '-cp', bakcp, 'org.jf.baksmali.Main', 'disassemble', dex / 'classes.dex', '-o', new])
        target = smali / 'adapter/activity/J10dTheme.smali'
        assert not target.exists(), 'baseline already contains J10d'
        shutil.copy2(new / 'adapter/activity/J10dTheme.smali', target)
        caller = smali / 'adapter/activity/AppSchedulerBridge.smali'
        text = caller.read_text()
        needle = '    iput v15, v4, Landroid/content/pm/ActivityInfo;->banner:I\n'
        assert text.count(needle) == 1, 'historical injection site not unique'
        caller.write_text(text.replace(needle, needle +
                          '    invoke-static {v4}, Ladapter/activity/J10dTheme;->restore(Landroid/content/pm/ActivityInfo;)V\n'))
        run([a.java, '-cp', smalicp, 'org.jf.smali.Main', 'assemble', '-j', '1', smali, '-o', a.out / 'classes.dex'])
        output = a.out / 'oh-adapter-runtime-j10d.jar'
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, data in [('META-INF/MANIFEST.MF', manifest), ('classes.dex', (a.out / 'classes.dex').read_bytes())]:
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
        receipt['output'] = {'sha256': sha(output), 'classes_dex_sha256': sha(a.out / 'classes.dex')}
        receipt['historical_jar_equal'] = sha(output) == lock['historical_jar_sha256']
        receipt['rc'] = 0 if receipt['historical_jar_equal'] else 2
        receipt['status'] = 'EXACT_HISTORICAL_JAR_MATCH' if receipt['historical_jar_equal'] else 'BUILD_SUCCEEDED_HISTORICAL_BYTES_DIFFER'
    except (AssertionError, OSError, KeyError, zipfile.BadZipFile) as exc:
        receipt.update(rc=2, status='REJECT', error=portable(exc))
    (a.out / 'execution.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'rc': receipt['rc']}))
    return receipt['rc']


if __name__ == '__main__':
    raise SystemExit(main())
