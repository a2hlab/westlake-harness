#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
group = {'predictions': 'Predictions', 'commands': 'Commands', 'probes': 'Experiments'}[sys.argv[1]]
subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_plan.' + group], cwd=HERE, check=True)
