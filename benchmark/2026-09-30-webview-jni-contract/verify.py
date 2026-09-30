#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parents[1] / 'scripts/lab'))
import lab_paths

mode = {'exact': 'ExactDefinitions', 'pair': 'RealPair'}[sys.argv[1]]
python = lab_paths.inputs() / 'venv/bin/python'
subprocess.run([str(python), '-m', 'unittest', '-v', 'test_contract.' + mode], cwd=P, check=True)
