
$HOME/.local/share/westlake/toutiao-resume-20261020/media-provider-readonly-0227/liboh_adapter_bridge.so:	file format elf64-littleaarch64

Disassembly of section .text:

00000000000f2e90 <_ZL10mclGetNameP7_JNIEnvP7_jclassi>:
   f2e90: f9400008     	ldr	x8, [x0]
   f2e94: b0fffca1     	adrp	x1, 0x87000 <_ZZN12_GLOBAL__N_19jsonQuoteERKNSt3__h12basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEE4kHex+0xcea1>
   f2e98: 912db421     	add	x1, x1, #0xb6d
   f2e9c: f9429d02     	ldr	x2, [x8, #0x538]
   f2ea0: d61f0040     	br	x2

00000000000f2ea4 <_ZL15mclGetCanonicalP7_JNIEnvP7_jclassi>:
   f2ea4: f9400008     	ldr	x8, [x0]
   f2ea8: b0fffca1     	adrp	x1, 0x87000 <_ZZN12_GLOBAL__N_19jsonQuoteERKNSt3__h12basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEE4kHex+0xcea1>
   f2eac: 912db421     	add	x1, x1, #0xb6d
   f2eb0: f9429d02     	ldr	x2, [x8, #0x538]
   f2eb4: d61f0040     	br	x2

00000000000f2eb8 <_ZL16mclGetAttributesP7_JNIEnvP7_jclassi>:
   f2eb8: 2a1f03e0     	mov	w0, wzr
   f2ebc: d65f03c0     	ret

00000000000f2ec0 <_ZL13mclFindByNameP7_JNIEnvP7_jclassP8_jstring>:
   f2ec0: a9bd7bfd     	stp	x29, x30, [sp, #-0x30]!
   f2ec4: a90157f6     	stp	x22, x21, [sp, #0x10]
   f2ec8: a9024ff4     	stp	x20, x19, [sp, #0x20]
   f2ecc: 910003fd     	mov	x29, sp
   f2ed0: b40002c2     	cbz	x2, 0xf2f28 <_ZL13mclFindByNameP7_JNIEnvP7_jclassP8_jstring+0x68>
   f2ed4: f9400008     	ldr	x8, [x0]
   f2ed8: aa0203f3     	mov	x19, x2
   f2edc: aa0203e1     	mov	x1, x2
   f2ee0: aa1f03e2     	mov	x2, xzr
   f2ee4: aa0003f4     	mov	x20, x0
   f2ee8: f942a508     	ldr	x8, [x8, #0x548]
   f2eec: d63f0100     	blr	x8
   f2ef0: b40001c0     	cbz	x0, 0xf2f28 <_ZL13mclFindByNameP7_JNIEnvP7_jclassP8_jstring+0x68>
   f2ef4: b0fffca1     	adrp	x1, 0x87000 <_ZZN12_GLOBAL__N_19jsonQuoteERKNSt3__h12basic_stringIcNS0_11char_traitsIcEENS0_9allocatorIcEEEEE4kHex+0xcea1>
   f2ef8: 912db421     	add	x1, x1, #0xb6d
   f2efc: aa0003f6     	mov	x22, x0
   f2f00: 9401b5a8     	bl	0x1605a0 <strcmp@plt>
   f2f04: f9400288     	ldr	x8, [x20]
   f2f08: 7100001f     	cmp	w0, #0x0
   f2f0c: aa1403e0     	mov	x0, x20
   f2f10: aa1303e1     	mov	x1, x19
   f2f14: aa1603e2     	mov	x2, x22
   f2f18: 5a9f03f5     	csetm	w21, ne
   f2f1c: f942a908     	ldr	x8, [x8, #0x550]
   f2f20: d63f0100     	blr	x8
   f2f24: 14000002     	b	0xf2f2c <_ZL13mclFindByNameP7_JNIEnvP7_jclassP8_jstring+0x6c>
   f2f28: 12800015     	mov	w21, #-0x1              // =-1
   f2f2c: 2a1503e0     	mov	w0, w21
