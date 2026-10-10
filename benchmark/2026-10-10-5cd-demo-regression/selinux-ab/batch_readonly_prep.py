#!/usr/bin/env python3
"""Same demo adapter/icon clicks; no sandbox or private-library writes in SELinux A/B."""
import importlib.util, json
from pathlib import Path
P=Path(__file__).resolve().parents[2]/'2026-10-09-demo-baseline/t3/batch_adapter.py'
s=importlib.util.spec_from_file_location('demo_adapter',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def unchanged_sandbox(board,package,uid,out):
 receipt={'status':'not_modified','reason':'outer single-variable A/B prohibits sandbox mutation','package':package,'uid':uid}
 (out/'sandbox-preparation.json').write_text(json.dumps(receipt)+'\n');return receipt
def unchanged_sidecars(board,app,remote,out,record):
 record['native_assembly']={'status':'not_modified','reason':'outer A/B uses already-installed bytes; no sidecar staging'}
m.b.prepare_sandbox=unchanged_sandbox
m.b.assemble_native_sidecars=unchanged_sidecars
if __name__=='__main__':raise SystemExit(m.main())
