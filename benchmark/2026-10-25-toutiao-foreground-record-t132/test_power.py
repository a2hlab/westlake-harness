#!/usr/bin/env python3
"""Execute only the two production parsing/maintenance functions with fake I/O."""
import ast
import re
from pathlib import Path

p = Path(__file__).with_name('observe_v2.py')
nodes = [n for n in ast.parse(p.read_text()).body if isinstance(n, ast.FunctionDef) and n.name in ('read_power', 'maintain_power')]
code = compile(ast.Module(body=nodes, type_ignores=[]), str(p), 'exec')
cases = [
    ('missing_override_then_confirmed', ['Current State: AWAKE\nScreenOffTime: Timeout=30000ms', 'Current State: AWAKE\nScreenOffTime: Timeout=30000ms OverrideTimeout=600000ms'], False),
    ('missing_base', ['Current State: AWAKE'], True),
    ('missing_state', ['ScreenOffTime: Timeout=30000ms'], True),
    ('post_value_missing', ['Current State: AWAKE\nScreenOffTime: Timeout=30000ms'] * 2, True),
    ('post_value_wrong', ['Current State: AWAKE\nScreenOffTime: Timeout=30000ms OverrideTimeout=10000ms'] * 2, True),
]
for name, outputs, expected_failure in cases:
    it = iter(outputs)
    calls = []
    def raw(label, command):
        calls.append((label, command))
        return 'OK' if command.startswith('power-shell') else next(it)
    ns = dict(re=re, power_preimage=dict(base=30000, override=10000), POWER='POWER_READ', raw_shell=raw, ok=lambda x: x, held=lambda label: None)
    exec(code, ns)
    try:
        ns['maintain_power']('fixture')
        failed = False
    except RuntimeError:
        failed = True
    assert failed == expected_failure, name
    if name == 'missing_override_then_confirmed':
        assert any(command == 'power-shell timeout -o 600000' for _, command in calls)
    print(name + ': PASS (synthetic only)')
