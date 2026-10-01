
libbionic_compat-candidate.so:	file format elf64-littleaarch64

Disassembly of section .text:

000000000000373c <android_dlopen_ext>:
    373c: a9bf7bfd     	stp	x29, x30, [sp, #-0x10]!
    3740: 910003fd     	mov	x29, sp
    3744: b0000008     	adrp	x8, 0x4000 <strerror_r@plt+0x5e0>
    3748: f9462508     	ldr	x8, [x8, #0xc48]
    374c: b40000c8     	cbz	x8, 0x3764 <android_dlopen_ext+0x28>
    3750: d50320ff     	xpaclri
    3754: aa1e03e3     	mov	x3, x30
    3758: 940000a6     	bl	0x39f0 <__loader_android_dlopen_ext@plt>
    375c: a8c17bfd     	ldp	x29, x30, [sp], #0x10
    3760: d65f03c0     	ret
    3764: b4000062     	cbz	x2, 0x3770 <android_dlopen_ext+0x34>
    3768: f9400042     	ldr	x2, [x2]
    376c: b5000062     	cbnz	x2, 0x3778 <android_dlopen_ext+0x3c>
    3770: a8c17bfd     	ldp	x29, x30, [sp], #0x10
    3774: 140000a3     	b	0x3a00 <dlopen@plt>
    3778: b0000008     	adrp	x8, 0x4000 <strerror_r@plt+0x5e0>
    377c: d0ffffe9     	adrp	x9, 0x1000 <strncpy+0x1000>
    3780: 91224129     	add	x9, x9, #0x890
    3784: f100001f     	cmp	x0, #0x0
    3788: 9a800123     	csel	x3, x9, x0, eq
    378c: d503201f     	nop
    3790: 30ff08a1     	adr	x1, 0x18a5 <strncpy+0x18a5>
    3794: f9462908     	ldr	x8, [x8, #0xc50]
    3798: f9400108     	ldr	x8, [x8]
    379c: aa0803e0     	mov	x0, x8
    37a0: 9400009c     	bl	0x3a10 <fprintf@plt>
    37a4: 9400006b     	bl	0x3950 <__errno_location@plt>
    37a8: aa0003e8     	mov	x8, x0
    37ac: 52800be9     	mov	w9, #0x5f               // =95
    37b0: aa1f03e0     	mov	x0, xzr
    37b4: b9000109     	str	w9, [x8]
    37b8: a8c17bfd     	ldp	x29, x30, [sp], #0x10
    37bc: d65f03c0     	ret
