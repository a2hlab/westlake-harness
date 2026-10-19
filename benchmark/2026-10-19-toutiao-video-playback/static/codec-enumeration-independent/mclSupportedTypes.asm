
$HOME/.local/share/westlake/toutiao-resume-20261020/media-provider-readonly-0227/liboh_adapter_bridge.so:	file format elf64-littleaarch64

Disassembly of section .text:

00000000000f2f40 <_ZL17mclSupportedTypesP7_JNIEnvP7_jclassi>:
   f2f40: a9bd7bfd     	stp	x29, x30, [sp, #-0x30]!
   f2f44: f9000bf5     	str	x21, [sp, #0x10]
   f2f48: a9024ff4     	stp	x20, x19, [sp, #0x20]
   f2f4c: 910003fd     	mov	x29, sp
   f2f50: f9400008     	ldr	x8, [x0]
   f2f54: aa0003f3     	mov	x19, x0
   f2f58: f9439108     	ldr	x8, [x8, #0x720]
   f2f5c: d63f0100     	blr	x8
   f2f60: 72001c1f     	tst	w0, #0xff
   f2f64: 540000a0     	b.eq	0xf2f78 <_ZL17mclSupportedTypesP7_JNIEnvP7_jclassi+0x38>
   f2f68: f9400268     	ldr	x8, [x19]
   f2f6c: aa1303e0     	mov	x0, x19
   f2f70: f9404508     	ldr	x8, [x8, #0x88]
   f2f74: d63f0100     	blr	x8
   f2f78: f0000408     	adrp	x8, 0x175000 <write+0x175000>
   f2f7c: f9477914     	ldr	x20, [x8, #0xef0]
   f2f80: b5000274     	cbnz	x20, 0xf2fcc <_ZL17mclSupportedTypesP7_JNIEnvP7_jclassi+0x8c>
   f2f84: f9400268     	ldr	x8, [x19]
   f2f88: b0fffca1     	adrp	x1, 0x87000 <_ZZN12_GLOBAL__N_19jsonQuoteERKNSt3__h12basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEE4kHex+0xcea1>
   f2f8c: 91270421     	add	x1, x1, #0x9c1
   f2f90: aa1303e0     	mov	x0, x19
   f2f94: f9401908     	ldr	x8, [x8, #0x30]
   f2f98: d63f0100     	blr	x8
   f2f9c: f9400268     	ldr	x8, [x19]
   f2fa0: aa0003f4     	mov	x20, x0
   f2fa4: aa1303e0     	mov	x0, x19
   f2fa8: f9439108     	ldr	x8, [x8, #0x720]
   f2fac: d63f0100     	blr	x8
   f2fb0: 72001c1f     	tst	w0, #0xff
   f2fb4: 540000a0     	b.eq	0xf2fc8 <_ZL17mclSupportedTypesP7_JNIEnvP7_jclassi+0x88>
   f2fb8: f9400268     	ldr	x8, [x19]
   f2fbc: aa1303e0     	mov	x0, x19
   f2fc0: f9404508     	ldr	x8, [x8, #0x88]
   f2fc4: d63f0100     	blr	x8
   f2fc8: b4000434     	cbz	x20, 0xf304c <_ZL17mclSupportedTypesP7_JNIEnvP7_jclassi+0x10c>
   f2fcc: f9400268     	ldr	x8, [x19]
   f2fd0: aa1303e0     	mov	x0, x19
   f2fd4: 52800021     	mov	w1, #0x1                // =1
   f2fd8: aa1403e2     	mov	x2, x20
   f2fdc: aa1f03e3     	mov	x3, xzr
