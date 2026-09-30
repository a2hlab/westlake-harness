
r155-libart.so:	file format elf64-littleaarch64

Disassembly of section .text:

000000000077089c <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)>:
  77089c: d10303ff     	sub	sp, sp, #192
  7708a0: a9067bfd     	stp	x29, x30, [sp, #96]
  7708a4: a9076ffc     	stp	x28, x27, [sp, #112]
  7708a8: a90867fa     	stp	x26, x25, [sp, #128]
  7708ac: a9095ff8     	stp	x24, x23, [sp, #144]
  7708b0: a90a57f6     	stp	x22, x21, [sp, #160]
  7708b4: a90b4ff4     	stp	x20, x19, [sp, #176]
  7708b8: 910183fd     	add	x29, sp, #96
  7708bc: aa0103e0     	mov	x0, x1
  7708c0: aa0803f3     	mov	x19, x8
  7708c4: a93effbf     	stp	xzr, xzr, [x29, #-24]
  7708c8: f81f83bf     	stur	xzr, [x29, #-8]
  7708cc: d10063a2     	sub	x2, x29, #24
  7708d0: 52800581     	mov	w1, #44
  7708d4: 94072603     	bl	0x93a0e0 <_ZN3art5SplitINSt3__h12basic_stringIcNS1_11char_traitsIcEENS1_9allocatorIcEEEES7_EEvRKT_cPNS1_6vectorIT0_NS5_ISC_EEEE@plt>
  7708d8: a97ef3b4     	ldp	x20, x28, [x29, #-24]
  7708dc: eb1c029f     	cmp	x20, x28
  7708e0: 54002ac0     	b.eq	0x770e38 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x59c>
  7708e4: 2a1f03f7     	mov	w23, wzr
  7708e8: 2a1f03f9     	mov	w25, wzr
  7708ec: 2a1f03fa     	mov	w26, wzr
  7708f0: 2a1f03fb     	mov	w27, wzr
  7708f4: 52800056     	mov	w22, #2
  7708f8: d0ffd635     	adrp	x21, 0x236000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x32c>
  7708fc: 9113aeb5     	add	x21, x21, #1259
  770900: b0ffd6f8     	adrp	x24, 0x24d000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x390>
  770904: 911f9f18     	add	x24, x24, #2023
  770908: a900ffff     	stp	xzr, xzr, [sp, #8]
  77090c: b90007ff     	str	wzr, [sp, #4]
  770910: 14000005     	b	0x770924 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x88>
  770914: 2a0003f6     	mov	w22, w0
  770918: 91006294     	add	x20, x20, #24
  77091c: eb1c029f     	cmp	x20, x28
  770920: 540029a0     	b.eq	0x770e54 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x5b8>
  770924: aa1403e0     	mov	x0, x20
  770928: 97ff3ce2     	bl	0x73fcb0 <art::ParseCollectorType(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)>
  77092c: 35ffff40     	cbnz	w0, 0x770914 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x78>
  770930: 39400288     	ldrb	w8, [x20]
  770934: f9400689     	ldr	x9, [x20, #8]
  770938: d341fd0a     	lsr	x10, x8, #1
  77093c: 7200011f     	tst	w8, #0x1
  770940: 9a89014a     	csel	x10, x10, x9, eq
  770944: d1002549     	sub	x9, x10, #9
  770948: f1002d3f     	cmp	x9, #11
  77094c: 54001a68     	b.hi	0x770c98 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x3fc>
  770950: 1000008b     	adr	x11, #16
  770954: 38696b0c     	ldrb	w12, [x24, x9]
  770958: 8b0c096b     	add	x11, x11, x12, lsl #2
  77095c: d61f0160     	br	x11
  770960: f9400a89     	ldr	x9, [x20, #16]
  770964: 7200011f     	tst	w8, #0x1
  770968: d28e4e0a     	mov	x10, #29296
  77096c: f2aeccaa     	movk	x10, #30309, lsl #16
  770970: 9a941528     	csinc	x8, x9, x20, ne
  770974: f2ce4caa     	movk	x10, #29285, lsl #32
  770978: f2eccd2a     	movk	x10, #26217, lsl #48
  77097c: f9400109     	ldr	x9, [x8]
  770980: 39402108     	ldrb	w8, [x8, #8]
  770984: ca0a0129     	eor	x9, x9, x10
  770988: 52800f2a     	mov	w10, #121
  77098c: ca0a0108     	eor	x8, x8, x10
  770990: aa080128     	orr	x8, x9, x8
  770994: b5001828     	cbnz	x8, 0x770c98 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x3fc>
  770998: 52800028     	mov	w8, #1
  77099c: b90013e8     	str	w8, [sp, #16]
  7709a0: 17ffffde     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  7709a4: f9400a89     	ldr	x9, [x20, #16]
  7709a8: 7200011f     	tst	w8, #0x1
  7709ac: d28dedca     	mov	x10, #28526
  7709b0: f2ae4e0a     	movk	x10, #29296, lsl #16
  7709b4: 9a941528     	csinc	x8, x9, x20, ne
  7709b8: f2ceccaa     	movk	x10, #30309, lsl #32
  7709bc: f2ee4caa     	movk	x10, #29285, lsl #48
  7709c0: f9400109     	ldr	x9, [x8]
  7709c4: f8403108     	ldur	x8, [x8, #3]
  7709c8: ca0a0129     	eor	x9, x9, x10
  7709cc: d28cae4a     	mov	x10, #25970
  7709d0: f2acaeca     	movk	x10, #25974, lsl #16
  7709d4: f2cd2e4a     	movk	x10, #26994, lsl #32
  7709d8: f2ef2cca     	movk	x10, #31078, lsl #48
  7709dc: ca0a0108     	eor	x8, x8, x10
  7709e0: aa080128     	orr	x8, x9, x8
  7709e4: b50015a8     	cbnz	x8, 0x770c98 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x3fc>
  7709e8: b90013ff     	str	wzr, [sp, #16]
  7709ec: 17ffffcb     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  7709f0: f9400a89     	ldr	x9, [x20, #16]
  7709f4: 7200011f     	tst	w8, #0x1
  7709f8: d28e4e0f     	mov	x15, #29296
  7709fc: f2ae6caf     	movk	x15, #29541, lsl #16
  770a00: 9a94152b     	csinc	x11, x9, x20, ne
  770a04: f2ccaeef     	movk	x15, #25975, lsl #32
  770a08: f2ee0caf     	movk	x15, #28773, lsl #48
  770a0c: a940356c     	ldp	x12, x13, [x11]
  770a10: 3940416e     	ldrb	w14, [x11, #16]
  770a14: ca0f018c     	eor	x12, x12, x15
  770a18: d28dcd2f     	mov	x15, #28265
  770a1c: f2aeccef     	movk	x15, #30311, lsl #16
  770a20: f2ce4caf     	movk	x15, #29285, lsl #32
  770a24: f2eccd2f     	movk	x15, #26217, lsl #48
  770a28: ca0f01ad     	eor	x13, x13, x15
  770a2c: 52800f2f     	mov	w15, #121
  770a30: ca0f01ce     	eor	x14, x14, x15
  770a34: aa0d018c     	orr	x12, x12, x13
  770a38: aa0e018c     	orr	x12, x12, x14
  770a3c: b40017cc     	cbz	x12, 0x770d34 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x498>
  770a40: a940356c     	ldp	x12, x13, [x11]
  770a44: d28dedce     	mov	x14, #28526
  770a48: f2acacee     	movk	x14, #25959, lsl #16
  770a4c: 3940416b     	ldrb	w11, [x11, #16]
  770a50: f2ccadce     	movk	x14, #25966, lsl #32
  770a54: f2ec2e4e     	movk	x14, #24946, lsl #48
  770a58: ca0e018c     	eor	x12, x12, x14
  770a5c: d28d2e8e     	mov	x14, #26996
  770a60: f2adcdee     	movk	x14, #28271, lsl #16
  770a64: f2cd8c2e     	movk	x14, #27745, lsl #32
  770a68: f2ec6bee     	movk	x14, #25439, lsl #48
  770a6c: ca0e01ad     	eor	x13, x13, x14
  770a70: 52800c6e     	mov	w14, #99
  770a74: ca0e016b     	eor	x11, x11, x14
  770a78: aa0d018c     	orr	x12, x12, x13
  770a7c: aa0b018b     	orr	x11, x12, x11
  770a80: b400160b     	cbz	x11, 0x770d40 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x4a4>
  770a84: d100294b     	sub	x11, x10, #10
  770a88: 93cb056b     	ror	x11, x11, #1
  770a8c: f100157f     	cmp	x11, #5
  770a90: 54001048     	b.hi	0x770c98 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x3fc>
  770a94: b0ffd6ee     	adrp	x14, 0x24d000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x524>
  770a98: 911fcdce     	add	x14, x14, #2035
  770a9c: 100000ac     	adr	x12, #20
  770aa0: 386b69cd     	ldrb	w13, [x14, x11]
  770aa4: 8b0d098c     	add	x12, x12, x13, lsl #2
  770aa8: d61f0180     	br	x12
  770aac: f9400a89     	ldr	x9, [x20, #16]
  770ab0: 7200011f     	tst	w8, #0x1
  770ab4: d28dee0d     	mov	x13, #28528
  770ab8: 9a94152b     	csinc	x11, x9, x20, ne
  770abc: f2ae8e6d     	movk	x13, #29811, lsl #16
  770ac0: f2ccaecd     	movk	x13, #25974, lsl #32
  770ac4: f2ed2e4d     	movk	x13, #26994, lsl #48
  770ac8: f940016c     	ldr	x12, [x11]
  770acc: 7940116b     	ldrh	w11, [x11, #8]
  770ad0: ca0d018c     	eor	x12, x12, x13
  770ad4: 528f2ccd     	mov	w13, #31078
  770ad8: ca0d016b     	eor	x11, x11, x13
  770adc: aa0b018b     	orr	x11, x12, x11
  770ae0: b400112b     	cbz	x11, 0x770d04 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x468>
  770ae4: f100315f     	cmp	x10, #12
  770ae8: 54000660     	b.eq	0x770bb4 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x318>
  770aec: 1400006b     	b	0x770c98 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x3fc>
  770af0: f9400a89     	ldr	x9, [x20, #16]
  770af4: 7200011f     	tst	w8, #0x1
  770af8: d28e4e0b     	mov	x11, #29296
  770afc: 9a941528     	csinc	x8, x9, x20, ne
  770b00: f2aeccab     	movk	x11, #30309, lsl #16
  770b04: f2ce4cab     	movk	x11, #29285, lsl #32
  770b08: f2eccd2b     	movk	x11, #26217, lsl #48
  770b0c: a9402909     	ldp	x9, x10, [x8]
  770b10: 79402108     	ldrh	w8, [x8, #16]
  770b14: ca0b0129     	eor	x9, x9, x11
  770b18: d28bef2b     	mov	x11, #24441
  770b1c: f2adee4b     	movk	x11, #28530, lsl #16
  770b20: f2cc2e6b     	movk	x11, #24947, lsl #32
  770b24: f2ed8d8b     	movk	x11, #27756, lsl #48
  770b28: ca0b014a     	eor	x10, x10, x11
  770b2c: 528c6deb     	mov	w11, #25455
  770b30: ca0b0108     	eor	x8, x8, x11
  770b34: aa0a0129     	orr	x9, x9, x10
  770b38: aa080128     	orr	x8, x9, x8
  770b3c: b5000ae8     	cbnz	x8, 0x770c98 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x3fc>
  770b40: 52800039     	mov	w25, #1
  770b44: 17ffff75     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770b48: f9400a89     	ldr	x9, [x20, #16]
  770b4c: 7200011f     	tst	w8, #0x1
  770b50: d28dedcb     	mov	x11, #28526
  770b54: f2ae4e0b     	movk	x11, #29296, lsl #16
  770b58: 9a941528     	csinc	x8, x9, x20, ne
  770b5c: f2ce6cab     	movk	x11, #29541, lsl #32
  770b60: f2ecaeeb     	movk	x11, #25975, lsl #48
  770b64: a9402909     	ldp	x9, x10, [x8]
  770b68: f840b108     	ldur	x8, [x8, #11]
  770b6c: ca0b0129     	eor	x9, x9, x11
  770b70: d28e0cab     	mov	x11, #28773
  770b74: f2adcd2b     	movk	x11, #28265, lsl #16
  770b78: f2cecceb     	movk	x11, #30311, lsl #32
  770b7c: f2ee4cab     	movk	x11, #29285, lsl #48
  770b80: ca0b014a     	eor	x10, x10, x11
  770b84: d28cae4b     	mov	x11, #25970
  770b88: f2acaecb     	movk	x11, #25974, lsl #16
  770b8c: aa0a0129     	orr	x9, x9, x10
  770b90: f2cd2e4b     	movk	x11, #26994, lsl #32
  770b94: f2ef2ccb     	movk	x11, #31078, lsl #48
  770b98: 9107f16b     	add	x11, x11, #508
  770b9c: ca0b0108     	eor	x8, x8, x11
  770ba0: aa080128     	orr	x8, x9, x8
  770ba4: b50007a8     	cbnz	x8, 0x770c98 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x3fc>
  770ba8: b90017ff     	str	wzr, [sp, #20]
  770bac: 17ffff5b     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770bb0: f9400a89     	ldr	x9, [x20, #16]
  770bb4: 7200011f     	tst	w8, #0x1
  770bb8: d28dedca     	mov	x10, #28526
  770bbc: 9a941528     	csinc	x8, x9, x20, ne
  770bc0: f2adee0a     	movk	x10, #28528, lsl #16
  770bc4: f2ce8e6a     	movk	x10, #29811, lsl #32
  770bc8: f2ecaeca     	movk	x10, #25974, lsl #48
  770bcc: f9400109     	ldr	x9, [x8]
  770bd0: b9400908     	ldr	w8, [x8, #8]
  770bd4: ca0a0129     	eor	x9, x9, x10
  770bd8: 528d2e4a     	mov	w10, #26994
  770bdc: 72af2cca     	movk	w10, #31078, lsl #16
  770be0: ca0a0108     	eor	x8, x8, x10
  770be4: aa080128     	orr	x8, x9, x8
  770be8: b5000588     	cbnz	x8, 0x770c98 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x3fc>
  770bec: 2a1f03f7     	mov	w23, wzr
  770bf0: 17ffff4a     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770bf4: f9400a89     	ldr	x9, [x20, #16]
  770bf8: 7200011f     	tst	w8, #0x1
  770bfc: d28cacea     	mov	x10, #25959
  770c00: f2acadca     	movk	x10, #25966, lsl #16
  770c04: 9a941528     	csinc	x8, x9, x20, ne
  770c08: f2cc2e4a     	movk	x10, #24946, lsl #32
  770c0c: f2ed2e8a     	movk	x10, #26996, lsl #48
  770c10: f9400109     	ldr	x9, [x8]
  770c14: f8407108     	ldur	x8, [x8, #7]
  770c18: ca0a0129     	eor	x9, x9, x10
  770c1c: d28ded2a     	mov	x10, #28521
  770c20: f2ac2dca     	movk	x10, #24942, lsl #16
  770c24: f2cbed8a     	movk	x10, #24428, lsl #32
  770c28: f2ec6c6a     	movk	x10, #25443, lsl #48
  770c2c: ca0a0108     	eor	x8, x8, x10
  770c30: aa080128     	orr	x8, x9, x8
  770c34: b5000328     	cbnz	x8, 0x770c98 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x3fc>
  770c38: 52800028     	mov	w8, #1
  770c3c: b9000fe8     	str	w8, [sp, #12]
  770c40: 17ffff36     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770c44: f9400a89     	ldr	x9, [x20, #16]
  770c48: 7200011f     	tst	w8, #0x1
  770c4c: d28dedcb     	mov	x11, #28526
  770c50: 9a941528     	csinc	x8, x9, x20, ne
  770c54: f2ae4e0b     	movk	x11, #29296, lsl #16
  770c58: f2ceccab     	movk	x11, #30309, lsl #32
  770c5c: f2ee4cab     	movk	x11, #29285, lsl #48
  770c60: a9402909     	ldp	x9, x10, [x8]
  770c64: b9401108     	ldr	w8, [x8, #16]
  770c68: ca0b0129     	eor	x9, x9, x11
  770c6c: d28ccd2b     	mov	x11, #26217
  770c70: f2abef2b     	movk	x11, #24441, lsl #16
  770c74: f2cdee4b     	movk	x11, #28530, lsl #32
  770c78: f2ec2e6b     	movk	x11, #24947, lsl #48
  770c7c: ca0b014a     	eor	x10, x10, x11
  770c80: 528d8d8b     	mov	w11, #27756
  770c84: 72ac6deb     	movk	w11, #25455, lsl #16
  770c88: aa0a0129     	orr	x9, x9, x10
  770c8c: ca0b0108     	eor	x8, x8, x11
  770c90: aa080128     	orr	x8, x9, x8
  770c94: b40003c8     	cbz	x8, 0x770d0c <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x470>
  770c98: aa1403e0     	mov	x0, x20
  770c9c: aa1503e1     	mov	x1, x21
  770ca0: 97f4537f     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770ca4: 36000060     	tbz	w0, #0, 0x770cb0 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x414>
  770ca8: 5280003a     	mov	w26, #1
  770cac: 17ffff1b     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770cb0: aa1403e0     	mov	x0, x20
  770cb4: b0ffd661     	adrp	x1, 0x23d000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x704>
  770cb8: 91007021     	add	x1, x1, #28
  770cbc: 97f45378     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770cc0: 36000060     	tbz	w0, #0, 0x770ccc <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x430>
  770cc4: 2a1f03fa     	mov	w26, wzr
  770cc8: 17ffff14     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770ccc: aa1403e0     	mov	x0, x20
  770cd0: b0ffd661     	adrp	x1, 0x23d000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x720>
  770cd4: 9100e421     	add	x1, x1, #57
  770cd8: 97f45371     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770cdc: 36000060     	tbz	w0, #0, 0x770ce8 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x44c>
  770ce0: 5280003b     	mov	w27, #1
  770ce4: 17ffff0d     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770ce8: aa1403e0     	mov	x0, x20
  770cec: d0ffd541     	adrp	x1, 0x21a000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x6b0>
  770cf0: 91320821     	add	x1, x1, #3202
  770cf4: 97f4536a     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770cf8: 360000e0     	tbz	w0, #0, 0x770d14 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x478>
  770cfc: 2a1f03fb     	mov	w27, wzr
  770d00: 17ffff06     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770d04: 52800037     	mov	w23, #1
  770d08: 17ffff04     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770d0c: 2a1f03f9     	mov	w25, wzr
  770d10: 17ffff02     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770d14: aa1403e0     	mov	x0, x20
  770d18: d0ffd4c1     	adrp	x1, 0x20a000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x69c>
  770d1c: 913e9c21     	add	x1, x1, #4007
  770d20: 97f4535f     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770d24: 36000120     	tbz	w0, #0, 0x770d48 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x4ac>
  770d28: 52800028     	mov	w8, #1
  770d2c: b9000be8     	str	w8, [sp, #8]
  770d30: 17fffefa     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770d34: 52800028     	mov	w8, #1
  770d38: b90017e8     	str	w8, [sp, #20]
  770d3c: 17fffef7     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770d40: b9000fff     	str	wzr, [sp, #12]
  770d44: 17fffef5     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770d48: aa1403e0     	mov	x0, x20
  770d4c: d0ffd4c1     	adrp	x1, 0x20a000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x6d0>
  770d50: 913ec021     	add	x1, x1, #4016
  770d54: 97f45352     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770d58: 36000060     	tbz	w0, #0, 0x770d64 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x4c8>
  770d5c: b9000bff     	str	wzr, [sp, #8]
  770d60: 17fffeee     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770d64: aa1403e0     	mov	x0, x20
  770d68: d0ffd621     	adrp	x1, 0x236000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x79c>
  770d6c: 91141821     	add	x1, x1, #1286
  770d70: 97f4534b     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770d74: 36000080     	tbz	w0, #0, 0x770d84 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x4e8>
  770d78: 52800028     	mov	w8, #1
  770d7c: b90007e8     	str	w8, [sp, #4]
  770d80: 17fffee6     	b	0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770d84: aa1403e0     	mov	x0, x20
  770d88: b0ffd541     	adrp	x1, 0x219000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x748>
  770d8c: 9104e421     	add	x1, x1, #313
  770d90: 97f45343     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770d94: 3707dc20     	tbnz	w0, #0, 0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770d98: aa1403e0     	mov	x0, x20
  770d9c: 90ffd601     	adrp	x1, 0x230000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x7b8>
  770da0: 9100a821     	add	x1, x1, #42
  770da4: 97f4533e     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770da8: 3707db80     	tbnz	w0, #0, 0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770dac: aa1403e0     	mov	x0, x20
  770db0: b0ffd6a1     	adrp	x1, 0x245000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x820>
  770db4: 91062421     	add	x1, x1, #393
  770db8: 97f45339     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770dbc: 3707dae0     	tbnz	w0, #0, 0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770dc0: aa1403e0     	mov	x0, x20
  770dc4: f0ffd6a1     	adrp	x1, 0x247000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x83c>
  770dc8: 9102cc21     	add	x1, x1, #179
  770dcc: 97f45334     	bl	0x485a9c <bool std::__h::operator==[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&, char const*)>
  770dd0: 3707da40     	tbnz	w0, #0, 0x770918 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x7c>
  770dd4: b0ffd6a1     	adrp	x1, 0x245000 <art::detail::CmdlineParseArgument<art::XGcOption>::ParseArgument(art::TokenRange const&, unsigned long*)+0x844>
  770dd8: 91066421     	add	x1, x1, #409
  770ddc: 910063e0     	add	x0, sp, #24
  770de0: 97edaf76     	bl	0x2dcbb8 <std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>::basic_string[abi:v15004]<std::nullptr_t>(char const*)>
  770de4: 9100c3e8     	add	x8, sp, #48
  770de8: 910063e0     	add	x0, sp, #24
  770dec: aa1403e1     	mov	x1, x20
  770df0: 97ff702f     	bl	0x74ceac <std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> std::__h::operator+[abi:v15004]<char, std::__h::char_traits<char>, std::__h::allocator<char>>(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>&&, std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)>
  770df4: 52800028     	mov	w8, #1
  770df8: aa1303e0     	mov	x0, x19
  770dfc: b8008408     	str	w8, [x0], #8
  770e00: 9100c3e1     	add	x1, sp, #48
  770e04: 940722a7     	bl	0x9398a0 <_ZNSt3__h12basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEEC1ERKS5_@plt>
  770e08: 52800048     	mov	w8, #2
  770e0c: 3940c3e9     	ldrb	w9, [sp, #48]
  770e10: f802427f     	stur	xzr, [x19, #36]
  770e14: 3900b27f     	strb	wzr, [x19, #44]
  770e18: b9002268     	str	w8, [x19, #32]
  770e1c: 3900c27f     	strb	wzr, [x19, #48]
  770e20: 37000789     	tbnz	w9, #0, 0x770f10 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x674>
  770e24: 394063e8     	ldrb	w8, [sp, #24]
  770e28: 370007c8     	tbnz	w8, #0, 0x770f20 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x684>
  770e2c: f85e83b3     	ldur	x19, [x29, #-24]
  770e30: b50003f3     	cbnz	x19, 0x770eac <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x610>
  770e34: 1400002f     	b	0x770ef0 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x654>
  770e38: b90007ff     	str	wzr, [sp, #4]
  770e3c: 2a1f03fb     	mov	w27, wzr
  770e40: 2a1f03fa     	mov	w26, wzr
  770e44: 2a1f03f9     	mov	w25, wzr
  770e48: 2a1f03f7     	mov	w23, wzr
  770e4c: a900ffff     	stp	xzr, xzr, [sp, #8]
  770e50: 52800056     	mov	w22, #2
  770e54: b94013e8     	ldr	w8, [sp, #16]
  770e58: b900027f     	str	wzr, [x19]
  770e5c: b94007e9     	ldr	w9, [sp, #4]
  770e60: a9017e7f     	stp	xzr, xzr, [x19, #16]
  770e64: f900067f     	str	xzr, [x19, #8]
  770e68: 39009268     	strb	w8, [x19, #36]
  770e6c: b94017e8     	ldr	w8, [sp, #20]
  770e70: 3900ae69     	strb	w9, [x19, #43]
  770e74: b9400be9     	ldr	w9, [sp, #8]
  770e78: b9002276     	str	w22, [x19, #32]
  770e7c: 39009668     	strb	w8, [x19, #37]
  770e80: b9400fe8     	ldr	w8, [sp, #12]
  770e84: 39009e77     	strb	w23, [x19, #39]
  770e88: 3900a279     	strb	w25, [x19, #40]
  770e8c: 39009a68     	strb	w8, [x19, #38]
  770e90: 52800028     	mov	w8, #1
  770e94: 3900a67a     	strb	w26, [x19, #41]
  770e98: 3900aa7b     	strb	w27, [x19, #42]
  770e9c: 3900b269     	strb	w9, [x19, #44]
  770ea0: 3900c268     	strb	w8, [x19, #48]
  770ea4: f85e83b3     	ldur	x19, [x29, #-24]
  770ea8: b4000253     	cbz	x19, 0x770ef0 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x654>
  770eac: f85f03a8     	ldur	x8, [x29, #-16]
  770eb0: aa1303e0     	mov	x0, x19
  770eb4: eb13011f     	cmp	x8, x19
  770eb8: 54000180     	b.eq	0x770ee8 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x64c>
  770ebc: aa0803f4     	mov	x20, x8
  770ec0: 14000004     	b	0x770ed0 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x634>
  770ec4: aa1403e8     	mov	x8, x20
  770ec8: eb13029f     	cmp	x20, x19
  770ecc: 540000c0     	b.eq	0x770ee4 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x648>
  770ed0: 385e8e89     	ldrb	w9, [x20, #-24]!
  770ed4: 3607ff89     	tbz	w9, #0, 0x770ec4 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x628>
  770ed8: f85f8100     	ldur	x0, [x8, #-8]
  770edc: 94072229     	bl	0x939780 <_ZdlPv@plt>
  770ee0: 17fffff9     	b	0x770ec4 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x628>
  770ee4: f85e83a0     	ldur	x0, [x29, #-24]
  770ee8: f81f03b3     	stur	x19, [x29, #-16]
  770eec: 94072225     	bl	0x939780 <_ZdlPv@plt>
  770ef0: a94b4ff4     	ldp	x20, x19, [sp, #176]
  770ef4: a94a57f6     	ldp	x22, x21, [sp, #160]
  770ef8: a9495ff8     	ldp	x24, x23, [sp, #144]
  770efc: a94867fa     	ldp	x26, x25, [sp, #128]
  770f00: a9476ffc     	ldp	x28, x27, [sp, #112]
  770f04: a9467bfd     	ldp	x29, x30, [sp, #96]
  770f08: 910303ff     	add	sp, sp, #192
  770f0c: d65f03c0     	ret
  770f10: f94023e0     	ldr	x0, [sp, #64]
  770f14: 9407221b     	bl	0x939780 <_ZdlPv@plt>
  770f18: 394063e8     	ldrb	w8, [sp, #24]
  770f1c: 3607f888     	tbz	w8, #0, 0x770e2c <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x590>
  770f20: f94017e0     	ldr	x0, [sp, #40]
  770f24: 94072217     	bl	0x939780 <_ZdlPv@plt>
  770f28: f85e83b3     	ldur	x19, [x29, #-24]
  770f2c: b5fffc13     	cbnz	x19, 0x770eac <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x610>
  770f30: 17fffff0     	b	0x770ef0 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x654>
  770f34: 3940c3e8     	ldrb	w8, [sp, #48]
  770f38: aa0003f3     	mov	x19, x0
  770f3c: 360000a8     	tbz	w8, #0, 0x770f50 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x6b4>
  770f40: f94023e0     	ldr	x0, [sp, #64]
  770f44: 9407220f     	bl	0x939780 <_ZdlPv@plt>
  770f48: 14000002     	b	0x770f50 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x6b4>
  770f4c: aa0003f3     	mov	x19, x0
  770f50: 394063e8     	ldrb	w8, [sp, #24]
  770f54: 360000c8     	tbz	w8, #0, 0x770f6c <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x6d0>
  770f58: f94017e0     	ldr	x0, [sp, #40]
  770f5c: 94072209     	bl	0x939780 <_ZdlPv@plt>
  770f60: 14000003     	b	0x770f6c <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x6d0>
  770f64: 14000001     	b	0x770f68 <art::CmdlineType<art::XGcOption>::Parse(std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>> const&)+0x6cc>
  770f68: aa0003f3     	mov	x19, x0
  770f6c: d10063a0     	sub	x0, x29, #24
  770f70: 97edbf36     	bl	0x2e0c48 <std::__h::vector<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>, std::__h::allocator<std::__h::basic_string<char, std::__h::char_traits<char>, std::__h::allocator<char>>>>::~vector[abi:v15004]()>
  770f74: aa1303e0     	mov	x0, x19
  770f78: 9407220a     	bl	0x9397a0 <_Unwind_Resume@plt>
