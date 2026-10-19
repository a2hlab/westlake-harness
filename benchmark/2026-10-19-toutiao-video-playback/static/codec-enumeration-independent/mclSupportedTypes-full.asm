
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
   f2fe0: f942b108     	ldr	x8, [x8, #0x560]
   f2fe4: d63f0100     	blr	x8
   f2fe8: aa0003f4     	mov	x20, x0
   f2fec: b40003c0     	cbz	x0, 0xf3064 <_ZL17mclSupportedTypesP7_JNIEnvP7_jclassi+0x124>
   f2ff0: f9400268     	ldr	x8, [x19]
   f2ff4: 90fffc01     	adrp	x1, 0x72000 <write+0x72000>
   f2ff8: 913e3421     	add	x1, x1, #0xf8d
   f2ffc: aa1303e0     	mov	x0, x19
   f3000: f9429d08     	ldr	x8, [x8, #0x538]
   f3004: d63f0100     	blr	x8
   f3008: b40001e0     	cbz	x0, 0xf3044 <_ZL17mclSupportedTypesP7_JNIEnvP7_jclassi+0x104>
   f300c: f9400268     	ldr	x8, [x19]
   f3010: aa0003f5     	mov	x21, x0
   f3014: aa1303e0     	mov	x0, x19
   f3018: aa1403e1     	mov	x1, x20
   f301c: 2a1f03e2     	mov	w2, wzr
   f3020: aa1503e3     	mov	x3, x21
   f3024: f942b908     	ldr	x8, [x8, #0x570]
   f3028: d63f0100     	blr	x8
   f302c: f9400268     	ldr	x8, [x19]
   f3030: aa1303e0     	mov	x0, x19
   f3034: aa1503e1     	mov	x1, x21
   f3038: f9405d08     	ldr	x8, [x8, #0xb8]
   f303c: d63f0100     	blr	x8
   f3040: 14000009     	b	0xf3064 <_ZL17mclSupportedTypesP7_JNIEnvP7_jclassi+0x124>
   f3044: aa1f03f4     	mov	x20, xzr
   f3048: 14000007     	b	0xf3064 <_ZL17mclSupportedTypesP7_JNIEnvP7_jclassi+0x124>
   f304c: b0fffc41     	adrp	x1, 0x7c000 <_ZZN12_GLOBAL__N_19jsonQuoteERKNSt3__h12basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEE4kHex+0x1ea1>
   f3050: 91019c21     	add	x1, x1, #0x67
   f3054: d0fffc02     	adrp	x2, 0x75000 <write+0x75000>
   f3058: 91123842     	add	x2, x2, #0x48e
   f305c: 528000c0     	mov	w0, #0x6                // =6
