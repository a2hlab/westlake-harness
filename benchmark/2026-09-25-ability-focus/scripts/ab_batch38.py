from board34 import *
script=pathlib.Path(__file__).with_name('ab38.py')
# Run only after the separate first baseline has completed its full cleanup.
while not (R/'ab-base-1/ab-config.json').exists():time.sleep(1)
time.sleep(2)
for arm,num in [('nojit',1),('npth',1),('verify',1),('verify',2),('base',2),('npth',2),('nojit',2),('npth',3),('nojit',3),('base',3),('verify',3),('base',4)]:
 name=f'ab-{arm}-{num}';print('BEGIN',name,flush=True)
 p=subprocess.run(['python3',str(script),arm,name]);print('END',name,p.returncode,flush=True)
 if p.returncode:break

