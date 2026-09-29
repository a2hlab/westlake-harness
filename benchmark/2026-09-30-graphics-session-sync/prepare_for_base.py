#!/usr/bin/env python3
"""Rebase the graphics runtime onto an explicitly supplied active package; no board IO."""
import argparse,importlib.util
from pathlib import Path
import sys
r=Path(__file__).resolve().parent
repo=r.parents[1]
sys.path.insert(0,str(repo/'scripts/lab'))
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('base',type=Path);p.add_argument('out',type=Path)
a=p.parse_args()
spec=importlib.util.spec_from_file_location('prepare_graphics_base', '/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate/handoff/tools/prepare_generation_replacement.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=Path('/Users/zhaoyue/orca/workspaces/westlake-runtime-graphics-session-sync-32dfac83/payload/android/lib64/liboh_android_runtime.so')
print(m.prepare(a.base.resolve(),'/system/android/lib64/liboh_android_runtime.so',source,'32dfac830320394d0b62781afcde68537d3b5fff372b5170d7a53baa069013b7',a.out.resolve()))
