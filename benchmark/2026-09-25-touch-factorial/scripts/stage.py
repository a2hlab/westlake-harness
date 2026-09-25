from board25 import *
A=pathlib.Path('/home/dspfac/a2hlab/source-closure/verify')
s=(A/'westlake-touch21/evidence/touch-latency-21/scripts/stage-wake.sh').read_text()
s=re.sub(r'S=[0-9a-f]+', 'S='+S,s).replace('/touch21','/touch25')
(R/'stage.sh').write_text(s)
with (R/'stage.log').open('w') as f:subprocess.run(['bash',str(R/'stage.sh')],stdout=f,stderr=subprocess.STDOUT,check=True)
print('framework complete',flush=True)
