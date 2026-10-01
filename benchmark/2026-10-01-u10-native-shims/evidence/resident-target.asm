
benchmark/2026-10-01-u10-native-shims/.artifacts/host/appspawn-x-candidate:	file format elf64-littleaarch64

Disassembly of section .text:

000000000000d468 <U10ShareResidentCompat>:
    d468: a9ba7bfd     	stp	x29, x30, [sp, #-0x60]!
    d46c: a9016ffc     	stp	x28, x27, [sp, #0x10]
    d470: a90267fa     	stp	x26, x25, [sp, #0x20]
    d474: a9035ff8     	stp	x24, x23, [sp, #0x30]
    d478: a90457f6     	stp	x22, x21, [sp, #0x40]
    d47c: a9054ff4     	stp	x20, x19, [sp, #0x50]
    d480: 910003fd     	mov	x29, sp
    d484: d10843ff     	sub	sp, sp, #0x210
    d488: aa0003f8     	mov	x24, x0
    d48c: 90ffffc0     	adrp	x0, 0x5000 <write+0x5000>
    d490: 9103c000     	add	x0, x0, #0xf0
    d494: 910423e1     	add	x1, sp, #0x108
    d498: 94003bce     	bl	0x1c3d0 <dlns_get@plt>
    d49c: 35000180     	cbnz	w0, 0xd4cc <U10ShareResidentCompat+0x64>
    d4a0: f0ffffc1     	adrp	x1, 0x8000 <write+0x8000>
    d4a4: 913d3c21     	add	x1, x1, #0xf4f
    d4a8: 910423e0     	add	x0, sp, #0x108
    d4ac: 528000c2     	mov	w2, #0x6                // =6
    d4b0: 94003bc0     	bl	0x1c3b0 <dlopen_ns@plt>
    d4b4: b5000200     	cbnz	x0, 0xd4f4 <U10ShareResidentCompat+0x8c>
    d4b8: b0000088     	adrp	x8, 0x1e000 <_DYNAMIC+0xb0>
    d4bc: d0ffffc0     	adrp	x0, 0x7000 <write+0x7000>
    d4c0: 91110800     	add	x0, x0, #0x442
    d4c4: 52800981     	mov	w1, #0x4c               // =76
    d4c8: 14000005     	b	0xd4dc <U10ShareResidentCompat+0x74>
    d4cc: b0000088     	adrp	x8, 0x1e000 <_DYNAMIC+0xb0>
    d4d0: 90ffffe0     	adrp	x0, 0x9000 <write+0x9000>
    d4d4: 910b7400     	add	x0, x0, #0x2dd
    d4d8: 528009c1     	mov	w1, #0x4e               // =78
    d4dc: f9414508     	ldr	x8, [x8, #0x288]
    d4e0: f9400103     	ldr	x3, [x8]
    d4e4: 52800022     	mov	w2, #0x1                // =1
    d4e8: 94003bc6     	bl	0x1c400 <fwrite@plt>
    d4ec: 52800059     	mov	w25, #0x2               // =2
    d4f0: 14000057     	b	0xd64c <U10ShareResidentCompat+0x1e4>
    d4f4: f0ffffc1     	adrp	x1, 0x8000 <write+0x8000>
    d4f8: 913d8c21     	add	x1, x1, #0xf63
    d4fc: aa0003f3     	mov	x19, x0
    d500: 94003b74     	bl	0x1c2d0 <dlsym@plt>
    d504: aa0003f5     	mov	x21, x0
    d508: 90ffffe1     	adrp	x1, 0x9000 <write+0x9000>
    d50c: 91271421     	add	x1, x1, #0x9c5
    d510: aa1303e0     	mov	x0, x19
    d514: 94003b6f     	bl	0x1c2d0 <dlsym@plt>
    d518: aa0003f6     	mov	x22, x0
    d51c: f0ffffc1     	adrp	x1, 0x8000 <write+0x8000>
    d520: 91144c21     	add	x1, x1, #0x513
    d524: aa1303e0     	mov	x0, x19
    d528: 94003b6a     	bl	0x1c2d0 <dlsym@plt>
    d52c: aa1f03f4     	mov	x20, xzr
    d530: 52800119     	mov	w25, #0x8               // =8
    d534: b4000740     	cbz	x0, 0xd61c <U10ShareResidentCompat+0x1b4>
    d538: b4000736     	cbz	x22, 0xd61c <U10ShareResidentCompat+0x1b4>
    d53c: b4000715     	cbz	x21, 0xd61c <U10ShareResidentCompat+0x1b4>
    d540: aa0003f7     	mov	x23, x0
    d544: b0ffffc0     	adrp	x0, 0x6000 <write+0x6000>
    d548: 9125d800     	add	x0, x0, #0x976
    d54c: 910023e1     	add	x1, sp, #0x8
    d550: 94003ba0     	bl	0x1c3d0 <dlns_get@plt>
    d554: 35000140     	cbnz	w0, 0xd57c <U10ShareResidentCompat+0x114>
    d558: f0ffffc1     	adrp	x1, 0x8000 <write+0x8000>
    d55c: 913d3c21     	add	x1, x1, #0xf4f
    d560: 910023e0     	add	x0, sp, #0x8
    d564: 528000c2     	mov	w2, #0x6                // =6
    d568: 94003b92     	bl	0x1c3b0 <dlopen_ns@plt>
    d56c: aa0003f4     	mov	x20, x0
    d570: b50000c0     	cbnz	x0, 0xd588 <U10ShareResidentCompat+0x120>
    d574: 910423fa     	add	x26, sp, #0x108
    d578: 1400001a     	b	0xd5e0 <U10ShareResidentCompat+0x178>
    d57c: aa1f03f4     	mov	x20, xzr
    d580: 910423fa     	add	x26, sp, #0x108
    d584: 14000017     	b	0xd5e0 <U10ShareResidentCompat+0x178>
    d588: f0ffffc1     	adrp	x1, 0x8000 <write+0x8000>
    d58c: 913d8c21     	add	x1, x1, #0xf63
    d590: aa1403e0     	mov	x0, x20
    d594: 94003b4f     	bl	0x1c2d0 <dlsym@plt>
    d598: aa0003fa     	mov	x26, x0
    d59c: 90ffffe1     	adrp	x1, 0x9000 <write+0x9000>
    d5a0: 91271421     	add	x1, x1, #0x9c5
    d5a4: aa1403e0     	mov	x0, x20
    d5a8: 94003b4a     	bl	0x1c2d0 <dlsym@plt>
    d5ac: aa0003fb     	mov	x27, x0
    d5b0: f0ffffc1     	adrp	x1, 0x8000 <write+0x8000>
    d5b4: 91144c21     	add	x1, x1, #0x513
    d5b8: aa1403e0     	mov	x0, x20
    d5bc: 94003b45     	bl	0x1c2d0 <dlsym@plt>
    d5c0: 52800119     	mov	w25, #0x8               // =8
    d5c4: eb17001f     	cmp	x0, x23
    d5c8: 540002a1     	b.ne	0xd61c <U10ShareResidentCompat+0x1b4>
    d5cc: eb16037f     	cmp	x27, x22
    d5d0: 54000261     	b.ne	0xd61c <U10ShareResidentCompat+0x1b4>
    d5d4: eb15035f     	cmp	x26, x21
    d5d8: 54000221     	b.ne	0xd61c <U10ShareResidentCompat+0x1b4>
    d5dc: 910023fa     	add	x26, sp, #0x8
    d5e0: f0ffffc2     	adrp	x2, 0x8000 <write+0x8000>
    d5e4: 913d3c42     	add	x2, x2, #0xf4f
    d5e8: aa1803e0     	mov	x0, x24
    d5ec: aa1a03e1     	mov	x1, x26
    d5f0: 94003b74     	bl	0x1c3c0 <dlns_inherit@plt>
    d5f4: 35000120     	cbnz	w0, 0xd618 <U10ShareResidentCompat+0x1b0>
    d5f8: f0ffffc1     	adrp	x1, 0x8000 <write+0x8000>
    d5fc: 913d3c21     	add	x1, x1, #0xf4f
    d600: aa1803e0     	mov	x0, x24
    d604: 528000c2     	mov	w2, #0x6                // =6
    d608: 94003b6a     	bl	0x1c3b0 <dlopen_ns@plt>
    d60c: b5000320     	cbnz	x0, 0xd670 <U10ShareResidentCompat+0x208>
    d610: 52800059     	mov	w25, #0x2               // =2
    d614: 14000002     	b	0xd61c <U10ShareResidentCompat+0x1b4>
    d618: 2a0003f9     	mov	w25, w0
    d61c: b0000088     	adrp	x8, 0x1e000 <_DYNAMIC+0xb0>
    d620: b0ffffc1     	adrp	x1, 0x6000 <write+0x6000>
    d624: 91279021     	add	x1, x1, #0x9e4
    d628: 2a1903e2     	mov	w2, w25
    d62c: f9414508     	ldr	x8, [x8, #0x288]
    d630: f9400100     	ldr	x0, [x8]
    d634: 94003b6b     	bl	0x1c3e0 <fprintf@plt>
    d638: b4000074     	cbz	x20, 0xd644 <U10ShareResidentCompat+0x1dc>
    d63c: aa1403e0     	mov	x0, x20
    d640: 94003b20     	bl	0x1c2c0 <dlclose@plt>
    d644: aa1303e0     	mov	x0, x19
    d648: 94003b1e     	bl	0x1c2c0 <dlclose@plt>
    d64c: 2a1903e0     	mov	w0, w25
    d650: 910843ff     	add	sp, sp, #0x210
    d654: a9454ff4     	ldp	x20, x19, [sp, #0x50]
    d658: a94457f6     	ldp	x22, x21, [sp, #0x40]
    d65c: a9435ff8     	ldp	x24, x23, [sp, #0x30]
    d660: a94267fa     	ldp	x26, x25, [sp, #0x20]
    d664: a9416ffc     	ldp	x28, x27, [sp, #0x10]
    d668: a8c67bfd     	ldp	x29, x30, [sp], #0x60
    d66c: d65f03c0     	ret
    d670: f0ffffc1     	adrp	x1, 0x8000 <write+0x8000>
    d674: 913d8c21     	add	x1, x1, #0xf63
    d678: aa0003f9     	mov	x25, x0
    d67c: 94003b15     	bl	0x1c2d0 <dlsym@plt>
    d680: aa0003f8     	mov	x24, x0
    d684: 90ffffe1     	adrp	x1, 0x9000 <write+0x9000>
    d688: 91271421     	add	x1, x1, #0x9c5
    d68c: aa1903e0     	mov	x0, x25
    d690: 94003b10     	bl	0x1c2d0 <dlsym@plt>
    d694: aa0003fb     	mov	x27, x0
    d698: f0ffffc1     	adrp	x1, 0x8000 <write+0x8000>
    d69c: 91144c21     	add	x1, x1, #0x513
    d6a0: aa1903e0     	mov	x0, x25
    d6a4: 94003b0b     	bl	0x1c2d0 <dlsym@plt>
    d6a8: aa0003fc     	mov	x28, x0
    d6ac: aa1903e0     	mov	x0, x25
    d6b0: 94003b04     	bl	0x1c2c0 <dlclose@plt>
    d6b4: 52800119     	mov	w25, #0x8               // =8
    d6b8: eb17039f     	cmp	x28, x23
    d6bc: 54fffb01     	b.ne	0xd61c <U10ShareResidentCompat+0x1b4>
    d6c0: eb16037f     	cmp	x27, x22
    d6c4: 54fffac1     	b.ne	0xd61c <U10ShareResidentCompat+0x1b4>
    d6c8: eb15031f     	cmp	x24, x21
    d6cc: 54fffa81     	b.ne	0xd61c <U10ShareResidentCompat+0x1b4>
    d6d0: b0000088     	adrp	x8, 0x1e000 <_DYNAMIC+0xb0>
    d6d4: b0ffffc1     	adrp	x1, 0x6000 <write+0x6000>
    d6d8: 9125f821     	add	x1, x1, #0x97e
    d6dc: aa1a03e2     	mov	x2, x26
    d6e0: aa1503e3     	mov	x3, x21
    d6e4: aa1603e4     	mov	x4, x22
    d6e8: f9414508     	ldr	x8, [x8, #0x288]
    d6ec: aa1703e5     	mov	x5, x23
    d6f0: f9400100     	ldr	x0, [x8]
    d6f4: 94003b3b     	bl	0x1c3e0 <fprintf@plt>
    d6f8: 2a1f03f9     	mov	w25, wzr
    d6fc: b5fffa14     	cbnz	x20, 0xd63c <U10ShareResidentCompat+0x1d4>
    d700: 17ffffd1     	b	0xd644 <U10ShareResidentCompat+0x1dc>
