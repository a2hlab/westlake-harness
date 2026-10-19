#!/usr/bin/env python3
# Logic probe for the slot-liveness / packed-reloc gates ONLY. NOT a deploy entry:
# derive_mffmpeg.py is SHA-pinned to fecf91e1 and that pin subsumes these gates on the
# real input (its sole slot is already null). This probe mirrors derive_mffmpeg.py's
# reloc_val() + kept-loop verbatim, with the input SHA pin removed, to show the gate
# refuses a library whose init slot is live. Keep in sync with derive_mffmpeg.py.
import sys, struct
d = open(sys.argv[1], "rb").read()
W = lambda o: struct.unpack_from("<Q", d, o)[0]; H = lambda o: struct.unpack_from("<H", d, o)[0]
phoff, phent, phnum = W(0x20), H(0x36), H(0x38)
def seg(va):
    for i in range(phnum):
        ph = phoff+i*phent
        if W(ph)&0xffffffff!=1: continue
        off,v,fsz=W(ph+8),W(ph+0x10),W(ph+0x20)
        if v<=va<v+fsz: return off+(va-v)
    return None
do=dz=0
for i in range(phnum):
    ph=phoff+i*phent
    if W(ph)&0xffffffff==2: do,dz=W(ph+8),W(ph+0x20); break
ia=iasz=rela=relasz=jmprel=pltsz=pltrel=0; packed=False; o=do
while o+16<=do+dz:
    t,v=W(o),W(o+8)
    if t==0: break
    if t==25: ia=v
    elif t==27: iasz=v
    elif t==7: rela=v
    elif t==8: relasz=v
    elif t==23: jmprel=v
    elif t==2: pltsz=v
    elif t==20: pltrel=v
    elif t in (35,36,0x6000000d,0x6000000e,0x6000000f,0x60000010): packed=True
    o+=16
if packed: sys.exit("REJECT: packed/undecodable relocs")
ao=seg(ia)
def reloc_val(slot_va, stored):
    for base,sz in ((rela,relasz),(jmprel if pltrel==7 else 0,pltsz)):
        if base==0 or sz<24: continue
        to=seg(base)
        if to is None: continue
        r=0
        while r+24<=sz:
            if W(to+r)==slot_va:
                ty=W(to+r+8)&0xffffffff; return W(to+r+16) if ty==1027 else 1
            r+=24
    return stored
kept=sum(1 for i in range(iasz//8) if reloc_val(ia+i*8, W(ao+i*8)) not in (0,(1<<64)-1))
if kept: sys.exit(f"REJECT: {kept} of {iasz//8} init slot(s) live/relocated -- refusing to drop a real constructor")
print(f"OK all {iasz//8} slot(s) null -> safe to set INIT_ARRAYSZ=0")
