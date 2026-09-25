#!/usr/bin/env python3
# usage: fnstr.py LIB vaddr...  -> for each vaddr: function start (paciasp heuristic), calls, and referenced strings
import sys, subprocess, re, struct
LIB=sys.argv[1]; OBJ=sys.argv[2]
data=open(LIB,'rb').read()
# section map for vaddr->file offset (PT_LOAD0 vaddr==offset; later loads: parse phdrs)
e_phoff=struct.unpack_from('<Q',data,0x20)[0]; e_phnum=struct.unpack_from('<H',data,0x38)[0]
loads=[]
for i in range(e_phnum):
    p_type,p_flags,p_off,p_vaddr,p_paddr,p_filesz,p_memsz,p_align=struct.unpack_from('<IIQQQQQQ',data,e_phoff+i*56)
    if p_type==1: loads.append((p_vaddr,p_off,p_filesz))
def v2o(v):
    for va,off,sz in loads:
        if va<=v<va+sz: return v-va+off
    return None
def cstr(v):
    o=v2o(v)
    if o is None: return None
    end=data.find(b'\0',o,o+200)
    if end<0: return None
    s=data[o:end]
    if len(s)<3: return None
    try: t=s.decode()
    except: return None
    if not all(32<=ord(c)<127 for c in t): return None
    return t
def dis(a,b):
    out=subprocess.run([OBJ,'-d','--no-show-raw-insn',f'--start-address={a:#x}',f'--stop-address={b:#x}',LIB],capture_output=True,text=True).stdout
    ins=[]
    for line in out.splitlines():
        m=re.match(r'\s*([0-9a-f]+):\s+(\S+)\s*(.*)',line)
        if m: ins.append((int(m.group(1),16),m.group(2),m.group(3)))
    return ins
for arg in sys.argv[3:]:
    pc=int(arg,16)
    win=dis(pc-0x3000,pc+0x3000)
    idx=max(i for i,x in enumerate(win) if x[0]<=pc)
    start=None
    for i in range(idx,-1,-1):
        if win[i][1]=='paciasp' or (i>0 and win[i-1][1] in ('ret','b') and win[i][1] in ('stp','sub','str')):
            start=win[i][0]; break
    end=None
    for i in range(idx+1,len(win)):
        if win[i][1]=='paciasp' and win[i][0]>pc:
            end=win[i][0]; break
    print(f'=== pc {pc:#x}  fn_start {start:#x}  fn_end {end:#x}  size {end-start if end and start else 0}')
    body=[x for x in win if start<=x[0]<(end or pc+4)]
    regs={}
    strs=[];calls=[]
    for a,m,o in body:
        if m=='adrp':
            r=o.split(',')[0]; mm=re.search(r'0x([0-9a-f]+)',o)
            if mm: regs[r]=int(mm.group(1),16)
        elif m=='add' and '#' in o:
            parts=[p.strip() for p in o.split(',')]
            if len(parts)==3 and parts[1] in regs:
                try: v=regs[parts[1]]+int(parts[2].lstrip('#'),0)
                except: continue
                s=cstr(v)
                if s: strs.append((a,s))
        elif m=='bl':
            mm=re.search(r'0x([0-9a-f]+)',o); calls.append((a,int(mm.group(1),16)))
        elif m=='blr':
            calls.append((a,'blr '+o))
    for a,s in strs: print(f'  str@{a:#x}: {s!r}')
    for a,c in calls:
        if abs(a-pc)<=0x20 or a==pc-4: print(f'  call@{a:#x} -> {c if isinstance(c,str) else hex(c)}  <== near pc')
    print(f'  ncalls={len(calls)} callsite_before_pc={[x for x in body if x[0]==pc-4]}')
