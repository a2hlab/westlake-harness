from board34 import *
script=pathlib.Path(__file__).with_name('ab38.py')
while not (R/'ab-npth-1/ab-config.json').exists():time.sleep(1)
time.sleep(3)
for arm,num in [('base',2),('verify',1),('nojit',2),('base',3),('verify',2),('nojit',3),('base',4),('verify',3)]:
 name=f'ab-{arm}-{num}';print('BEGIN',name,flush=True)
 p=subprocess.run(['python3',str(script),arm,name]);print('END',name,p.returncode,flush=True)
