"""Dispatch one approved plan using the reviewed pre-lock and detached runner."""
from pathlib import Path
import os,re,subprocess,sys,json
H=Path(__file__).resolve().parent;W=H.parents[3]
env=dict(os.environ,WORKSPACES=str(W),MAC_HOME=str(Path.home()),LAB_HOME=re.search(r'hw248:([^\s,]+?)/aosp-14\.0\.0_r1-art',(W/'westlake-inputs/aosp-14.0.0_r1-src/SOURCE.txt').read_text()).group(1))
board=sys.argv[1];assert board in {'5ea','5cd','61b'}
receipt=json.loads((H/'infra-prelock-final.json').read_text())
assert receipt['orb_rc']==0 and receipt['rss_kib'] is not None and not receipt['restart_required'],'infrastructure RSS/readiness gate refused before LOCK'
composition=json.loads((H/'composition.json').read_text())
for surface in ('mac','vm'):
 gate=json.loads((H/('gate-'+surface+'-pass.json')).read_text())
 assert gate['deployable'] and gate['gates_passed'] and gate['production_dry_run_exit_code']==0
 assert gate['bundle_sha256']==composition['bundle_sha256'] and gate['native_manifest_sha256']==composition['native_manifest_sha256'],'production gate belongs to a different package'
p=subprocess.run([sys.executable,H/'runner.py','dispatch',H/('plan-'+board+'.json'),'--detach'],env=env)
raise SystemExit(p.returncode)
