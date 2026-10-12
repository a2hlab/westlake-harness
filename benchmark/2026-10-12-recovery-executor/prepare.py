#!/usr/bin/env python3
"""Refresh member bindings in a NEW package. Does not sign an approval or call devices."""
import argparse,hashlib,json,shutil
from pathlib import Path
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--startup-config');p.add_argument('--startup-config-sha256');a=p.parse_args()
out=Path(a.out);shutil.copytree(D,out,ignore=shutil.ignore_patterns('evidence','__pycache__','tests'))
plan=json.loads((D/'plan.disabled.json').read_text())
if a.startup_config:
 if sha(a.startup_config)!=a.startup_config_sha256:raise SystemExit('startup config explicit pin mismatch')
 shutil.copyfile(a.startup_config,out/'payload/startup.env')
 (out/'payload/startup.expected.sha256').write_text(a.startup_config_sha256+'\n')
# Approval alone does NOT execute anything. Outer must independently pin a JSON
# authorization to the complete resulting plan SHA and pass its SHA on the CLI.
plan['execution_enabled']=bool(a.startup_config)
for r in plan['members']:
 r['sha256']=sha(out/r['source'].removeprefix('$PACKAGE/'))
(out/'plan.disabled.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps({'plan_sha256':sha(out/'plan.disabled.json'),'device_calls':0,'startup_pin':a.startup_config_sha256,'execution_enabled':plan['execution_enabled']}))
