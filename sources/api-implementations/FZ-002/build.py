#!/usr/bin/env python3
"""Replay the two original compiler/link argv using the delivered candidate unit.
The restored generation supplies pinned dependencies; this never touches a device.
Relocated debug/source paths may change the output SHA. No equivalence is inferred.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--generation',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
here=Path(__file__).resolve().parent
cmds=json.loads((here/'build-evidence/original-commands.json').read_text())
old=cmds[0][0].split('/.work/product-tls-generation/')[0]
source=here/'src/child_main_after_stock.cpp'
original_source=cmds[0][cmds[0].index('-c')+1]; original_object=cmds[0][cmds[0].index('-o')+1]
assert a.generation.is_dir() and not a.out.exists()
new_object=str(a.out.resolve()/'child_main_after_stock.o'); output=str(a.out.resolve()/'libwestlake_android_runtime_provider.so')
def maparg(s):
    if s==original_source:return str(source)
    if s==original_object:return new_object
    return s.replace(old,str(a.generation.resolve()))
mapped=[[maparg(s) for s in cmd] for cmd in cmds]
mapped[1][mapped[1].index('-o')+1]=output
print(json.dumps({'argv':mapped,'executed':a.run},indent=2))
if a.run:
    a.out.mkdir(parents=True)
    for i,cmd in enumerate(mapped):
        with (a.out/('command-%d.stdout.txt'%i)).open('wb') as stdout,(a.out/('command-%d.stderr.txt'%i)).open('wb') as stderr:
            subprocess.run(cmd,cwd=a.generation,stdout=stdout,stderr=stderr,check=True)
    actual=hashlib.sha256(Path(output).read_bytes()).hexdigest()
    expected='0509fe235a7883b5cd9b57477221cb868465de944c6f70ed0cf2835b0fe4a97c'
    (a.out/'result.json').write_text(json.dumps({'sha256':actual,'frozen_sha256':expected,'byte_equal':actual==expected},indent=2)+'\n')
    if actual!=expected:raise SystemExit('built; frozen-byte identity not established (inspect recorded source paths)')
