
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/platform-link/libframe_ui_intf.z.so:	file format elf64-littleaarch64

Disassembly of section .text:

000000000000a438 <OHOS::RME::BasicOpenRtgNode()>:
    a438: d503237f     	pacibsp
    a43c: d10103ff     	sub	sp, sp, #0x40
    a440: a9027bfd     	stp	x29, x30, [sp, #0x20]
    a444: f9001bf3     	str	x19, [sp, #0x30]
    a448: 910083fd     	add	x29, sp, #0x20
    a44c: d503201f     	nop
    a450: 70fcd448     	adr	x8, 0x3edb
    a454: d0ffffc1     	adrp	x1, 0x4000
    a458: 91096421     	add	x1, x1, #0x259
    a45c: 910003e0     	mov	x0, sp
    a460: 3dc00100     	ldr	q0, [x8]
    a464: 3cc0a101     	ldur	q1, [x8, #0xa]
    a468: 3d8003e0     	str	q0, [sp]
    a46c: 3c80a3e1     	stur	q1, [sp, #0xa]
    a470: 940004c0     	bl	0xb770 <fopen@plt>
    a474: f0000008     	adrp	x8, 0xd000
    a478: f9073900     	str	x0, [x8, #0xe70]
    a47c: b4000240     	cbz	x0, 0xa4c4 <OHOS::RME::BasicOpenRtgNode()+0x8c>
    a480: 940004c8     	bl	0xb7a0 <fileno@plt>
    a484: f0000008     	adrp	x8, 0xd000
    a488: b90dd900     	str	w0, [x8, #0xdd8]
    a48c: 37f802e0     	tbnz	w0, #0x1f, 0xa4e8 <OHOS::RME::BasicOpenRtgNode()+0xb0>
    a490: a9427bfd     	ldp	x29, x30, [sp, #0x20]
    a494: 5282e0c2     	mov	w2, #0x1706             // =5894
    a498: b0ffffc3     	adrp	x3, 0x3000
    a49c: 913cac63     	add	x3, x3, #0xf2b
    a4a0: f9401bf3     	ldr	x19, [sp, #0x30]
    a4a4: b0ffffc4     	adrp	x4, 0x3000
    a4a8: 91309084     	add	x4, x4, #0xc24
    a4ac: 52800060     	mov	w0, #0x3                // =3
    a4b0: 52800081     	mov	w1, #0x4                // =4
    a4b4: 72a1a002     	movk	w2, #0xd00, lsl #16
    a4b8: 910103ff     	add	sp, sp, #0x40
    a4bc: d50323ff     	autibsp
    a4c0: 14000408     	b	0xb4e0 <HiLogPrint@plt>
