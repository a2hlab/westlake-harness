#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
from analyze import analyze,stat,dev,object_record
D=Path(__file__).resolve().parent
def main():
 p=D/'evidence';r=json.loads((D/'results.json').read_text())
 for x in json.loads((D/'provenance.json').read_text()):assert hashlib.sha256((D/x['public']).read_bytes()).hexdigest()==x['public_sha256']
 assert dev(66352)==(259,48)
 for i in [0,1]:
  assert r['rounds'][i]['maps_identity_bracket']
  assert all(o['accepted'] for o in r['rounds'][i]['objects'])
  for phase in ['before','after']:assert stat((p/f'{i}-stat-{phase}.stdout.txt').read_text())['birth']==598912
 assert stat((p/'2-stat-after.stdout.txt').read_text()) is None
 for i in range(4):assert object_record((p/f'2-object-{i}.stdout.txt').read_text()) is None
 assert not r['rounds'][2]['maps_identity_bracket'] and not any(x['accepted'] for x in r['rounds'][2]['objects'])
 assert r['loader_entry_winner']==r['namespace_owner_per_mapping']=='UNKNOWN'
 rows=[o['parsed'] for o in r['rounds'][1]['objects']]
 for name in ['libapp_native_loader.so','libnativeloader.so']:
  pair=[o for o in rows if o['path'].endswith('/'+name)];assert len(pair)==2 and pair[0]['sha256']==pair[1]['sha256'] and pair[0]['inode']!=pair[1]['inode']
 print('PASS: raw hashes, two complete identity intervals, four rejected round2 object bodies, Linux dev_t and same-SHA/different-inode; winner UNKNOWN')
if __name__=='__main__':main()
