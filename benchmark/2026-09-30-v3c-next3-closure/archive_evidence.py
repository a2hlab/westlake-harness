#!/usr/bin/env python3
"""Retain measured records, process tables, screenshots and diagnostic excerpts."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for run in sorted((ROOT / 'runs').iterdir()):
    for board in run.iterdir():
        if not board.is_dir():
            continue
        out = ROOT / 'evidence' / run.name / board.name
        out.mkdir(parents=True, exist_ok=True)
        for name in ['facts.txt', 'preflight.json', 'plan.json', 'summary.json', 'runtime-fingerprint.json']:
            src = board / name
            if src.is_file():
                shutil.copy2(src, out / name)
        for rec in board.glob('*/record.json'):
            app = rec.parent
            dest = out / app.name
            dest.mkdir(exist_ok=True)
            for src in app.iterdir():
                if src.is_file() and (src.name in ['record.json', 'diagnostics.json', 'bundle.txt'] or src.name.startswith('processes-') or src.suffix == '.jpeg'):
                    shutil.copy2(src, dest / src.name)
            log = app / 'hilog.txt'
            if log.exists():
                data = log.read_bytes()
                needles = ['JNI FatalError', 'FATAL EXCEPTION', 'UnsatisfiedLinkError', 'librsdroid', 'AudioSystem', 'native_getMaxChannelCount', 'NoClassDefFoundError', 'Add too many the special handlers', 'libdfx_signalhandler.z.so', 'do_init_fini', 'dlopen_impl', 'Reason:Signal']
                lines = [f'{i}: {line}' for i, line in enumerate(data.decode(errors='replace').splitlines(), 1) if any(n in line for n in needles)]
                (dest / 'selected-hilog.txt').write_text('\n'.join(lines) + '\n')
                (dest / 'hilog-source.json').write_text(json.dumps({'path': str(log), 'sha256': hashlib.sha256(data).hexdigest()}, indent=2) + '\n')
