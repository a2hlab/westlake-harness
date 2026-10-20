"""Validate only reference receipt/plan structure; playback remains human-reviewed."""
import json
from pathlib import Path
p=Path(__file__).parent
r=json.loads((p/'results.json').read_text())
t=json.loads((p/'trace-plan.json').read_text())
assert r['package']['apk_sha256']=='a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395'
assert r['serial']==t['serial']=='N100CU025C18D000128'
assert r['trace_started'] is False
assert t['status']=='NOT_EXECUTED_OUTER_ONLY'
assert any('20s' in str(x.get('argv',[])) for x in t['steps'])
print('PASS baseline and unexecuted plan structure only; runtime review remains pending')
