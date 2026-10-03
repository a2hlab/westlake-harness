"""Proposed pre-lock wrapper. Current candidate refuses offline, before even VM/USB reads."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import shlex

H = Path(__file__).resolve().parent
R = H.parents[1]
sys.path.insert(0, str(H))
sys.path.insert(0, str(R.parent / 'westlake-harness/scripts/lab'))
import board_run
import lab_paths
import promotion_hook_u14_runtime as hook


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
        'python3', '-c', script, str(workspaces), str(hook.path(hook.composition()["package"]))],
        timeout=60, check=True, capture_output=True, text=True)
    report = json.loads(result.stdout)
    if report.get('status') != 'PASS':
        raise RuntimeError('VM tool readiness refused before LOCK')
    return report


def remote_oatdump_preflight():
    # LAB_HOME names the hw248 frozen tool tree, not the OrbStack user's home.
    prefix = os.environ.get('LAB_HOME')
    if not prefix:
        raise RuntimeError('LAB_HOME missing: frozen remote oatdump cannot be located')
    target = os.environ.get('OATDUMP', prefix+'/aosp-14.0.0_r1-art/out/host/linux-x86/bin/oatdump')
    remote = subprocess.run(['ssh', os.environ.get('HW248','hw248'),
        'test -x '+shlex.quote(target)], timeout=20, capture_output=True, text=True)
    if remote.returncode:
        raise RuntimeError('remote frozen oatdump is not executable at LAB_HOME: refuse before LOCK')
    return {'status':'PASS','tool':'$LAB_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/oatdump'}


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
    if plan.get('phase') != 'B':
        raise RuntimeError('unknown window phase')
    hook.require_enabled()
    hook.validate_plan(plan)
    hook.stage_a_admission(hook.path(plan.get('stage_a_decision', '')))
    hook.admission()
    w = lab_paths.workspaces()
    rss = subprocess.run(['ps', '-axo', 'rss=,comm='], capture_output=True, text=True, check=True)
    vmgr_kib = sum(int(line.split(None,1)[0]) for line in rss.stdout.splitlines() if 'vmgr' in line or 'OrbStack Helper.app/Contents/MacOS/OrbStack Helper' in line)
    if vmgr_kib > 3*1024*1024:
        raise RuntimeError('vmgr RSS >3GiB: preventive RUNBOOK restart required before LOCK')
    start = time.monotonic()
    subprocess.run(['orb', '-m', 'a2hlab', 'true'], timeout=25, check=True)
    orb_latency = time.monotonic()-start
    # These paths must be the Mac workspace bind inside the VM, not a private stale copy.
    check = ['orb', '-m', 'a2hlab', 'python3', '-c',
             'import hashlib,pathlib,sys; p=pathlib.Path(sys.argv[1]); assert p.is_file(); assert hashlib.sha256(p.read_bytes()).hexdigest()==sys.argv[2]',
             str(hook.path(hook.composition()["package"]) / 'bundle.json'), hook.gb.sha(hook.path(hook.composition()["package"]) / 'bundle.json')]
    subprocess.run(check, timeout=25, check=True)
    tool_report = vm_tools_preflight(w)
    remote_report = remote_oatdump_preflight()
    hdc = subprocess.run(['orb', '-m', 'a2hlab', 'bash', str(lab_paths.tools() / 'hdc_mac.sh'), 'list', 'targets'], timeout=25, check=True, capture_output=True, text=True)
    if plan['serial'] not in hdc.stdout.split():
        raise RuntimeError('serial absent from HDC targets; no lock taken')
    held = subprocess.run(['bash', str(lab_paths.tools()/'board_note.sh'), 'held', plan['serial']], capture_output=True, text=True, timeout=15)
    if held.stdout.strip():
        raise RuntimeError('board held; no lock taken: '+held.stdout.strip())
    return {'vmgr_rss_kib':vmgr_kib,'orb_latency_seconds':orb_latency,'orb': 'PASS', 'workspace_bind_sha': 'PASS', 'vm_tools': tool_report, 'remote_oatdump':remote_report, 'hdc_serial': plan['serial']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('plan', type=Path)
    parser.add_argument('--detach', action='store_true', required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    report = prelock(plan)
    destination = args.plan.parent / (args.plan.stem+'-prelock.json')
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report), flush=True)
    subprocess.run([sys.executable, str(lab_paths.harness() / 'scripts/lab/board_run.py'), str(args.plan.resolve()), '--detach'], check=True)


if __name__ == '__main__':
    main()
