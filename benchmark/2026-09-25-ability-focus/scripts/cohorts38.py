"""Serial cold/warm pairs on the single authorized board; never clear warm data."""
from board34 import *
script=pathlib.Path(__file__).with_name('physical34.py')
while not (R/'warm-b7/child.stderr').exists():time.sleep(2)
origin='warm-b7'
for name,warm in [('cold-a5',False),('warm-b8',True),('cold-a6',False),('warm-b9',True)]:
    print('COHORT_BEGIN',name,flush=True)
    args=['python3',str(script),name,'article','--candidate','--origin='+origin,'--wait-idle']
    if warm:args+=['--warm']
    p=subprocess.run(args)
    print('COHORT_END',name,'rc',p.returncode,flush=True)
    origin=name
