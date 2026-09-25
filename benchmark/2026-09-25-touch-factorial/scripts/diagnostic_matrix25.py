from board25 import *
for mode,extra in [('offline',['late']),('online',[])]:
 name=f'{mode}-fresh-diag1'
 print('START',name,flush=True)
 with (R/(name+'.log')).open('w') as f:
  p=subprocess.run(['python3',str(pathlib.Path(__file__).with_name('diagnose25.py')),mode,'fresh','diag1',*extra],stdout=f,stderr=subprocess.STDOUT)
 print('END',name,p.returncode,flush=True)
 if p.returncode:sys.exit(p.returncode)
