#!/usr/bin/env python3
"""Fail until item 64 has real, complete three-board observations."""
import json
from pathlib import Path
import collect

p = Path(__file__).resolve().parent / 'results.json'
data = json.loads(p.read_text())
errors = list(data['gaps'])
if {b['serial'] for b in data['boards']} != set(collect.SERIALS):
    errors.append('three-board serial coverage incomplete')
for b in data['boards']:
    if not b.get('stable_boot'):
        errors.append(b['serial'] + ': boot identity not verified')
    for role in ['appspawn', 'helloworld']:
        procs = [p for p in b['processes'] if p['role'] == role]
        if not procs or not all(p['stable_process'] and p.get('stable_maps') and p['maps_nonempty'] and not p['unverified_files'] for p in procs):
            errors.append(b['serial'] + ': missing/unstable/unverified ' + role + ' mappings')
print(json.dumps({'passed': not errors, 'errors': errors}, indent=2))
raise SystemExit(1 if errors else 0)
