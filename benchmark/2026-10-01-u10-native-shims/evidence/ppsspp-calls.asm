00000000010b3ec4 <linkernsbypass_namespace_dlopen>:
 10b3ec4:      	sub	sp, sp, #0x60
 10b3ec8:      	str	x19, [sp, #0x40]
 10b3ecc:      	stp	x29, x30, [sp, #0x50]
 10b3ed0:      	add	x29, sp, #0x50
 10b3ed4:      	mrs	x19, TPIDR_EL0
 10b3ed8:      	ldr	x8, [x19, #0x28]
 10b3edc:      	mov	w9, #0x200              // =512
 10b3ee0:      	movi	v0.2d, #0000000000000000
 10b3ee4:      	stur	x8, [x29, #-0x18]
 10b3ee8:      	str	x2, [sp, #0x30]
 10b3eec:      	add	x2, sp, #0x8
 10b3ef0:      	str	x9, [sp, #0x8]
 10b3ef4:      	stp	q0, q0, [sp, #0x10]
 10b3ef8:      	bl	0x46f980 <android_dlopen_ext@plt>
 10b3efc:      	ldr	x8, [x19, #0x28]
 10b3f00:      	ldur	x9, [x29, #-0x18]
 10b3f04:      	cmp	x8, x9
 10b3f08:      	b.ne	0x10b3f1c <linkernsbypass_namespace_dlopen+0x58>
 10b3f0c:      	ldp	x29, x30, [sp, #0x50]
 10b3f10:      	ldr	x19, [sp, #0x40]
 10b3f14:      	add	sp, sp, #0x60
 10b3f18:      	ret
 10b3f1c:      	bl	0x47bc60 <__stack_chk_fail@plt>

00000000010b3f20 <linkernsbypass_namespace_dlopen_unique>:

 10b400c:      	mov	w1, w22
 10b4010:      	bl	0x487bf0 <elf_soname_patch@plt>
 10b4014:      	tbz	w0, #0x0, 0x10b4064 <linkernsbypass_namespace_dlopen_unique+0x144>
 10b4018:      	stp	xzr, x20, [sp, #0x20]
 10b401c:      	adrp	x20, 0x19e0000 <_ZN12ExampleAsset20s_current_sort_specsE+0x67f8>
 10b4020:      	add	x20, x20, #0x640
 10b4024:      	adrp	x3, 0x13ee000 <_ZTSN6snappy22UncheckedByteArraySinkE+0x1dc05>
 10b4028:      	mov	w8, #0x210              // =528
 10b402c:      	add	x3, x3, #0x126
 10b4030:      	mov	w1, #0x1000             // =4096
 10b4034:      	mov	w2, #0x1000             // =4096
 10b4038:      	mov	x0, x20
 10b403c:      	mov	w4, w22
 10b4040:      	stp	xzr, xzr, [sp, #0x8]
 10b4044:      	stp	wzr, w22, [sp, #0x18]
 10b4048:      	str	x8, [sp]
 10b404c:      	bl	0x10b4098 <linkernsbypass_namespace_dlopen_unique+0x178>
 10b4050:      	mov	x2, sp
 10b4054:      	mov	x0, x20
 10b4058:      	mov	w1, w19
 10b405c:      	bl	0x46f980 <android_dlopen_ext@plt>
 10b4060:      	b	0x10b4068 <linkernsbypass_namespace_dlopen_unique+0x148>
 10b4064:      	mov	x0, xzr
 10b4068:      	ldr	x8, [x24, #0x28]
 10b406c:      	ldr	x9, [sp, #0x38]
 10b4070:      	cmp	x8, x9
