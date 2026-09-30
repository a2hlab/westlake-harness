
r155-libart.so:	file format elf64-littleaarch64

Disassembly of section .text:

0000000000807df0 <art_quick_update_inline_cache>:
  807df0: b9400509     	ldr	w9, [x8, #4]
  807df4: 6b00013f     	cmp	w9, w0
  807df8: 540004e0     	b.eq	0x807e94 <art_quick_update_inline_cache+0xa4>
  807dfc: 350000e9     	cbnz	w9, 0x807e18 <art_quick_update_inline_cache+0x28>
  807e00: 9100110a     	add	x10, x8, #4
  807e04: 885f7d49     	ldxr	w9, [x10]
  807e08: 35ffff49     	cbnz	w9, 0x807df0 <art_quick_update_inline_cache>
  807e0c: 88097d40     	stxr	w9, w0, [x10]
  807e10: 34000429     	cbz	w9, 0x807e94 <art_quick_update_inline_cache+0xa4>
  807e14: 17fffff7     	b	0x807df0 <art_quick_update_inline_cache>
  807e18: b9400909     	ldr	w9, [x8, #8]
  807e1c: 6b00013f     	cmp	w9, w0
  807e20: 540003a0     	b.eq	0x807e94 <art_quick_update_inline_cache+0xa4>
  807e24: 350000e9     	cbnz	w9, 0x807e40 <art_quick_update_inline_cache+0x50>
  807e28: 9100210a     	add	x10, x8, #8
  807e2c: 885f7d49     	ldxr	w9, [x10]
  807e30: 35ffff49     	cbnz	w9, 0x807e18 <art_quick_update_inline_cache+0x28>
  807e34: 88097d40     	stxr	w9, w0, [x10]
  807e38: 340002e9     	cbz	w9, 0x807e94 <art_quick_update_inline_cache+0xa4>
  807e3c: 17fffff7     	b	0x807e18 <art_quick_update_inline_cache+0x28>
  807e40: b9400d09     	ldr	w9, [x8, #12]
  807e44: 6b00013f     	cmp	w9, w0
  807e48: 54000260     	b.eq	0x807e94 <art_quick_update_inline_cache+0xa4>
  807e4c: 350000e9     	cbnz	w9, 0x807e68 <art_quick_update_inline_cache+0x78>
  807e50: 9100310a     	add	x10, x8, #12
  807e54: 885f7d49     	ldxr	w9, [x10]
  807e58: 35ffff49     	cbnz	w9, 0x807e40 <art_quick_update_inline_cache+0x50>
  807e5c: 88097d40     	stxr	w9, w0, [x10]
  807e60: 340001a9     	cbz	w9, 0x807e94 <art_quick_update_inline_cache+0xa4>
  807e64: 17fffff7     	b	0x807e40 <art_quick_update_inline_cache+0x50>
  807e68: b9401109     	ldr	w9, [x8, #16]
  807e6c: 6b00013f     	cmp	w9, w0
  807e70: 54000120     	b.eq	0x807e94 <art_quick_update_inline_cache+0xa4>
  807e74: 350000e9     	cbnz	w9, 0x807e90 <art_quick_update_inline_cache+0xa0>
  807e78: 9100410a     	add	x10, x8, #16
  807e7c: 885f7d49     	ldxr	w9, [x10]
  807e80: 35ffff49     	cbnz	w9, 0x807e68 <art_quick_update_inline_cache+0x78>
  807e84: 88097d40     	stxr	w9, w0, [x10]
  807e88: 34000069     	cbz	w9, 0x807e94 <art_quick_update_inline_cache+0xa4>
  807e8c: 17fffff7     	b	0x807e68 <art_quick_update_inline_cache+0x78>
  807e90: b9001500     	str	w0, [x8, #20]
  807e94: d65f03c0     	ret
