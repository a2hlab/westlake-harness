"""Same fresh-data/foreground/click timing as the accepted #25 matrix."""
from board25 import *
scripts=pathlib.Path(__file__).resolve().parent
for args in [('run25.py','offline','1','fresh-only'),('trial25.py','offline','fresh','2'),('trial25.py','online','fresh','1'),('trial25.py','online','fresh','2')]:
 name='-'.join(args[1:])
 print('START',name,flush=True)
 with (R/(name+'.driver.log')).open('w') as f:
  subprocess.run(['python3',str(scripts/args[0]),*args[1:]],stdout=f,stderr=subprocess.STDOUT,check=True)
 print('PASS',name,flush=True)
