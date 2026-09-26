"""Runs on Mac via mac; hard timeout covers the real hdc process, not only its VM proxy."""
import base64,json,os,signal,subprocess,sys
j=json.loads(base64.b64decode(sys.argv[1]));assert j['serial']=='61b0657200000000000000000324012c'
p=subprocess.Popen(['/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc','-t',j['serial'],*j['args']],cwd=j['cwd'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
try:out=p.communicate(timeout=min(float(j['timeout']),55))[0]
except subprocess.TimeoutExpired:
 os.killpg(p.pid,signal.SIGKILL)
 try:out=p.communicate(timeout=2)[0]
 except subprocess.TimeoutExpired:out=b''
 sys.stdout.buffer.write(out+b'\nHDC_HARD_TIMEOUT\n');sys.exit(124)
sys.stdout.buffer.write(out);sys.exit(p.returncode)
