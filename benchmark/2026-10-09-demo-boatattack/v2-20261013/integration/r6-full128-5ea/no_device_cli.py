"""Execute actual argparse entrypoints while denying every process/transport launch."""
import runpy,subprocess,sys,os
calls=[]
def deny(*args,**kwargs):
    calls.append(repr(args[:1]));raise AssertionError('OFFLINE_ONLY_SUBPROCESS_DENIED: '+repr(args[:1]))
for name in ('run','Popen','call','check_call','check_output'):setattr(subprocess,name,deny)
os.system=deny
program=sys.argv[1];sys.argv=sys.argv[1:]
try:runpy.run_path(program,run_name='__main__')
finally:print('OFFLINE_TRANSPORT_ATTEMPTS='+str(len(calls)),file=sys.stderr)
