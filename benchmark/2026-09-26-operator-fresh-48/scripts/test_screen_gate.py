from pathlib import Path
from PIL import Image
import sys,json,hashlib
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'gate-tests','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x);r=x['r'];r.mkdir(exist_ok=True)
x['hdc'](['file','send','screen-gate','/data/local/tmp/operator45/screen-gate'],x['R'],10);x['dev']('chmod 755 /data/local/tmp/operator45/screen-gate',5)
root=p.parents[2]
cases=[('privacy','2026-09-26-operator-fresh-48/preview/fresh-r2/gate-1.jpeg'),('login','2026-09-26-operator-fresh-48/preview/fresh-r3/feed-gate.jpeg'),('feed','2026-09-26-operator-fresh-48/preview/fresh-r3/close-2.jpeg'),('unknown','2026-09-26-operator-fresh-48/preview/fresh-r3/current.jpeg'),('unknown','2026-09-26-master-hook-48/evidence/master-r1/during-10.jpeg'),('unknown','2026-09-26-master-hook-48/evidence/master-r4/gate-2.jpeg')]
rows=[]
for i,(expected,name) in enumerate(cases):
 src=root/name;out=r/(str(i)+'.png');Image.open(src).convert('RGB').save(out)
 x['hdc'](['file','send',out.name,'/data/local/tmp/fresh48-gate-test.png'],r,10)
 label=x['dev']('/data/local/tmp/operator45/screen-gate /data/local/tmp/fresh48-gate-test.png',5).strip()
 rows.append(dict(source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),expected=expected,actual=label,pass_=label==expected))
(r/'results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2));assert all(j['pass_'] for j in rows)
