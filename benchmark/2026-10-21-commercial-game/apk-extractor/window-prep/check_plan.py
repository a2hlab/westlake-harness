#!/usr/bin/env python3
"""Validate recorded offline G12 facts, never admit device execution."""
import json
from pathlib import Path
p=Path(__file__).resolve().parent
plan=json.loads((p/'plan.disabled.json').read_text());proof=json.loads((p/'build-proof.json').read_text());fresh=json.loads((p/'fresh-next-review.json').read_text())
assert plan['execution_enabled'] is False
assert plan['candidate']['sha256']==proof['candidate']['library_sha256']=='7c24bd11190b0728b81ecd958519f01c688efb2533ef26c9b7ae4eefc82151db'
assert proof['step_count']==13 and proof['all_rc_zero'] and len(proof['raw'])==52
assert fresh['processes']==345 and fresh['consumers']==[] and fresh['ondemand'] is True
assert fresh['profile']['systemability'][0]['stop-on-demand']['longtimeunused-unload']==180
assert plan['historical_reload']['enabled'] is False
print('G12 offline evidence consistent; device execution disabled')
