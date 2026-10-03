#!/usr/bin/env python3
"""runtime-fingerprint.txt for one board, computed by bms_batch's own runtime_fingerprint (same paths, same hash).

    fingerprint.py <serial> <out dir> <file name>   -> prints 'RUNTIME fingerprint=<12> files=N'
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'benchmark/2026-09-28-bms-route-deploy/batch'))
sys.path.insert(0, str(REPO / 'scripts/lab'))
import bms_batch  # noqa: E402


class Hdc:
    def __init__(self, serial):
        self.serial = serial

    def shell(self, command, required=True, timeout=60):
        p = subprocess.run(['hdc', '-t', self.serial, 'shell', command], capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout


serial, out, name = sys.argv[1:4]
short = bms_batch.runtime_fingerprint(Hdc(serial), out, name=name)
n = len((Path(out) / name).read_text().split('\n')) - 1
print(f'RUNTIME fingerprint={short} files={n}')
sys.exit(0 if short else 1)
