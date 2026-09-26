from pathlib import Path
import sys,shutil
p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'crash-review','inspect'];x={'__file__':str(p)};exec(p.read_text(),x);r=x['r'];r.mkdir(exist_ok=True)
s=x['dev']('sha256sum '+x['rt']+'/libhwui.so',8);(r/'hwui-sha.txt').write_text(s);x['recv'](x['rt']+'/libhwui.so',r/'libhwui.so',15)
old=x['R'].parent/'selfheal48/board-archive/crashes'
for q in old.glob('selfheal-*'):
 if q.name.split('-')[1] in ('9','10'):shutil.copytree(q,x['R']/'pre-speed-watchdog'/q.name,dirs_exist_ok=True)
print(s)
