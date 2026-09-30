#!/usr/bin/env python3
import os
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import lab_paths

ws = lab_paths.workspaces()
env = dict(os.environ, DOCKBUILD_IMAGE='a2hlab-b5-java:24.04',
           DOCKBUILD_MOUNTS=str(ws / 'vm-copies/j3-75c2068c'))
args = ['python3', str(HERE / 'build.py'), '--base', str(ws / 'vm-copies/j3-75c2068c/oh-adapter-runtime.jar'),
        '--inputs', lab_paths.vm_home() + '/a2hlab/build-runs/20260929-oh6.1.0.31-b7/inputs',
        '--out', str(ROOT / 'bms/src/.work/u4-probes')]
subprocess.run([str(lab_paths.tools() / 'dockbuild.sh'), 'run', '-n', 'u4-offline-probes', '--', shlex.join(args)],
               cwd=ROOT, env=env, check=True)
