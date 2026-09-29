#!/usr/bin/env python3
"""Create an absent-only gapfill addition from the board's actual resident package."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from prepare_generation_replacement import prepare
from deploy_generation import sha
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('resident_package',type=Path);p.add_argument('output',type=Path)
a=p.parse_args();m=json.loads((ROOT/'artifact.json').read_text())
for name,digest in m['tool_sha256'].items():
    if sha(ROOT/name)!=digest:raise ValueError('tool SHA mismatch: '+name)
print(prepare(a.resident_package.resolve(),m['target'],ROOT/m['file'],m['sha256'],a.output.resolve(),adding=True))
