"""Archive current attempt evidence; raw stderr stays on VM, filtered excerpts in git."""
import json
import shutil
import sys
import hashlib
import t0_evidence as evidence
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DEST = REPO / 'benchmark/2026-09-28-blocker-triage/runs'


def export(run):
    base = Path.home() / 'a2hlab/ws' / ('out-appsweep-t0-' + run)
    for board in base.iterdir():
        if not board.is_dir():
            continue
        dest_board = DEST / run / board.name
        dest_board.mkdir(parents=True, exist_ok=True)
        for name in ('invalidated.json', 'shard.json', 'admission.json'):
            if (board / name).exists():
                shutil.copyfile(board / name, dest_board / name)
        for directory in ('base-audit', 'clock-sync', 'cleanup', 'interference-audit', 'isolation-audit'):
            if (board / directory).exists():
                shutil.copytree(board / directory, dest_board / directory, dirs_exist_ok=True)
    for p in base.glob('*/*/triage.json'):
        row = json.loads(p.read_text())
        serial, key = row['serial'], row['key']
        dst = DEST / run / serial / key
        dst.mkdir(parents=True, exist_ok=True)
        source = p.parent
        names = ['triage.json', 'hilog.crash.txt',
                 'rs.txt', 'wm.txt', 'commands.jsonl', 'snapshot.txt', 'input-hashes.json',
                 'quit0.stack.txt', 'quit1.stack.txt', 'framework.json']
        for name in names:
            if (source / name).exists():
                shutil.copyfile(source / name, dst / name)
        raw_path = source / 'child.final.stderr.filtered'
        if not raw_path.exists():
            raw_path = source / 'child.pre.stderr.filtered'
        if raw_path.exists():
            raw = raw_path.read_text()
            excerpt, lines = evidence.stderr_excerpt(raw)
            (dst / 'stderr-evidence.txt').write_text(excerpt)
            (dst / 'stderr-provenance.json').write_text(json.dumps({
                'vm_source': str(raw_path), 'sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                'raw_filtered_line_count': len(raw.splitlines()), 'excerpt_source_lines': lines}, indent=2) + '\n')
        parent = source / 'parent.log'
        if parent.exists():
            (dst / 'parent-evidence.txt').write_text('\n'.join(parent.read_text().splitlines()[-25:]) + '\n')
        # Keep probe identity and hash verification command receipts, no bundle personal metadata.
        report_path = source / 'probe/device-report.json'
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        reduced = {k: report.get(k) for k in ['child', 'parent', 'runtime', 'stage', 'window',
                   'apk_sha256', 'source_host_hap_sha256', 'framework_report_sha256', 'source_files']}
        (dst / 'device-identity.json').write_text(json.dumps(reduced, indent=2) + '\n')
        commands_path = source / 'probe/commands.jsonl'
        commands = commands_path.read_text().splitlines() if commands_path.exists() else []
        checks = [json.loads(line) for line in commands if json.loads(line)['command'].startswith('sha256sum ')]
        (dst / 'hash-checks.json').write_text(json.dumps(checks, indent=2) + '\n')
        f = source / (key + '.jpeg')
        if f.exists():
            shutil.copyfile(f, dst.parent / f.name)
        print(run, serial[:8], key, flush=True)


if __name__ == '__main__':
    for run in sys.argv[1:]:
        export(run)
