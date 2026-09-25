"""Exercise actual pinned artifacts in a new local VM fixture, never HDC."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import apply_all_fixes as apply

def inventory(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}

def main():
    ws = Path.home()/'a2hlab/ws'
    base = ws/'out-recipe46'; base.mkdir(exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix='smoke-', dir=base))
    stage = fixture/'runtime'; stage.mkdir()
    evidence = Path.home()/'a2hlab/board/5ea34a4500000000000000001123012c/ability38/mc46-verification'
    sources = {
        'webview-t-lib/libwebview_bionic_shim.so': ws/'out-wv46/repro/libwebview_bionic_shim.so',
        'liboh_adapter_bridge.so': evidence/'original-bridge.so',
        'lib/arm64-v8a/libnpth.so': evidence/'original-npth.so',
        'run.sh': evidence/'pre-tt-run.sh',
    }
    for name, path in sources.items():
        target = stage/name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(path, target)
    (stage/'unrelated.keep').write_bytes(b'preserve app data and other libraries\n')
    before = inventory(stage)
    command = ['bash', str(apply.HERE/'apply_all_fixes.sh'), str(stage), '--workspace', str(ws)]
    dry = subprocess.check_output(command+['--dry-run'], text=True)
    assert inventory(stage) == before
    first = subprocess.check_output(command, text=True)
    after = inventory(stage)
    second = subprocess.check_output(command, text=True)
    assert inventory(stage) == after, 'Non-idempotent second application'
    subprocess.run(['sha256sum', '-c', 'stability46/SHA256SUMS'], cwd=stage, check=True,
                   stdout=subprocess.DEVNULL)
    m = json.loads((apply.HERE/'fixes.json').read_text())
    for binary in m['binaries']:
        assert after[binary['destination']] == binary['sha256']
        assert (stage/'.stability46/backups'/binary['original_sha256']).is_file()
    text = (stage/'run.sh').read_text()
    targets_only = text.replace(apply.CHECK+'\n', '', 1).encode()
    assert apply.digest(targets_only) == m['reference_run_sha256_after_targets_only']
    assert after['unrelated.keep'] == before['unrelated.keep']
    # These are local regular files, not the VM or device sysctl.
    fake = fixture/'fake-map-count'; fake.write_text('65530\n')
    hook = ['sh', str(stage/'stability46/prelaunch_map_count.sh'), '--file', str(fake)]
    subprocess.run(hook, check=True, capture_output=True)
    subprocess.run(hook+['--check'], check=True, capture_output=True)
    assert fake.read_text() == '1048576\n'
    report = dict(fixture=str(fixture), dry_run_no_writes=True, all_three_actual_artifacts=True,
                  targets_only_matches_reference=True, second_apply_byte_identical=True,
                  original_backups_verified=True, unrelated_file_unchanged=True,
                  fake_sysctl_readback=True, device_tested=False,
                  installed=json.loads((stage/'.stability46/receipt.json').read_text()))
    (fixture/'smoke.json').write_text(json.dumps(report, indent=2)+'\n')
    (fixture/'apply-first.txt').write_text(first); (fixture/'apply-second.txt').write_text(second)
    (fixture/'dry-run.json').write_text(dry)
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
