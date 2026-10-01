
libc.so:	file format elf64-littleaarch64

Disassembly of section .text:

0000000000129748 <strerror_r>:
  129748: a9bd7bfd     	stp	x29, x30, [sp, #-0x30]!
  12974c: f9000bf5     	str	x21, [sp, #0x10]
  129750: a9024ff4     	stp	x20, x19, [sp, #0x20]
  129754: 910003fd     	mov	x29, sp
  129758: 71020c1f     	cmp	w0, #0x83
  12975c: d503201f     	nop
  129760: 10858e4a     	adr	x10, 0x34928
  129764: 1a8083e9     	csel	w9, wzr, w0, hi
  129768: d53bd048     	mrs	x8, TPIDR_EL0
  12976c: aa0203f4     	mov	x20, x2
  129770: f8518108     	ldur	x8, [x8, #-0xe8]
  129774: aa0103f3     	mov	x19, x1
  129778: 78695949     	ldrh	w9, [x10, w9, uxtw #1]
  12977c: d503201f     	nop
  129780: 5085516a     	adr	x10, 0x341ae
  129784: f9401508     	ldr	x8, [x8, #0x28]
  129788: 8b090155     	add	x21, x10, x9
  12978c: b40000a8     	cbz	x8, 0x1297a0 <strerror_r+0x58>
  129790: a9400500     	ldp	x0, x1, [x8]
  129794: aa1503e2     	mov	x2, x21
  129798: 97fe9452     	bl	0xce8e0 <fremovexattr+0x7c>
  12979c: 14000002     	b	0x1297a4 <strerror_r+0x5c>
  1297a0: aa1f03e0     	mov	x0, xzr
  1297a4: f100001f     	cmp	x0, #0x0
  1297a8: 9a8002b5     	csel	x21, x21, x0, eq
  1297ac: aa1503e0     	mov	x0, x21
  1297b0: 97fdbd14     	bl	0x98c00 <strlen>
  1297b4: eb14001f     	cmp	x0, x20
  1297b8: 540000e2     	b.hs	0x1297d4 <strerror_r+0x8c>
  1297bc: 91000402     	add	x2, x0, #0x1
  1297c0: aa1303e0     	mov	x0, x19
  1297c4: aa1503e1     	mov	x1, x21
  1297c8: 97fdbabe     	bl	0x982c0 <memmove>
  1297cc: 2a1f03e0     	mov	w0, wzr
  1297d0: 1400000b     	b	0x1297fc <strerror_r+0xb4>
  1297d4: b4000134     	cbz	x20, 0x1297f8 <strerror_r+0xb0>
  1297d8: d1000694     	sub	x20, x20, #0x1
  1297dc: aa1303e0     	mov	x0, x19
  1297e0: aa1503e1     	mov	x1, x21
  1297e4: aa1403e2     	mov	x2, x20
  1297e8: 97fdbab6     	bl	0x982c0 <memmove>
  1297ec: 52800440     	mov	w0, #0x22               // =34
  1297f0: 38346a7f     	strb	wzr, [x19, x20]
  1297f4: 14000002     	b	0x1297fc <strerror_r+0xb4>
  1297f8: 52800440     	mov	w0, #0x22               // =34
  1297fc: a9424ff4     	ldp	x20, x19, [sp, #0x20]
  129800: f9400bf5     	ldr	x21, [sp, #0x10]
  129804: a8c37bfd     	ldp	x29, x30, [sp], #0x30
  129808: d65f03c0     	ret
