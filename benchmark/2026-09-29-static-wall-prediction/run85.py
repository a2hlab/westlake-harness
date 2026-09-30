#!/usr/bin/env python3
"""Reproduce the frozen detector into a NEW directory, keeping released outputs intact."""
import argparse
from pathlib import Path
import scan85
p=argparse.ArgumentParser()
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
if a.out.exists() and any(a.out.iterdir()):p.error('--out must be empty or absent')
a.out.mkdir(parents=True,exist_ok=True)
(a.out/'protocol.json').write_bytes((scan85.OUT/'protocol.json').read_bytes())
scan85.OUT=a.out.resolve()
scan85.main()
