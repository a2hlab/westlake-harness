"""Offline per-run WL-KS-PROBE accounting. Silence is unknown, never successful crypto."""
import argparse
import hashlib
import json
import re
from pathlib import Path

LINE = re.compile(r'^\S+ \S+\s+(\d+)\s+')
OK = re.compile(r'validateAead(?:\([^)]*\))?\s*=\s*OK\b')

def scan_text(text, pids):
    rows = {str(pid): {'marker_lines': 0, 'selftest_errors': [], 'validateAead_OK': []} for pid in pids}
    for number, line in enumerate(text.splitlines(), 1):
        m = LINE.match(line)
        if not m or m[1] not in rows or '[WL-KS-PROBE]' not in line:
            continue
        row = rows[m[1]]
        row['marker_lines'] += 1
        event = {'line_number': number, 'line': line,
                 'line_sha256': hashlib.sha256(line.encode()).hexdigest()}
        if re.search(r'\bselftest error\b', line):
            row['selftest_errors'].append(event)
        if OK.search(line):
            row['validateAead_OK'].append(event)
    for row in rows.values():
        row['status'] = ('REJECT' if row['selftest_errors'] else
                         'PASS' if row['validateAead_OK'] else 'unknown')
    return rows

def run_row(record):
    d = record.parent
    rec = json.loads(record.read_text())
    uid = (rec.get('bms') or {}).get('uid')
    pids = set()
    for p in d.glob('processes-t*.txt'):
        for line in p.read_text(errors='replace').splitlines():
            f = line.split()
            if len(f) >= 4 and f[0].isdigit() and f[2] == str(uid) and f[3] == 'appspawn-x':
                pids.add(f[0])
    log = d / 'hilog.txt'
    rows = scan_text(log.read_text(errors='replace') if log.is_file() else '', pids)
    diagnostic = rec.get('diagnostics') or {}
    complete = diagnostic.get('complete') is True and log.is_file()
    status = ('REJECT' if any(r['selftest_errors'] for r in rows.values()) else
              'PASS' if rows and complete and all(r['status'] == 'PASS' for r in rows.values()) else 'unknown')
    return {'record': str(record), 'key': rec.get('key', d.name), 'uid': uid,
            'processes': rows, 'complete_hilog': complete, 'status': status,
            'selftest_error_count': sum(len(v['selftest_errors']) for v in rows.values()),
            'validateAead_OK_count': sum(len(v['validateAead_OK']) for v in rows.values()),
            'hilog_sha256': hashlib.sha256(log.read_bytes()).hexdigest() if log.is_file() else None}

def report(root):
    rows = [run_row(p) for p in sorted(root.rglob('record.json'))]
    return {'runs': rows, 'run_count': len(rows),
            'error_runs': sum(r['selftest_error_count'] > 0 for r in rows),
            'selftest_error_count': sum(r['selftest_error_count'] for r in rows),
            'validateAead_OK_count': sum(r['validateAead_OK_count'] for r in rows),
            'unknown_runs': sum(r['status'] == 'unknown' for r in rows),
            'passed': bool(rows) and all(r['status'] == 'PASS' for r in rows)}

def main():
    p = argparse.ArgumentParser(); p.add_argument('root', type=Path); p.add_argument('--out', type=Path)
    a = p.parse_args(); data = report(a.root)
    body = json.dumps(data, indent=2) + '\n'
    if a.out: a.out.write_text(body)
    print(body, end='')
    return 0 if data['passed'] else 1

if __name__ == '__main__': raise SystemExit(main())
