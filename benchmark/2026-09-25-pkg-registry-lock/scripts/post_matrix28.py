from board25 import *
scripts=pathlib.Path(__file__).resolve().parent
for mode in ['offline','online']:
 name=mode+'-fresh-diag1'
 print('START',name,flush=True)
 with (R/(name+'.driver.log')).open('w') as f:
  subprocess.run(['python3',str(scripts/'diagnose25.py'),mode,'fresh','diag1'],stdout=f,stderr=subprocess.STDOUT,check=True)
 print('PASS',name,flush=True)
