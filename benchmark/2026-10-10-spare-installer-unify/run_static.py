import json
import os
from pathlib import Path
import shutil
import subprocess

from prepare import HERE, REPO, save, sha


def main():
    workspaces = Path(os.environ.get('WORKSPACES', REPO.parent)).resolve()
    tools = workspaces / 'westlake-harness/scripts/lab'
    old = workspaces / 'oh61-bms-kit-b79/board-baseline/libinstalls.z.so'
    new = workspaces / 'oh61-bms-kit-b79/out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so'
    raw = HERE / '.artifacts/static'
    evidence = HERE / 'evidence'
    raw.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(exist_ok=True)
    commands = [
        ('whois', ['python3', str(tools / 'deployed_whois.py'), 'libinstalls.z.so']),
        ('open-old', ['python3', str(tools / 'open_site_scan.py'), str(old), '--json', str(raw / 'open-old.json')]),
        ('open-new', ['python3', str(tools / 'open_site_scan.py'), str(new), '--json', str(raw / 'open-new.json')]),
        ('strings', ['python3', str(tools / 'deployed_strings_diff.py'), str(new), '--deployed', str(old)]),
        ('abi', ['python3', str(tools / 'abi_diff.py'), '--old', str(old), '--new', str(new), '--calls', '--json', str(raw / 'abi.json')]),
        ('needed-old', [shutil.which('llvm-readelf') or 'llvm-readelf', '-d', str(old)]),
        ('needed-new', [shutil.which('llvm-readelf') or 'llvm-readelf', '-d', str(new)]),
    ]
    rows = []
    for name, argv in commands:
        result = subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', errors='backslashreplace')
        text = result.stdout + result.stderr
        original = raw / (name + '.txt')
        original.write_text(text)
        published = evidence / (name + '.txt')
        published.write_text(text.replace(str(workspaces) + '/', '$WORKSPACES/'))
        rows.append(dict(name=name, command=[value.replace(str(workspaces) + '/', '$WORKSPACES/') for value in argv],
                         exit_code=result.returncode, raw_path='.artifacts/static/' + original.name, raw_sha256=sha(original),
                         published_path='evidence/' + published.name, published_sha256=sha(published),
                         normalization='Only workspace prefix replaced; diagnostics and exit retained'))
        for path in raw.glob(name + '.json'):
            (evidence / path.name).write_text(path.read_text().replace(str(workspaces) + '/', '$WORKSPACES/'))
        print(f'{name}: exit={result.returncode}')
    tool_rows = []
    for name in ['llvm-nm', 'llvm-objdump', 'llvm-readelf']:
        executable = Path(shutil.which(name)).resolve()
        tool_rows.append(dict(name=name, path=str(executable).replace(str(Path.home()) + '/', '$HOME/'), sha256=sha(executable)))
    save(HERE / 'static-results.json', dict(board_access=False, commands=rows, toolchain=tool_rows,
                                          string_rejection_is_not_waived=True, service_owner_and_consumers='live window pending'))


if __name__ == '__main__':
    main()
