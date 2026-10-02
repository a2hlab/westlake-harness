#!/usr/bin/env python3
"""Build build/nsd-test.jar (test-only) with the pinned javac / d8 of build_u12.py, against android-34 android.jar."""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / '2026-10-02-u12-jar-plan'))  # the u12 recipe (pinned javac/d8)
import build_u12 as r1  # noqa: E402

w = HERE.parent / 'build/work-test'
if w.exists():
    shutil.rmtree(w)
(w / 'cls').mkdir(parents=True)
(w / 'dex').mkdir()
subprocess.run([r1.pinned_javac(), '-source', '8', '-target', '8', '-nowarn', '-cp', str(r1.AJ), '-d', str(w / 'cls'),
                str(HERE / 'NsdTest.java')], check=True)
subprocess.run([str(r1.D8_JAVA), '-cp', str(r1.T / 'd8.jar'), 'com.android.tools.r8.D8', '--min-api', '28', '--lib',
                str(r1.AJ), '--output', str(w / 'dex'), *map(str, sorted((w / 'cls').rglob('*.class')))], check=True)
out = HERE.parent / 'build/nsd-test.jar'
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr(zipfile.ZipInfo('classes.dex', (1980, 1, 1, 0, 0, 0)), (w / 'dex/classes.dex').read_bytes())
shutil.rmtree(w)
print(out.name, r1.sha(out))
