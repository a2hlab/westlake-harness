#!/usr/bin/env python3
"""Generate one exact wrapper successor without editing its frozen predecessor."""
import argparse,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE_SHA='f274b76304983f61b7e383f3eaaeb402ac2b0701f7d010d91c203295c28d3c08'
MARKER=b'# Explicit v2 staging; all existing v1 routes below remain byte-identical.\n'
def render(base):
    raw=Path(base).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=BASE_SHA:raise ValueError('wrapper predecessor SHA drift')
    if raw.count(MARKER)!=1:raise ValueError('wrapper insertion point drift')
    return raw.replace(MARKER,(HERE/'dispatch-block.sh.txt').read_bytes()+MARKER,1)
def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    data=render(a.base)
    with a.out.open('xb') as f:f.write(data)
    print(hashlib.sha256(data).hexdigest())
if __name__=='__main__':main()
