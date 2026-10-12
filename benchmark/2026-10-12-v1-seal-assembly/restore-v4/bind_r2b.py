#!/usr/bin/env python3
"""Bind t0 frozen r2b helper to actual disabled5cd control24 without board access."""
import hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=HERE.parents[3]
COMMIT='379d1a46de0c388e105157d455916d356c11028b'
REL='benchmark/2026-10-12-child-readiness/r2b-quiet-reset'
T0=WS/'westlake-harness-t0'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 manifest=T0/REL/'checkpoint-manifest.json'
 blob=subprocess.check_output(['git','show',COMMIT+':'+REL+'/checkpoint-manifest.json'],cwd=T0)
 assert hashlib.sha256(blob).hexdigest()==sha(manifest)
 j=json.loads(blob)
 for row in j['files']:
  path=manifest.parent/row['path'];assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
 b=json.loads((HERE/'binding.5cd.disabled.json').read_text());assert b['startup_enabled'] is False
 b['guardian_update']={'path':'$WORKSPACES/'+str(manifest.relative_to(WS)),'sha256':sha(manifest)}
 b['observation_provenance']['t9_r2b']={'commit':COMMIT,'checkpoint':b['guardian_update'],
    'helper_sha256':sha(manifest.parent/'candidate/route-b-owner.sh'),
    'scope':'helper quiet discovery and load reset0 only; measured control24 base unchanged; no donor authorization'}
 out=HERE/'binding.5cd.r2b.disabled.json'
 with out.open('x') as f:json.dump(b,f,indent=2);f.write('\n')
 print(json.dumps({'status':'R2B_DISABLED_BOUND','manifest_sha256':sha(manifest),'binding_sha256':sha(out),'device_calls':0}))
if __name__=='__main__':main()
