"""No rebuild: compare existing WebView knobs on the feed-capable #38 stage."""
from board34 import *
import hashlib
fixed='--gles-fixed' in sys.argv
mode,name=sys.argv[1:3];assert mode in ('no-surface-control','in-process','software')
d=json.loads((R/'warm-b11/device-report.json').read_text());runtime=d['runtime']
assert not dev('cat /proc/[0-9]*/mountinfo 2>/dev/null | grep '+pathlib.Path(runtime).name,120).strip(),'live namespace'
base=R/'ab-config/original-run.sh';text=base.read_text()
assert 'APPSPAWNX_NO_JIT' not in text
text=text.replace('exec /data/local/tmp/asx/appspawn-x',f'export WESTLAKE_WEBVIEW_GPU_MODE={mode}\nexport WESTLAKE_WEBVIEW_SINGLE_PROCESS=1\nexec /data/local/tmp/asx/appspawn-x')
work=R/'webview-config';work.mkdir(exist_ok=True);run=work/(name+'.run.sh');run.write_text(text)
def send(p,remote):subprocess.run([H,'-t',S,'file','send',str(p),remote],check=True,timeout=240)
send(run,runtime+'/run.sh');dev('chmod 755 '+runtime+'/run.sh')
provenance={'mode_requested':mode,'single_process_requested':True,'run_sha256':hashlib.sha256(run.read_bytes()).hexdigest(),'hiperf':False,'origin':'warm-b11','timing_acceptance':False}
original_shim=pathlib.Path.home()/'a2hlab/ws/out-sp20/webview-candidate/webview-t-lib/libwebview_bionic_shim.so'
remote_shim=runtime+'/webview-t-lib/libwebview_bionic_shim.so'
if fixed:
 expected=hashlib.sha256(original_shim.read_bytes()).hexdigest()
 assert dev('sha256sum '+remote_shim).split()[0]==expected,'unexpected original shim'
 shim=pathlib.Path.home()/'a2hlab/ws/out-ability38/webview-gles-order/libwebview_bionic_shim.so'
 provenance['shim_sha256']=hashlib.sha256(shim.read_bytes()).hexdigest()
 send(shim,remote_shim);dev('chmod 644 '+remote_shim)
 assert dev('sha256sum '+remote_shim).split()[0]==provenance['shim_sha256']
try:
 args=['python3',str(pathlib.Path(__file__).with_name('physical34.py')),name,'article','--candidate','--origin=warm-b11','--select-title','--setup-manual','--manual-ready','--observe-long']
 if '--warm' in sys.argv:args+=['--warm']
 p=subprocess.run(args)
finally:
 if (R/name).exists():(R/name/'webview-config.json').write_text(json.dumps(provenance,indent=2)+'\n')
 if fixed:send(original_shim,remote_shim);dev('chmod 644 '+remote_shim)
 send(base,runtime+'/run.sh');dev('chmod 755 '+runtime+'/run.sh')
sys.exit(p.returncode)
