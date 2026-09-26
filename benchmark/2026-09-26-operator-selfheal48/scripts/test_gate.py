from pathlib import Path
import subprocess
import sys,json,gzip,hashlib
p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'gate-tests','inspect'];x={'__file__':str(p)};exec(p.read_text(),x);r=x['r'];r.mkdir(exist_ok=True);F='/data/local/tmp/operator45/selfheal48'
x['hdc'](['file','send','screen-gate',F+'/screen-gate'],x['R'],10);x['dev']('chmod 755 '+F+'/screen-gate',5)
root=p.parents[2]; old=root/'2026-09-26-operator-fresh-48/evidence/gate-tests'
cases=[]
for i,label in enumerate(['privacy','login','feed','unknown','unknown','unknown']):
 q=r/(str(i)+'.png');q.write_bytes(gzip.decompress((old/(str(i)+'.png.gz')).read_bytes()));cases.append((label,q))
for name,label in [('recovery1-feed','unknown'),('recovery1-final','feed'),('inflow5-later','unknown'),('newdetail5-later','unknown')]:
 q=r/(name+'.png');shared=p.parents[1]/'preview'/(name+'.png');subprocess.run(['mac','sips','-s','format','png',str(p.parents[1]/'preview/validation'/(name+'.jpeg')),'--out',str(shared)],check=True,stdout=subprocess.DEVNULL);q.write_bytes(shared.read_bytes());cases.append((label,q))
rows=[]
for expected,q in cases:
 x['hdc'](['file','send',q.name,F+'/gate-test.png'],r,10)
 actual=x['dev'](F+'/screen-gate '+F+'/gate-test.png',5).strip()
 rows.append(dict(name=q.name,expected=expected,actual=actual,sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
(r/'results.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2));assert all(j['expected']==j['actual'] for j in rows)
