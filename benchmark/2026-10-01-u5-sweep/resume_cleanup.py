#!/usr/bin/env python3
"""Retry target-only cleanup after its completed timed collection, preserving raw record."""
import json, shlex, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts/lab'));import lab_paths
sys.path.insert(0,str(lab_paths.harness()/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
serial=next(s for s in lab_paths.boards('oh') if s.startswith('5ea'))
record=HERE/'runs/u5-5ea'/serial/'fd-organicmaps/record.json';d=json.loads(record.read_text())
assert d['status']=='batch_interrupted' and d['error']=='target cleanup could not be verified; stop before next app'
assert {s['scheduled_seconds'] for s in d['screenshots'] if s['captured']}=={5,20}
out=HERE/'5ea/cleanup-resume';out.mkdir(exist_ok=False)
board=b.Board(serial,str(ROOT/'benchmark/2026-09-30-n3-61b/transport/hdc_mac.sh'),'mac '+shlex.quote(str(lab_paths.tools()/'board_note.sh')),'cx-t0',out/'commands');board.ready();assert board.boot==d['boot_id']
ok=b.cold_stop(board,d['package'],d['bms']['uid'],out,'retry')
b.save(out/'receipt.json',{'record':str(record.relative_to(HERE)),'boot_id':board.boot,'cleanup_verified':ok,'original_record_preserved':True})
assert ok
print('cleanup verified; original timed trial retained')
