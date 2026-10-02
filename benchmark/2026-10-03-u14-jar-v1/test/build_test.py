#!/usr/bin/env python3
"""Build the host-ART harness jars (test-only, never deployed) with the pinned toolchain of build_u12.py:
    build/bind-order-test.jar   BindOrderAndroidTest (+ RecordingService)
    build/host-shim-v1.jar      android.util.Log + android.os.SystemClock without libandroid_runtime natives"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / '2026-10-02-u12-jar-plan'))
import build_u12 as r1  # noqa: E402

OUT = HERE.parent / 'build'


def dexjar(name, srcs):
    w = OUT / ('work-' + name)
    if w.exists():
        shutil.rmtree(w)
    (w / 'cls').mkdir(parents=True)
    (w / 'dex').mkdir()
    subprocess.run([r1.pinned_javac(), '-source', '8', '-target', '8', '-nowarn', '-cp', str(r1.AJ), '-d', str(w / 'cls'),
                    *map(str, srcs)], check=True)
    subprocess.run([str(r1.D8_JAVA), '-cp', str(r1.T / 'd8.jar'), 'com.android.tools.r8.D8', '--min-api', '28', '--lib',
                    str(r1.AJ), '--output', str(w / 'dex'), *map(str, sorted((w / 'cls').rglob('*.class')))], check=True)
    jar = OUT / name
    with zipfile.ZipFile(jar, 'w', zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo('classes.dex', (1980, 1, 1, 0, 0, 0))
        z.writestr(zi, (w / 'dex/classes.dex').read_bytes())
    shutil.rmtree(w)
    print(name, r1.sha(jar))


OUT.mkdir(exist_ok=True)
dexjar('bind-order-test.jar', [HERE / 'BindOrderAndroidTest.java'])
dexjar('host-shim-v1.jar', sorted((HERE / 'hostshim').rglob('*.java')))
