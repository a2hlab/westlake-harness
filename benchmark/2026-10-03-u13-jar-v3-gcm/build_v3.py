#!/usr/bin/env python3
"""U13 JAR v3 = U13 JAR v2 506abe23 with adapter.core.GcmDefaultNonce rebuilt from src/ (the only change).

    build_v3.py

Same pinned toolchain as build_u12.py (javac pinned, d8 on openjdk@17, baksmali/smali 2.5.2, `smali -j 1`, fixed zip
time). The base jar is disassembled, every adapter/core/GcmDefaultNonce*.smali is removed, the rebuilt class family
is added, and the result reassembled; no other smali file is touched (checked: every other file is byte-identical
to the base disassembly). Built twice; the jars must be byte-identical.
"""
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-02-own-provider-local'))
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import lab_paths  # noqa: E402
from build_u11j import BAK_CP, SMALI_CP, AJ, D8_JAVA, T, pinned_javac, sha, run  # noqa: E402

BASE = lab_paths.inputs() / 'generations/u13-jar-v2/oh-adapter-runtime-u13-v2.jar'
BASE_SHA = '506abe23dd08'
SRC = HERE / 'src/adapter/core/GcmDefaultNonce.java'
FAMILY = 'adapter/core/GcmDefaultNonce'
OUT = HERE / 'build/oh-adapter-runtime-u13-v3.jar'


def build(work, out):
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    bj = work / 'basejar'
    with zipfile.ZipFile(BASE) as z:
        z.extractall(bj)
    base = work / 'smali'
    run(['java', '-cp', BAK_CP, 'org.jf.baksmali.Main', 'disassemble', bj / 'classes.dex', '-o', base])
    before = {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*.smali')}
    removed = sorted(r for r in before if r.startswith(FAMILY) and r[len(FAMILY):len(FAMILY) + 1] in ('.', '$'))
    for r in removed:
        (base / r).unlink()
    cc = work / 'classes'
    cc.mkdir()
    run([pinned_javac(), '-source', '8', '-target', '8', '-nowarn', '-cp', AJ, '-d', cc, SRC])
    dd = work / 'dex'
    dd.mkdir()
    run([D8_JAVA, '-cp', T / 'd8.jar', 'com.android.tools.r8.D8', '--min-api', '28', '--lib', AJ,
         '--output', dd, *sorted(cc.rglob('*.class'))])
    js = work / 'js'
    run(['java', '-cp', BAK_CP, 'org.jf.baksmali.Main', 'disassemble', dd / 'classes.dex', '-o', js])
    added = []
    for p in sorted(js.rglob('*.smali')):
        rel = str(p.relative_to(js))
        assert rel.startswith(FAMILY), f'{rel}: outside the GcmDefaultNonce family'
        shutil.copy2(p, base / rel)
        added.append(rel)
    after = {str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest() for p in base.rglob('*.smali')}
    others = {r for r in before if r not in removed}
    assert all(after.get(r) == before[r] for r in others), 'a smali file outside the family changed'
    assert set(after) - others == set(added), 'unexpected files'
    outdex = work / 'classes.dex'
    run(['java', '-cp', SMALI_CP, 'org.jf.smali.Main', 'assemble', '-j', '1', base, '-o', outdex])
    man = (bj / 'META-INF/MANIFEST.MF').read_bytes()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for nm, data in (('META-INF/MANIFEST.MF', man), ('classes.dex', outdex.read_bytes())):
            zi = zipfile.ZipInfo(nm, (1980, 1, 1, 0, 0, 0))
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
    return sha(out), removed, added


def main():
    b = sha(BASE)
    assert b.startswith(BASE_SHA), f'base is not U13 JAR v2 506abe23: {b}'
    s1, removed, added = build(HERE / 'build/w1', OUT)
    s2, _, _ = build(HERE / 'build/w2', HERE / 'build/check.jar')
    (HERE / 'build/check.jar').unlink()
    for w in ('w1', 'w2'):
        shutil.rmtree(HERE / 'build' / w)
    print('removed:', ', '.join(removed))
    print('added:  ', ', '.join(added))
    print('sha256', s1, 'DETERMINISTIC', 'YES' if s1 == s2 else 'NO ' + s2)
    return 0 if s1 == s2 else 1


if __name__ == '__main__':
    sys.exit(main())
