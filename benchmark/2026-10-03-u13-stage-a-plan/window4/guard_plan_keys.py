"""Read-only pre-LOCK membership: never infer corpus from a key prefix."""
from pathlib import Path
from collections import Counter
import json,os

def expand(s):
 workspace=Path(os.environ.get('WORKSPACES',str(Path(__file__).resolve().parent.parents[3])))
 return Path(os.path.expandvars(str(s).replace('$WORKSPACES',str(workspace))))
def validate(plan):
 rows=[]
 for shard in plan['shards']:
  data=json.loads(expand(shard['manifest']).read_text());apps=data.get('apps',data) if isinstance(data,dict) else data
  known=set(apps) if isinstance(apps,dict) else {x['key'] for x in apps}
  keys=expand(shard['keys_file']).read_text().replace(',',' ').split()
  unknown=sorted(set(keys)-known);duplicates=sorted(k for k,n in Counter(keys).items() if n>1)
  if unknown or duplicates:raise ValueError(f"{shard['name']}: unknown={unknown} duplicate={duplicates}")
  rows.append({'shard':shard['name'],'keys':keys,'manifest':shard['manifest']})
 return rows

if __name__=='__main__':
 import sys
 print(json.dumps(validate(json.loads(Path(sys.argv[1]).read_text())),indent=2))
