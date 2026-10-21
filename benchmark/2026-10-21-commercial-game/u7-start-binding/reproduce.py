#!/usr/bin/env python3
"""Call the exact original inherited start with no transport installed."""
import importlib.util,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root/'scripts/lab'))
source=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else root/'scripts/lab/u7_executor.py'
spec=importlib.util.spec_from_file_location('u7_original_reproduction',source);u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
io=u.DeviceIO.__new__(u.DeviceIO)
def forbidden(*args,**kwargs):raise AssertionError('Transport must never run')
io.shell=forbidden;io.ps=forbidden;io.hashes=forbidden
io.start('0'*64)
