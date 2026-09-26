"""Freeze existing evidence, audit compatibility, and smoke-test AOT installation.
No HDC, no compilation, no changes to shared source/output artifacts.
"""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from apply_speed_aot import sha
from inspect_oat import inspect

def main():
    here = Path(__file__).resolve().parent
    ws = Path.home()/'a2hlab/ws'
    lock = json.loads((here/'speed-lock.json').read_text())
    base = ws/'out-speed-aot'; base.mkdir(exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix='verify-', dir=base))
    board = Path.home()/'a2hlab/board/61b0657200000000000000000324012c'
    report_path = board/'operator45/framework/device-report.json'
    report = json.loads(report_path.read_text())
    for name, entry in lock['inputs'].items():
        assert report['files'][name]['sha256'] == entry['sha256'], name
        assert sha(ws/'out-aot42/inputs'/name) == entry['sha256'], name
    current_art = ws/'out-operator48/libart.so'
    assert sha(current_art) == lock['libart_sha256']
    lineage = json.loads((ws/'out-operator48/result.json').read_text())
    assert lineage['stock_relink_identical'] and lineage['objects'] == 454
    assert lineage['patched_art'] == lock['libart_sha256']
    assert lineage['changed_object'] == 'stubs/link_stubs_arm64.weak.o'
    assert sha(ws/'out-aot42/tools/dex2oat') == lock['compiler_sha256']
    for name, value in lock['artifacts'].items():
        assert sha(ws/'out-aot42/speed-explicit'/name) == value['sha256'], name
    oat = inspect(ws/'out-aot42/speed-explicit/toutiao.odex')
    assert oat['oat_version'] == '247' and oat['dex_file_count'] == 21
    assert oat['metadata']['compiler-filter'] == 'speed'
    assert oat['metadata']['classpath'] == 'PCL[]'
    assert oat['metadata']['bootclasspath-checksums'] == 'i;9/aa28fa9b'
    parent = board/'stub48/stub-r3/parent.log'
    lines = [line for line in parent.read_text(errors='replace').splitlines()
             if '[AppSpawnX][VM]' in line and ('-Xbootclasspath' in line or '-Ximage:' in line)]
    logical = [Path(x).name for x in oat['metadata']['bootclasspath'].split(':')]
    assert any('-Xbootclasspath-locations:'+oat['metadata']['bootclasspath'] in line for line in lines)
    assert any('-Xbootclasspath:'+':'.join('/data/local/tmp/asx/fw/'+x for x in logical) in line for line in lines)
    assert any('-Ximage:/data/local/tmp/asx/boot/boot.art' in line for line in lines)
    (out/'parent-bcp.txt').write_text('\n'.join(lines)+'\n')
    shutil.copy2(report_path, out/'framework-report.json')
    (out/'lineage.json').write_text(json.dumps(lineage, indent=2)+'\n')
    stage = out/'runtime'; stage.mkdir()
    for name in lock['inputs']:
        p = stage/name; p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ws/'out-aot42/inputs'/name, p)
    shutil.copy2(current_art, stage/'libart.so')
    shutil.copy2(ws/'out-aot42/inputs/toutiao.apk', stage/'toutiao.apk')
    # Use archived operator run solely as data; no shell command is executed.
    run = board/'operator45/warm/run.sh'; shutil.copy2(run, stage/'run.sh')
    before_run = sha(stage/'run.sh'); before_art = sha(stage/'libart.so')
    command = ['bash', str(here/'apply_speed_aot.sh'), str(stage), '--framework-report', str(report_path)]
    subprocess.run(command+['--dry-run'], check=True, stdout=(out/'dry-run.txt').open('w'))
    assert not (stage/'oat').exists()
    subprocess.run(command, check=True, stdout=(out/'first-apply.txt').open('w'))
    assert (stage/'oat').stat().st_mode & 0o777 == 0o755
    assert (stage/'oat/arm64').stat().st_mode & 0o777 == 0o755
    assert all((stage/'oat/arm64'/name).stat().st_mode & 0o777 == 0o644 for name in lock['artifacts'])
    receipt = (stage/'.speed-aot/receipt.json').read_bytes()
    subprocess.run(command, check=True, stdout=(out/'second-apply.txt').open('w'))
    assert receipt == (stage/'.speed-aot/receipt.json').read_bytes()
    assert sha(stage/'run.sh') == before_run and sha(stage/'libart.so') == before_art
    subprocess.run(['sha256sum','-c','.speed-aot/SHA256SUMS'], cwd=stage, check=True,
                   stdout=(out/'installed-sha.txt').open('w'))
    record = dict(output=str(out), framework_report=str(report_path),
                  framework_report_sha256=sha(report_path), framework_stage=report['stage'],
                  parent_evidence=str(parent), parent_sha256=sha(parent),
                  bcp_and_boot_files_matched=len(lock['inputs']), libart_lineage=lineage,
                  compiler_sha256=lock['compiler_sha256'], artifacts=lock['artifacts'],
                  reused_without_recompile=True, oat_metadata=oat['metadata'],
                  idempotent=True, run_and_native_unchanged=True, device_tested=False,
                  note='Archived report/BCP plus A1 lineage; actual deployment hashes gated by installer')
    (out/'verification.json').write_text(json.dumps(record, indent=2)+'\n')
    print(out)

if __name__ == '__main__': main()
