from pathlib import Path
import sys,json
p=Path('/Users/zhaoyue/orca/workspaces/westlake-harness-fresh48/benchmark/2026-09-26-operator-fresh-48/scripts/warm48.py');sys.argv=[str(p),'guardian-test','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
dev=x['dev'];r=x['r'];F='/data/local/tmp/operator45/fresh48'
s=dev('cat '+F+'/instance.txt',5);d=dict(l.split('=',1) for l in s.splitlines());(r/'final-instance.txt').write_text(s)
(r/'stopped-state.txt').write_text(dev('cat /proc/uptime; cat '+F+'/state; cat '+F+'/events.log; cat '+F+'/ui.log; cat '+F+'/guardian.log; test ! -d '+F+'/lock && echo GUARD_STOPPED',10))
x['cleanup'](d['parent'],d['child']);x['collect'](int(d['child']))
for name in ['fresh-r1','fresh-r2','fresh-r3','fresh-r4']:
 dr=x['R']/name
 (dr/'visual-review.json').write_text(json.dumps(dict(feed_real_titles=name=='fresh-r3',body_text_visible=False,note='No article body observed; r1 is infrastructure abort, excluded from formal three rounds.')))
