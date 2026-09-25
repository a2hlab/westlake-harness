from board25 import *
# Alternate condition order across repetitions to reduce monotonic order effects.
trials=[('offline','fresh','3'),('online','fresh','1'),('online','seeded','1'),('offline','seeded','1'),('offline','seeded','2'),('online','seeded','2'),('online','fresh','2'),('offline','fresh','4')]
for mode,kind,rep in trials:
 name=f'{mode}-{kind}-{rep}'
 print('START',name,flush=True)
 with (R/(name+'.log')).open('w') as f:
  p=subprocess.run(['python3',str(pathlib.Path(__file__).with_name('trial25.py')),mode,kind,rep],stdout=f,stderr=subprocess.STDOUT)
 print('END',name,p.returncode,flush=True)
 if p.returncode:sys.exit(p.returncode)
