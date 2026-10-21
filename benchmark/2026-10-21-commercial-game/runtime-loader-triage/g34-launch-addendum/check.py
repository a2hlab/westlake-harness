import json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
r=json.loads((D/'results.json').read_text());e=json.loads((D/'log-excerpts.json').read_text());f=json.loads((D/'fault-evidence.json').read_text());i=json.loads((D/'identity-and-maps.json').read_text())
assert r['terminal']['signal']==11 and r['terminal']['line']==3791
assert r['terminal']['faulting_tid']=='UNKNOWN' and r['winner']=='UNKNOWN'
assert 'exit with signal:11' in next(x['text'] for x in e['lines'] if x['line']==3791)
assert '[CODE: -31]' in f['dfx_query']['stdout'] and f['dfx_query']['outer_rc']==0
assert i['before']['birth_ticks']==i['after']['birth_ticks']==2248607
assert r['captured_list_entries']==2 and not r['new_fix_proposed']
assert r['search_counts_in_supplied_child_log']['gles_fallback_errors']==66
print('PASS static addendum consistency; crash cause and binding winner remain UNKNOWN')
