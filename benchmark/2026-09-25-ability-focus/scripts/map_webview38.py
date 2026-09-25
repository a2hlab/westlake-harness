"""Use registers+maps to avoid accepting faulty printed relative PCs."""
from board34 import *
import hashlib
r=R/'webview-offline';r.mkdir(exist_ok=True)
f=next((R/'cold-a4').glob('cppcrash-*'));s=f.read_text()
lib=pathlib.Path.home()/'a2hlab/ws/out-sp20/webview-candidate/webview-t-lib/libwebviewchromium.so'
base=int(re.search(r'^([0-9a-f]+)-[0-9a-f]+ r-xp 00000000 /data/local/tmp/asx/webview-t-lib/libwebviewchromium.so$',s,re.M)[1],16)
regs={k:int(v,16) for k,v in re.findall(r'\b(pc|lr|x0):([0-9a-f]+)',s)}
result={'faultlog':str(f),'sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'map_base':hex(base),'registers':{k:hex(v) for k,v in regs.items()},'actual_elf_pc':hex(regs['pc']-base),'actual_lr':hex(regs['lr']-base),'callsite':hex(regs['lr']-base-4),'printed_frame0':'0x3e026f0','printed_frame0_error':hex(0x3e026f0-(regs['pc']-base)),'instruction':'ldr x8, [x0]','x0_is_null':regs['x0']==0,'symbol_name':'unknown (stripped library)'}
(r/'mapped.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
toolsdir=pathlib.Path.home()/'a2hlab/ws/toolchains/ohos-sdk/native/llvm/bin'
for label,args in [('elf',['llvm-readelf','-l',str(lib)]),('fault',['llvm-objdump','-d','--start-address=0x1e006e0','--stop-address=0x1e00770',str(lib)]),('caller',['llvm-objdump','-d','--start-address=0x4526f90','--stop-address=0x4527000',str(lib)])]:
 (r/(label+'.txt')).write_text(subprocess.check_output([str(toolsdir/args[0])]+args[1:],text=True))
