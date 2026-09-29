#!/usr/bin/env python3
"""Outer-reviewer helper: copy the verified candidate to a NEW local directory."""
import argparse,json,shutil
from pathlib import Path
from assemble import HERE,audit,load_package,pin,sha

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=json.loads((HERE/'results.json').read_text());source=Path(result['candidate']);out=a.out.resolve()
    if out.exists():raise ValueError('refuse existing destination: '+str(out))
    pin(source/'package.json',result['package_manifest_sha256']);audit(load_package(source))
    shutil.copytree(source,out)
    audit(load_package(out));pin(out/'package.json',result['package_manifest_sha256'])
    handoff=out/'handoff';handoff.mkdir(exist_ok=False)
    for item in HERE.iterdir():
        if item.is_file() and item.name!='.gitignore':shutil.copy2(item,handoff/item.name)
    for name in ['tools','evidence']:
        shutil.copytree(HERE/name,handoff/name,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    print(json.dumps(dict(output=str(out),package_sha256=sha(out/'package.json'),device_io=False,rollout_ready=False),indent=2))
if __name__=='__main__':main()
