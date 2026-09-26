from pathlib import Path
import sys,hashlib,json,struct,subprocess
p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),'symbol','inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
d=x['R']/'symbols';d.mkdir(exist_ok=True);f=d/'libsscronet.so';remote=x['rt']+'/lib/arm64-v8a/libsscronet.so'
s=x['dev']('sha256sum '+remote,10);x['recv'](remote,f,20);b=f.read_bytes();sha=hashlib.sha256(b).hexdigest();assert sha in s
loads=[];phoff=struct.unpack_from('<Q',b,32)[0];entsz,num=struct.unpack_from('<HH',b,54)
for i in range(num):
 t,flags,o,v,pa,z,ms,al=struct.unpack_from('<IIQQQQQQ',b,phoff+i*entsz)
 if t==1:loads.append((o,v,z))
va=next(v+0x28a21c-o for o,v,z in loads if o<=0x28a21c<o+z)
tool=Path.home()/'a2hlab/ws/toolchains/ohos-sdk/native/llvm/bin'
sym=subprocess.run([str(tool/'llvm-addr2line'),'-f','-C','-e',str(f),hex(va)],capture_output=True,text=True,timeout=10).stdout
dis=subprocess.run([str(tool/'llvm-objdump'),'-d','--start-address='+hex(va-64),'--stop-address='+hex(va+64),str(f)],capture_output=True,text=True,timeout=10).stdout
(d/'sscronet-symbolized.txt').write_text(s+f'file0x28a21c -> ELF{hex(va)}\n'+sym+dis);print((d/'sscronet-symbolized.txt').read_text())
