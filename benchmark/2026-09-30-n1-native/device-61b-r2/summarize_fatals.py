#!/usr/bin/env python3
"""Keep exact fatal/checkpoint lines; absence of a line is not a pass."""
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent
rows = []
for record in sorted((P / 'runs/n1-r2-targets-61b').glob('61b*/*/record.json')):
    log = record.parent / 'hilog.txt'
    lines = log.read_text(errors='replace').splitlines()
    def matching(needle):
        return [{'line': n + 1, 'text': line} for n, line in enumerate(lines)
                if needle in line]
    fatal = matching('J_invokeStaticMain_main_threw')
    rows.append({
        'key': record.parent.name,
        'hilog': str(log.relative_to(P)),
        'hilog_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
        'first_main_fatal': fatal[0] if fatal else None,
        'relocation_errors': matching('relocating failed:')[:8],
        'flutter_ready': matching('[ANL-FLUTTER]'),
        'soundpool_checkpoint': matching('OH_AVPlayer_Create'),
        'background_exceptions': matching('[B8-UEH]') + matching('Caused by: java.lang.NullPointerException'),
        'egl_checkpoints': matching('/OH_EglHijack:'),
        'limit': 'Captured log only; no main fatal does not prove a live or rendered app.'
    })
(P / 'first-fatal-summary.json').write_text(json.dumps(rows, indent=2) + '\n')
print('Summarized', len(rows), 'records')
