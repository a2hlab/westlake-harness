"""Window2 auxiliary scheduling, same approved capture and selftest implementation.

Run the independent long-wait block once after the first regular group, so a
large remaining shard cannot starve all six authorized auxiliary observations.
All captures share the parent cutoff; transaction/finish ownership is unchanged.
"""
from pathlib import Path
import json,sys
import observe

def main():
 argv=sys.argv[1:];mode=argv[0]
 def value(name):return argv[argv.index(name)+1]
 plan=json.loads(Path(value('--plan')).read_text())
 if mode=='longwait':
  root=Path(value('--root'))
  if (root/'longwait-result.json').exists():return 0
  return observe.main()
 rc=observe.main()
 if value('--name')==plan.get('longwait_after_shard'):
  root=Path(value('--out')).parent.parent
  if not (root/'longwait-result.json').exists():
   return observe.longwait(plan,root,float(value('--cutoff')))
 return rc
if __name__=='__main__':raise SystemExit(main())
