
r155-libart.so:	file format elf64-littleaarch64

Disassembly of section .text:

0000000000461b1c <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)>:
  461b1c: d10403ff     	sub	sp, sp, #256
  461b20: a90a7bfd     	stp	x29, x30, [sp, #160]
  461b24: a90b6ffc     	stp	x28, x27, [sp, #176]
  461b28: a90c67fa     	stp	x26, x25, [sp, #192]
  461b2c: a90d5ff8     	stp	x24, x23, [sp, #208]
  461b30: a90e57f6     	stp	x22, x21, [sp, #224]
  461b34: a90f4ff4     	stp	x20, x19, [sp, #240]
  461b38: 910283fd     	add	x29, sp, #160
  461b3c: aa0603f3     	mov	x19, x6
  461b40: aa0503f9     	mov	x25, x5
  461b44: aa0403f5     	mov	x21, x4
  461b48: aa0303f7     	mov	x23, x3
  461b4c: aa0203fa     	mov	x26, x2
  461b50: aa0103f4     	mov	x20, x1
  461b54: aa0003f8     	mov	x24, x0
  461b58: 940aa467     	bl	0x70acf4 <art::OatFile::GetOatHeader() const>
  461b5c: 91002302     	add	x2, x24, #8
  461b60: aa1303e1     	mov	x1, x19
  461b64: aa1403e3     	mov	x3, x20
  461b68: 94000f62     	bl	0x4658f0 <art::gc::space::ImageSpace::ValidateApexVersions(art::OatHeader const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)>
  461b6c: f0002748     	adrp	x8, 0x94c000 <art::gc::space::ImageSpace::BootImageLayout::CompileBootclasspathElements(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, unsigned long, std::__h::vector<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>, std::__h::allocator<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>>> const&, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x700>
  461b70: f9427108     	ldr	x8, [x8, #1248]
  461b74: f9400113     	ldr	x19, [x8]
  461b78: 360025c0     	tbz	w0, #0, 0x462030 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x514>
  461b7c: d0ffee60     	adrp	x0, 0x22f000 <art::gc::space::ImageSpace::BootImageLayout::MatchNamedComponents(art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, std::__h::vector<art::gc::space::ImageSpace::BootImageLayout::NamedComponentLocation, std::__h::allocator<art::gc::space::ImageSpace::BootImageLayout::NamedComponentLocation>>*, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x7f0>
  461b80: 9115c800     	add	x0, x0, #1394
  461b84: 52800221     	mov	w1, #17
  461b88: 52800022     	mov	w2, #1
  461b8c: aa1303e3     	mov	x3, x19
  461b90: 941360e4     	bl	0x939f20 <fwrite@plt>
  461b94: aa1303e0     	mov	x0, x19
  461b98: 941360e6     	bl	0x939f30 <fflush@plt>
  461b9c: aa1803e0     	mov	x0, x24
  461ba0: 940aa455     	bl	0x70acf4 <art::OatFile::GetOatHeader() const>
  461ba4: 940a9857     	bl	0x707d00 <art::OatHeader::GetKeyValueStoreSize() const>
  461ba8: 340000a0     	cbz	w0, 0x461bbc <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0xa0>
  461bac: aa1803e0     	mov	x0, x24
  461bb0: 940aa451     	bl	0x70acf4 <art::OatFile::GetOatHeader() const>
  461bb4: 940a99d2     	bl	0x7082fc <art::OatHeader::IsConcurrentCopying() const>
  461bb8: 37002720     	tbnz	w0, #0, 0x46209c <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x580>
  461bbc: a9485b1b     	ldp	x27, x22, [x24, #128]
  461bc0: eb16037f     	cmp	x27, x22
  461bc4: 540023e0     	b.eq	0x462040 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x524>
  461bc8: 91002708     	add	x8, x24, #9
  461bcc: a902dffa     	stp	x26, x23, [sp, #40]
  461bd0: aa1f03fa     	mov	x26, xzr
  461bd4: 91000689     	add	x9, x20, #1
  461bd8: f90013f9     	str	x25, [sp, #32]
  461bdc: a90123f5     	stp	x21, x8, [sp, #16]
  461be0: 910143e8     	add	x8, sp, #80
  461be4: b2400108     	orr	x8, x8, #0x1
  461be8: a90023e9     	stp	x9, x8, [sp]
  461bec: 14000007     	b	0x461c08 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0xec>
  461bf0: f94013f9     	ldr	x25, [sp, #32]
  461bf4: 34002297     	cbz	w23, 0x462044 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x528>
  461bf8: 9100075a     	add	x26, x26, #1
  461bfc: 9100237b     	add	x27, x27, #8
  461c00: eb16037f     	cmp	x27, x22
  461c04: 540021e0     	b.eq	0x462040 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x524>
  461c08: f9400375     	ldr	x21, [x27]
  461c0c: aa1503f7     	mov	x23, x21
  461c10: f9400ea9     	ldr	x9, [x21, #24]
  461c14: 910026aa     	add	x10, x21, #9
  461c18: 38408ee8     	ldrb	w8, [x23, #8]!
  461c1c: 7200011f     	tst	w8, #0x1
  461c20: 9a890140     	csel	x0, x10, x9, eq
  461c24: 94136383     	bl	0x93aa30 <_ZN3art13DexFileLoader18IsMultiDexLocationEPKc@plt>
  461c28: 3707fea0     	tbnz	w0, #0, 0x461bfc <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0xe0>
  461c2c: f94017e8     	ldr	x8, [sp, #40]
  461c30: 52800309     	mov	w9, #24
  461c34: 9b092348     	madd	x8, x26, x9, x8
  461c38: f9401be9     	ldr	x9, [sp, #48]
  461c3c: f100013f     	cmp	x9, #0
  461c40: 9a8802f7     	csel	x23, x23, x8, eq
  461c44: eb19035f     	cmp	x26, x25
  461c48: 54000082     	b.hs	0x461c58 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x13c>
  461c4c: f9400be8     	ldr	x8, [sp, #16]
  461c50: b87a791c     	ldr	w28, [x8, x26, lsl #2]
  461c54: 14000002     	b	0x461c5c <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x140>
  461c58: 1280001c     	mov	w28, #-1
  461c5c: a93e7fbf     	stp	xzr, xzr, [x29, #-32]
  461c60: aa1303e0     	mov	x0, x19
  461c64: f81f03bf     	stur	xzr, [x29, #-16]
  461c68: f0ffeda1     	adrp	x1, 0x218000 <art::gc::space::ImageSpace::BootImageLayout::MatchNamedComponents(art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, std::__h::vector<art::gc::space::ImageSpace::BootImageLayout::NamedComponentLocation, std::__h::allocator<art::gc::space::ImageSpace::BootImageLayout::NamedComponentLocation>>*, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x880>
  461c6c: 911fe821     	add	x1, x1, #2042
  461c70: a93d7fbf     	stp	xzr, xzr, [x29, #-48]
  461c74: f81c83bf     	stur	xzr, [x29, #-56]
  461c78: f9400ae9     	ldr	x9, [x23, #16]
  461c7c: 394002e8     	ldrb	w8, [x23]
  461c80: aa1a03e2     	mov	x2, x26
  461c84: 7200011f     	tst	w8, #0x1
  461c88: 9a971523     	csinc	x3, x9, x23, ne
  461c8c: 94135f81     	bl	0x939a90 <fprintf@plt>
  461c90: aa1303e0     	mov	x0, x19
  461c94: 941360a7     	bl	0x939f30 <fflush@plt>
  461c98: 394002e8     	ldrb	w8, [x23]
  461c9c: f9400ae9     	ldr	x9, [x23, #16]
  461ca0: 7200011f     	tst	w8, #0x1
  461ca4: 9a971520     	csinc	x0, x9, x23, ne
  461ca8: d10083a1     	sub	x1, x29, #32
  461cac: d100e3a2     	sub	x2, x29, #56
  461cb0: aa1403e3     	mov	x3, x20
  461cb4: 2a1c03e4     	mov	w4, w28
  461cb8: aa1f03e5     	mov	x5, xzr
  461cbc: 9413611d     	bl	0x93a130 <_ZN3art16ArtDexFileLoader20GetMultiDexChecksumsEPKcPNSt3__h6vectorIjNS3_9allocatorIjEEEEPNS4_INS3_12basic_stringIcNS3_11char_traitsIcEENS5_IcEEEENS5_ISD_EEEEPSD_iPb@plt>
  461cc0: 910006f9     	add	x25, x23, #1
  461cc4: 36000ec0     	tbz	w0, #0, 0x461e9c <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x380>
  461cc8: a97e27a8     	ldp	x8, x9, [x29, #-32]
  461ccc: eb09011f     	cmp	x8, x9
  461cd0: 54001840     	b.eq	0x461fd8 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x4bc>
  461cd4: b9400104     	ldr	w4, [x8]
  461cd8: b9403aa3     	ldr	w3, [x21, #56]
  461cdc: 6b03009f     	cmp	w4, w3
  461ce0: 54000501     	b.ne	0x461d80 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x264>
  461ce4: f85e83a9     	ldur	x9, [x29, #-24]
  461ce8: cb080128     	sub	x8, x9, x8
  461cec: f100151f     	cmp	x8, #5
  461cf0: 540007c3     	b.lo	0x461de8 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x2cc>
  461cf4: 5280003c     	mov	w28, #1
  461cf8: f94007f5     	ldr	x21, [sp, #8]
  461cfc: 14000006     	b	0x461d14 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x1f8>
  461d00: f85e83a9     	ldur	x9, [x29, #-24]
  461d04: 9100079c     	add	x28, x28, #1
  461d08: cb080128     	sub	x8, x9, x8
  461d0c: eb880b9f     	cmp	x28, x8, asr #2
  461d10: 540006c2     	b.hs	0x461de8 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x2cc>
  461d14: 394002e8     	ldrb	w8, [x23]
  461d18: f9400ae9     	ldr	x9, [x23, #16]
  461d1c: 7200011f     	tst	w8, #0x1
  461d20: 9a890321     	csel	x1, x25, x9, eq
  461d24: 910143e8     	add	x8, sp, #80
  461d28: aa1c03e0     	mov	x0, x28
  461d2c: 94136345     	bl	0x93aa40 <_ZN3art13DexFileLoader19GetMultiDexLocationEmPKc@plt>
  461d30: 394143e8     	ldrb	w8, [sp, #80]
  461d34: f94033e9     	ldr	x9, [sp, #96]
  461d38: 7200011f     	tst	w8, #0x1
  461d3c: 9a8902a1     	csel	x1, x21, x9, eq
  461d40: aa1803e0     	mov	x0, x24
  461d44: aa1f03e2     	mov	x2, xzr
  461d48: aa1403e3     	mov	x3, x20
  461d4c: 940aaba3     	bl	0x70cbd8 <art::OatFile::GetOatDexFile(char const*, unsigned int const*, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*) const>
  461d50: b4000560     	cbz	x0, 0x461dfc <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x2e0>
  461d54: f85e03a8     	ldur	x8, [x29, #-32]
  461d58: b9403803     	ldr	w3, [x0, #56]
  461d5c: b87c7904     	ldr	w4, [x8, x28, lsl #2]
  461d60: 6b03009f     	cmp	w4, w3
  461d64: 54000681     	b.ne	0x461e34 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x318>
  461d68: 394143e9     	ldrb	w9, [sp, #80]
  461d6c: 3607fca9     	tbz	w9, #0, 0x461d00 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x1e4>
  461d70: f94033e0     	ldr	x0, [sp, #96]
  461d74: 94135e83     	bl	0x939780 <_ZdlPv@plt>
  461d78: f85e03a8     	ldur	x8, [x29, #-32]
  461d7c: 17ffffe1     	b	0x461d00 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x1e4>
  461d80: 39402308     	ldrb	w8, [x24, #8]
  461d84: f9400f09     	ldr	x9, [x24, #24]
  461d88: 394002ea     	ldrb	w10, [x23]
  461d8c: 7200011f     	tst	w8, #0x1
  461d90: f9400fe8     	ldr	x8, [sp, #24]
  461d94: f9400aeb     	ldr	x11, [x23, #16]
  461d98: 9a890101     	csel	x1, x8, x9, eq
  461d9c: 7200015f     	tst	w10, #0x1
  461da0: 9a8b0322     	csel	x2, x25, x11, eq
  461da4: 910143e8     	add	x8, sp, #80
  461da8: b0ffede0     	adrp	x0, 0x21e000 <art::gc::space::ImageSpace::BootImageLayout::ValidateBootImageChecksum(char const*, art::ImageHeader const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x88>
  461dac: 910f0000     	add	x0, x0, #960
  461db0: 94135ea0     	bl	0x939830 <_ZN7android4base12StringPrintfEPKcz@plt>
  461db4: 39400288     	ldrb	w8, [x20]
  461db8: 36000068     	tbz	w8, #0, 0x461dc4 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x2a8>
  461dbc: f9400a80     	ldr	x0, [x20, #16]
  461dc0: 94135e70     	bl	0x939780 <_ZdlPv@plt>
  461dc4: 2a1f03f7     	mov	w23, wzr
  461dc8: 3dc017e0     	ldr	q0, [sp, #80]
  461dcc: f94033e8     	ldr	x8, [sp, #96]
  461dd0: 52800035     	mov	w21, #1
  461dd4: 3d800280     	str	q0, [x20]
  461dd8: f9000a88     	str	x8, [x20, #16]
  461ddc: f85c83b9     	ldur	x25, [x29, #-56]
  461de0: b5000d19     	cbnz	x25, 0x461f80 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x464>
  461de4: 14000078     	b	0x461fc4 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x4a8>
  461de8: 2a1f03f5     	mov	w21, wzr
  461dec: 52800037     	mov	w23, #1
  461df0: f85c83b9     	ldur	x25, [x29, #-56]
  461df4: b5000c79     	cbnz	x25, 0x461f80 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x464>
  461df8: 14000073     	b	0x461fc4 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x4a8>
  461dfc: 39402308     	ldrb	w8, [x24, #8]
  461e00: f9400f09     	ldr	x9, [x24, #24]
  461e04: 394143ea     	ldrb	w10, [sp, #80]
  461e08: 7200011f     	tst	w8, #0x1
  461e0c: f9400fe8     	ldr	x8, [sp, #24]
  461e10: f94033eb     	ldr	x11, [sp, #96]
  461e14: 9a890101     	csel	x1, x8, x9, eq
  461e18: 7200015f     	tst	w10, #0x1
  461e1c: 9a8b02a2     	csel	x2, x21, x11, eq
  461e20: 9100e3e8     	add	x8, sp, #56
  461e24: b0ffeee0     	adrp	x0, 0x23e000 <art::gc::space::ImageSpace::BootImageLayout::ValidateBootImageChecksum(char const*, art::ImageHeader const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x184>
  461e28: 91192c00     	add	x0, x0, #1611
  461e2c: 94135e81     	bl	0x939830 <_ZN7android4base12StringPrintfEPKcz@plt>
  461e30: 1400000e     	b	0x461e68 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x34c>
  461e34: 39402308     	ldrb	w8, [x24, #8]
  461e38: f9400f09     	ldr	x9, [x24, #24]
  461e3c: 394143ea     	ldrb	w10, [sp, #80]
  461e40: 7200011f     	tst	w8, #0x1
  461e44: f9400fe8     	ldr	x8, [sp, #24]
  461e48: f94033eb     	ldr	x11, [sp, #96]
  461e4c: 9a890101     	csel	x1, x8, x9, eq
  461e50: 7200015f     	tst	w10, #0x1
  461e54: 9a8b02a2     	csel	x2, x21, x11, eq
  461e58: 9100e3e8     	add	x8, sp, #56
  461e5c: b0ffede0     	adrp	x0, 0x21e000 <art::gc::space::ImageSpace::BootImageLayout::ValidateBootImageChecksum(char const*, art::ImageHeader const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x13c>
  461e60: 910f0000     	add	x0, x0, #960
  461e64: 94135e73     	bl	0x939830 <_ZN7android4base12StringPrintfEPKcz@plt>
  461e68: 39400288     	ldrb	w8, [x20]
  461e6c: 36000068     	tbz	w8, #0, 0x461e78 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x35c>
  461e70: f9400a80     	ldr	x0, [x20, #16]
  461e74: 94135e43     	bl	0x939780 <_ZdlPv@plt>
  461e78: f94027e8     	ldr	x8, [sp, #72]
  461e7c: 3cc383e0     	ldur	q0, [sp, #56]
  461e80: f9000a88     	str	x8, [x20, #16]
  461e84: 394143e8     	ldrb	w8, [sp, #80]
  461e88: 3d800280     	str	q0, [x20]
  461e8c: 36000728     	tbz	w8, #0, 0x461f70 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x454>
  461e90: f94033e0     	ldr	x0, [sp, #96]
  461e94: 94135e3b     	bl	0x939780 <_ZdlPv@plt>
  461e98: 14000036     	b	0x461f70 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x454>
  461e9c: 394002e8     	ldrb	w8, [x23]
  461ea0: b0ffed63     	adrp	x3, 0x20e000 <art::gc::space::ImageSpace::BootImageLayout::ValidateBootImageChecksum(char const*, art::ImageHeader const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x140>
  461ea4: 91253c63     	add	x3, x3, #2383
  461ea8: f9400ae9     	ldr	x9, [x23, #16]
  461eac: f94003f5     	ldr	x21, [sp]
  461eb0: 7200011f     	tst	w8, #0x1
  461eb4: 9a890322     	csel	x2, x25, x9, eq
  461eb8: b40000b4     	cbz	x20, 0x461ecc <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x3b0>
  461ebc: 39400288     	ldrb	w8, [x20]
  461ec0: f9400a89     	ldr	x9, [x20, #16]
  461ec4: 7200011f     	tst	w8, #0x1
  461ec8: 9a8902a3     	csel	x3, x21, x9, eq
  461ecc: aa1303e0     	mov	x0, x19
  461ed0: f0ffed41     	adrp	x1, 0x20c000 <art::gc::space::ImageSpace::BootImageLayout::ValidateBootImageChecksum(char const*, art::ImageHeader const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x168>
  461ed4: 9118ac21     	add	x1, x1, #1579
  461ed8: 94135eee     	bl	0x939a90 <fprintf@plt>
  461edc: aa1303e0     	mov	x0, x19
  461ee0: 94136014     	bl	0x939f30 <fflush@plt>
  461ee4: 394002e8     	ldrb	w8, [x23]
  461ee8: f9400ae9     	ldr	x9, [x23, #16]
  461eec: 3940230a     	ldrb	w10, [x24, #8]
  461ef0: 7200011f     	tst	w8, #0x1
  461ef4: f9400f0b     	ldr	x11, [x24, #24]
  461ef8: 3940028c     	ldrb	w12, [x20]
  461efc: 9a890321     	csel	x1, x25, x9, eq
  461f00: f9400fe9     	ldr	x9, [sp, #24]
  461f04: 7200015f     	tst	w10, #0x1
  461f08: f9400a88     	ldr	x8, [x20, #16]
  461f0c: 9a8b0122     	csel	x2, x9, x11, eq
  461f10: 7200019f     	tst	w12, #0x1
  461f14: 9a8802a3     	csel	x3, x21, x8, eq
  461f18: 910143e8     	add	x8, sp, #80
  461f1c: b0ffed60     	adrp	x0, 0x20e000 <art::gc::space::ImageSpace::BootImageLayout::ValidateHeader(art::ImageHeader const&, unsigned long, char const*, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x30>
  461f20: 91271400     	add	x0, x0, #2501
  461f24: 94135e43     	bl	0x939830 <_ZN7android4base12StringPrintfEPKcz@plt>
  461f28: 39400288     	ldrb	w8, [x20]
  461f2c: 36000068     	tbz	w8, #0, 0x461f38 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x41c>
  461f30: f9400a80     	ldr	x0, [x20, #16]
  461f34: 94135e13     	bl	0x939780 <_ZdlPv@plt>
  461f38: 3dc017e0     	ldr	q0, [sp, #80]
  461f3c: aa1303e0     	mov	x0, x19
  461f40: f94033e8     	ldr	x8, [sp, #96]
  461f44: d0ffee41     	adrp	x1, 0x22b000 <art::gc::space::ImageSpace::BootImageLayout::ValidateOatFile(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, unsigned long, unsigned long, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0xc>
  461f48: 9107a421     	add	x1, x1, #489
  461f4c: 3d800280     	str	q0, [x20]
  461f50: f9000a88     	str	x8, [x20, #16]
  461f54: 39400288     	ldrb	w8, [x20]
  461f58: f9400a89     	ldr	x9, [x20, #16]
  461f5c: 7200011f     	tst	w8, #0x1
  461f60: 9a8902a2     	csel	x2, x21, x9, eq
  461f64: 94135ecb     	bl	0x939a90 <fprintf@plt>
  461f68: aa1303e0     	mov	x0, x19
  461f6c: 94135ff1     	bl	0x939f30 <fflush@plt>
  461f70: 2a1f03f7     	mov	w23, wzr
  461f74: 52800035     	mov	w21, #1
  461f78: f85c83b9     	ldur	x25, [x29, #-56]
  461f7c: b4000259     	cbz	x25, 0x461fc4 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x4a8>
  461f80: f85d03a8     	ldur	x8, [x29, #-48]
  461f84: aa1903e0     	mov	x0, x25
  461f88: eb19011f     	cmp	x8, x25
  461f8c: 54000180     	b.eq	0x461fbc <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x4a0>
  461f90: aa0803fc     	mov	x28, x8
  461f94: 14000004     	b	0x461fa4 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x488>
  461f98: aa1c03e8     	mov	x8, x28
  461f9c: eb19039f     	cmp	x28, x25
  461fa0: 540000c0     	b.eq	0x461fb8 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x49c>
  461fa4: 385e8f89     	ldrb	w9, [x28, #-24]!
  461fa8: 3607ff89     	tbz	w9, #0, 0x461f98 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x47c>
  461fac: f85f8100     	ldur	x0, [x8, #-8]
  461fb0: 94135df4     	bl	0x939780 <_ZdlPv@plt>
  461fb4: 17fffff9     	b	0x461f98 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x47c>
  461fb8: f85c83a0     	ldur	x0, [x29, #-56]
  461fbc: f81d03b9     	stur	x25, [x29, #-48]
  461fc0: 94135df0     	bl	0x939780 <_ZdlPv@plt>
  461fc4: f85e03a0     	ldur	x0, [x29, #-32]
  461fc8: b4ffe140     	cbz	x0, 0x461bf0 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0xd4>
  461fcc: f81e83a0     	stur	x0, [x29, #-24]
  461fd0: 94135dec     	bl	0x939780 <_ZdlPv@plt>
  461fd4: 17ffff07     	b	0x461bf0 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0xd4>
  461fd8: 910143e0     	add	x0, sp, #80
  461fdc: d0ffeea1     	adrp	x1, 0x237000 <art::gc::space::ImageSpace::BootImageLayout::ValidateOatFile(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, unsigned long, unsigned long, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0xd4>
  461fe0: 91211c21     	add	x1, x1, #2119
  461fe4: 5281ba42     	mov	w2, #3538
  461fe8: 528000c3     	mov	w3, #6
  461fec: aa1f03e4     	mov	x4, xzr
  461ff0: 12800005     	mov	w5, #-1
  461ff4: 94135df7     	bl	0x9397d0 <_ZN7android4base10LogMessageC1EPKcjNS0_11LogSeverityES3_i@plt>
  461ff8: 910143e0     	add	x0, sp, #80
  461ffc: 94135df9     	bl	0x9397e0 <_ZN7android4base10LogMessage6streamEv@plt>
  462000: b0ffee41     	adrp	x1, 0x22b000 <art::gc::space::ImageSpace::BootImageLayout::ValidateOatFile(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, unsigned long, unsigned long, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0xc4>
  462004: 91083c21     	add	x1, x1, #527
  462008: 52800402     	mov	w2, #32
  46200c: 97f9a8a7     	bl	0x2cc2a8 <std::__h::basic_ostream<char, std::__h::char_traits<char>>& std::__h::__put_character_sequence<char, std::__h::char_traits<char>>(std::__h::basic_ostream<char, std::__h::char_traits<char>>&, char const*, unsigned long)>
  462010: d0ffee81     	adrp	x1, 0x234000 <art::gc::space::ImageSpace::BootImageLayout::ValidateOatFile(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, unsigned long, unsigned long, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0xf8>
  462014: 913fd021     	add	x1, x1, #4084
  462018: 52800022     	mov	w2, #1
  46201c: 97f9a8a3     	bl	0x2cc2a8 <std::__h::basic_ostream<char, std::__h::char_traits<char>>& std::__h::__put_character_sequence<char, std::__h::char_traits<char>>(std::__h::basic_ostream<char, std::__h::char_traits<char>>&, char const*, unsigned long)>
  462020: 910143e0     	add	x0, sp, #80
  462024: 94135df3     	bl	0x9397f0 <_ZN7android4base10LogMessageD1Ev@plt>
  462028: f85e03a8     	ldur	x8, [x29, #-32]
  46202c: 17ffff2a     	b	0x461cd4 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x1b8>
  462030: b5000114     	cbnz	x20, 0x462050 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x534>
  462034: 90ffed62     	adrp	x2, 0x20e000 <art::gc::space::ImageSpace::BootImageLayout::ValidateOatFile(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, unsigned long, unsigned long, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x84>
  462038: 91253c42     	add	x2, x2, #2383
  46203c: 14000009     	b	0x462060 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x544>
  462040: 52800055     	mov	w21, #2
  462044: 71000abf     	cmp	w21, #2
  462048: 1a9f17e0     	cset	w0, eq
  46204c: 1400000c     	b	0x46207c <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x560>
  462050: 39400288     	ldrb	w8, [x20]
  462054: f9400a89     	ldr	x9, [x20, #16]
  462058: 7200011f     	tst	w8, #0x1
  46205c: 9a941522     	csinc	x2, x9, x20, ne
  462060: f0ffee61     	adrp	x1, 0x231000 <art::gc::space::ImageSpace::BootImageLayout::ValidateOatFile(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, unsigned long, unsigned long, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x13c>
  462064: 9115ec21     	add	x1, x1, #1403
  462068: aa1303e0     	mov	x0, x19
  46206c: 94135e89     	bl	0x939a90 <fprintf@plt>
  462070: aa1303e0     	mov	x0, x19
  462074: 94135faf     	bl	0x939f30 <fflush@plt>
  462078: 2a1f03e0     	mov	w0, wzr
  46207c: a94f4ff4     	ldp	x20, x19, [sp, #240]
  462080: a94e57f6     	ldp	x22, x21, [sp, #224]
  462084: a94d5ff8     	ldp	x24, x23, [sp, #208]
  462088: a94c67fa     	ldp	x26, x25, [sp, #192]
  46208c: a94b6ffc     	ldp	x28, x27, [sp, #176]
  462090: a94a7bfd     	ldp	x29, x30, [sp, #160]
  462094: 910403ff     	add	sp, sp, #256
  462098: d65f03c0     	ret
  46209c: aa1803e0     	mov	x0, x24
  4620a0: 940aa315     	bl	0x70acf4 <art::OatFile::GetOatHeader() const>
  4620a4: 940a9896     	bl	0x7082fc <art::OatHeader::IsConcurrentCopying() const>
  4620a8: 92400008     	and	x8, x0, #0x1
  4620ac: a93effbf     	stp	xzr, xzr, [x29, #-24]
  4620b0: d0002740     	adrp	x0, 0x94c000 <art::gc::space::ImageSpace::BootImageLayout::CompileBootclasspathElements(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, unsigned long, std::__h::vector<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>, std::__h::allocator<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>>> const&, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0xc40>
  4620b4: f81f83bf     	stur	xzr, [x29, #-8]
  4620b8: d10083a3     	sub	x3, x29, #32
  4620bc: 528009a1     	mov	w1, #77
  4620c0: f81e03a8     	stur	x8, [x29, #-32]
  4620c4: d100e3a8     	sub	x8, x29, #56
  4620c8: f9476000     	ldr	x0, [x0, #3776]
  4620cc: 52800ee2     	mov	w2, #119
  4620d0: 94136260     	bl	0x93aa50 <_ZN3fmt2v76detail7vformatENS0_17basic_string_viewIcEENS0_11format_argsE@plt>
  4620d4: 39400288     	ldrb	w8, [x20]
  4620d8: 36000068     	tbz	w8, #0, 0x4620e4 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x5c8>
  4620dc: f9400a80     	ldr	x0, [x20, #16]
  4620e0: 94135da8     	bl	0x939780 <_ZdlPv@plt>
  4620e4: 3cdc83a0     	ldur	q0, [x29, #-56]
  4620e8: d0ffede1     	adrp	x1, 0x220000 <art::gc::space::ImageSpace::BootImageLayout::ValidateOatFile(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, unsigned long, unsigned long, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*)+0x180>
  4620ec: 911d7421     	add	x1, x1, #1885
  4620f0: f85d83a8     	ldur	x8, [x29, #-40]
  4620f4: 3d800280     	str	q0, [x20]
  4620f8: f9000a88     	str	x8, [x20, #16]
  4620fc: 39400288     	ldrb	w8, [x20]
  462100: f9400a89     	ldr	x9, [x20, #16]
  462104: 7200011f     	tst	w8, #0x1
  462108: 9a941522     	csinc	x2, x9, x20, ne
  46210c: 17ffffd7     	b	0x462068 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x54c>
  462110: 14000010     	b	0x462150 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x634>
  462114: aa0003f3     	mov	x19, x0
  462118: 910143e0     	add	x0, sp, #80
  46211c: 94135db5     	bl	0x9397f0 <_ZN7android4base10LogMessageD1Ev@plt>
  462120: 1400000d     	b	0x462154 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x638>
  462124: 14000005     	b	0x462138 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x61c>
  462128: 14000004     	b	0x462138 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x61c>
  46212c: 14000009     	b	0x462150 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x634>
  462130: 14000008     	b	0x462150 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x634>
  462134: 14000007     	b	0x462150 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x634>
  462138: aa0003f3     	mov	x19, x0
  46213c: 394143e8     	ldrb	w8, [sp, #80]
  462140: 360000a8     	tbz	w8, #0, 0x462154 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x638>
  462144: f94033e0     	ldr	x0, [sp, #96]
  462148: 94135d8e     	bl	0x939780 <_ZdlPv@plt>
  46214c: 14000002     	b	0x462154 <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x638>
  462150: aa0003f3     	mov	x19, x0
  462154: d100e3a0     	sub	x0, x29, #56
  462158: 97f9fabc     	bl	0x2e0c48 <std::__h::vector<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>, std::__h::allocator<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>>>::~vector[abi:v15004]()>
  46215c: f85e03a0     	ldur	x0, [x29, #-32]
  462160: b4000060     	cbz	x0, 0x46216c <art::gc::space::ImageSpace::ValidateOatFile(art::OatFile const&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>*, art::ArrayRef<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const>, art::ArrayRef<int const>, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x650>
  462164: f81e83a0     	stur	x0, [x29, #-24]
  462168: 94135d86     	bl	0x939780 <_ZdlPv@plt>
  46216c: aa1303e0     	mov	x0, x19
  462170: 94135d8c     	bl	0x9397a0 <_Unwind_Resume@plt>
