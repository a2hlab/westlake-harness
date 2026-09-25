from board34 import *
script=pathlib.Path(__file__).with_name('physical34.py')
while not (R/'warm-b9/child.stderr').exists():time.sleep(2)
# Wait for prior finally block to remove the old private namespace.
while dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep a2hlab-source-f9c50f561b75433b97d54cc945f9aed8',120).strip():time.sleep(1)
origin='warm-b9'
for name,warm in [('cold-a7',False),('warm-b10',True)]:
 args=['python3',str(script),name,'article','--candidate','--origin='+origin,'--wait-idle','--select-title']
 if warm:args+=['--warm']
 print('FINAL_PAIR_BEGIN',name,flush=True);p=subprocess.run(args);print('FINAL_PAIR_END',name,p.returncode,flush=True);origin=name
