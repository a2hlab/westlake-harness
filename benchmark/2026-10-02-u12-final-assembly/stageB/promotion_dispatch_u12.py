"""Proposed pre-lock wrapper. Current candidate refuses offline, before even VM/USB reads."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

H = Path(__file__).resolve().parent
R = H.parents[2]
sys.path.insert(0, str(H))
sys.path.insert(0, str(R / 'scripts/lab'))
import board_run
import lab_paths
import promotion_hook_u12 as hook


def vm_tools_preflight(workspaces):
    """Exercise the production VM tools and Mac-visible DEX scratch before LOCK."""
    script = '''
import json, os, pathlib, shutil, subprocess, sys, tempfile, zipfile
root = pathlib.Path(sys.argv[1]) / 'westlake-harness'
tools = root / 'benchmark/2026-10-01-u7-executor/.vm-tools'
scratch = root / 'benchmark/2026-10-01-u7-executor/.vm-tmp'
assert scratch.is_dir() and os.access(scratch, os.W_OK), 'shared VM scratch unavailable'
os.environ['PATH'] = str(tools) + ':' + os.environ['PATH']
os.environ['TMPDIR'] = str(scratch)
package = pathlib.Path(sys.argv[2])
required = ('dexdump', 'llvm-nm', 'llvm-objdump', 'llvm-readelf', 'readelf')
resolved = {name: shutil.which(name) for name in required}
assert all(resolved.values()), 'missing VM tool: ' + str(resolved)
with tempfile.TemporaryDirectory(dir=scratch) as directory:
    jar = next(package.rglob('oh-adapter-runtime.jar'))
    with zipfile.ZipFile(jar) as archive:
        dex = pathlib.Path(directory) / 'probe.dex'
        dex.write_bytes(archive.read('classes.dex'))
    subprocess.run(['dexdump', '-f', str(dex)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=15)
for name in required[1:]:
    subprocess.run([name, '--version'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=10)
print(json.dumps({'status': 'PASS', 'tools': resolved, 'shared_dex_read': 'PASS'}))
'''
    result = subprocess.run(['orb', '-m', 'a2hlab', 'env',
        'MAC_HOME=' + os.environ.get('MAC_HOME', str(Path.home())),
        'python3', '-c', script, str(workspaces), str(hook.CANDIDATE)],
        timeout=60, check=True, capture_output=True, text=True)
    report = json.loads(result.stdout)
    if report.get('status') != 'PASS':
        raise RuntimeError('VM tool readiness refused before LOCK')
    return report


def prelock(plan):
    problem = board_run.precheck_problem(plan.get('offline_precheck'))
    if problem:
        raise RuntimeError('REFUSE before infra or LOCK: ' + problem)
    if plan.get('execution_enabled') is not True:
        raise RuntimeError('REVIEW-ONLY plan is not executable')
    composition = json.loads((H / 'composition.json').read_text())
    if (plan.get('bundle_sha256') != composition['bundle_sha256'] or
            plan.get('package_manifest_sha256') != composition['native_manifest_sha256']):
        raise RuntimeError('plan/package SHA drift; rebind approved plans before LOCK')
    if plan.get('phase') == 'B':
        hook.stage_a_admission(Path(os.path.expandvars(plan['stage_a_decision'])))
    elif plan.get('phase') != 'A':
        raise RuntimeError('unknown window phase')
    hook.admission()
    w = lab_paths.workspaces()
    subprocess.run(['orb', '-m', 'a2hlab', 'true'], timeout=25, check=True)
    # These paths must be the Mac workspace bind inside the VM, not a private stale copy.
    check = ['orb', '-m', 'a2hlab', 'python3', '-c',
             'import hashlib,pathlib,sys; p=pathlib.Path(sys.argv[1]); assert p.is_file(); assert hashlib.sha256(p.read_bytes()).hexdigest()==sys.argv[2]',
             str(hook.CANDIDATE / 'bundle.json'), hook.gb.sha(hook.CANDIDATE / 'bundle.json')]
    subprocess.run(check, timeout=25, check=True)
    tool_report = vm_tools_preflight(w)
    hdc = subprocess.run(['orb', '-m', 'a2hlab', 'bash', str(lab_paths.tools() / 'hdc_mac.sh'), 'list', 'targets'], timeout=25, check=True, capture_output=True, text=True)
    if plan['serial'] not in hdc.stdout.split():
        raise RuntimeError('serial absent from HDC targets; no lock taken')
    return {'orb': 'PASS', 'workspace_bind_sha': 'PASS', 'vm_tools': tool_report, 'hdc_serial': plan['serial']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('plan', type=Path)
    parser.add_argument('--detach', action='store_true', required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    prelock(plan)
    subprocess.run([sys.executable, str(lab_paths.harness() / 'scripts/lab/board_run.py'), str(args.plan.resolve()), '--detach'], check=True)


if __name__ == '__main__':
    main()
