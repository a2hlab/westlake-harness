
r155-libart.so:	file format elf64-littleaarch64

Disassembly of section .text:

000000000076e508 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)>:
  76e508: d10143ff     	sub	sp, sp, #80
  76e50c: a9017bfd     	stp	x29, x30, [sp, #16]
  76e510: f90013f7     	str	x23, [sp, #32]
  76e514: a90357f6     	stp	x22, x21, [sp, #48]
  76e518: a9044ff4     	stp	x20, x19, [sp, #64]
  76e51c: 910043fd     	add	x29, sp, #16
  76e520: f9400016     	ldr	x22, [x0]
  76e524: aa0003f4     	mov	x20, x0
  76e528: aa0103f3     	mov	x19, x1
  76e52c: f8408ed7     	ldr	x23, [x22, #8]!
  76e530: b4000357     	cbz	x23, 0x76e598 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x90>
  76e534: aa1603f5     	mov	x21, x22
  76e538: 14000004     	b	0x76e548 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x40>
  76e53c: 910022f7     	add	x23, x23, #8
  76e540: f94002f7     	ldr	x23, [x23]
  76e544: b4000177     	cbz	x23, 0x76e570 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x68>
  76e548: f94012e0     	ldr	x0, [x23, #32]
  76e54c: b4ffff80     	cbz	x0, 0x76e53c <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x34>
  76e550: f9400008     	ldr	x8, [x0]
  76e554: aa1303e1     	mov	x1, x19
  76e558: f9400d08     	ldr	x8, [x8, #24]
  76e55c: d63f0100     	blr	x8
  76e560: 3707fee0     	tbnz	w0, #0, 0x76e53c <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x34>
  76e564: aa1703f5     	mov	x21, x23
  76e568: f94002f7     	ldr	x23, [x23]
  76e56c: b5fffef7     	cbnz	x23, 0x76e548 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x40>
  76e570: eb1602bf     	cmp	x21, x22
  76e574: 54000120     	b.eq	0x76e598 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x90>
  76e578: f9400268     	ldr	x8, [x19]
  76e57c: aa1303e0     	mov	x0, x19
  76e580: f94012a1     	ldr	x1, [x21, #32]
  76e584: f9400d08     	ldr	x8, [x8, #24]
  76e588: d63f0100     	blr	x8
  76e58c: 37000060     	tbnz	w0, #0, 0x76e598 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x90>
  76e590: f94016a0     	ldr	x0, [x21, #40]
  76e594: b5000640     	cbnz	x0, 0x76e65c <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x154>
  76e598: 52800200     	mov	w0, #16
  76e59c: f9400295     	ldr	x21, [x20]
  76e5a0: 94072cbc     	bl	0x939890 <_Znwm@plt>
  76e5a4: 52800048     	mov	w8, #2
  76e5a8: aa0003f6     	mov	x22, x0
  76e5ac: f800401f     	stur	xzr, [x0, #4]
  76e5b0: aa1303e1     	mov	x1, x19
  76e5b4: b9000c1f     	str	wzr, [x0, #12]
  76e5b8: b9000008     	str	w8, [x0]
  76e5bc: aa1503e0     	mov	x0, x21
  76e5c0: 97fffef2     	bl	0x76e188 <void art::VariantMap<art::RuntimeArgumentMap, art::RuntimeArgumentMapKey>::Remove<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)>
  76e5c4: f9400268     	ldr	x8, [x19]
  76e5c8: aa1303e0     	mov	x0, x19
  76e5cc: f9400108     	ldr	x8, [x8]
  76e5d0: d63f0100     	blr	x8
  76e5d4: a9005be0     	stp	x0, x22, [sp]
  76e5d8: 910003e1     	mov	x1, sp
  76e5dc: 910003e2     	mov	x2, sp
  76e5e0: aa1503e0     	mov	x0, x21
  76e5e4: 97ff6cd5     	bl	0x749938 <std::__h::pair<std::__h::__tree_iterator<std::__h::__value_type<art::detail::VariantMapKeyRaw const*, void*>, std::__h::__tree_node<std::__h::__value_type<art::detail::VariantMapKeyRaw const*, void*>, void*>*, long>, bool> std::__h::__tree<std::__h::__value_type<art::detail::VariantMapKeyRaw const*, void*>, std::__h::__map_value_compare<art::detail::VariantMapKeyRaw const*, std::__h::__value_type<art::detail::VariantMapKeyRaw const*, void*>, art::VariantMap<art::RuntimeArgumentMap, art::RuntimeArgumentMapKey>::KeyComparator, true>, std::__h::allocator<std::__h::__value_type<art::detail::VariantMapKeyRaw const*, void*>>>::__emplace_unique_key_args<art::detail::VariantMapKeyRaw const*, std::__h::pair<art::detail::VariantMapKeyRaw const* const, void*>>(art::detail::VariantMapKeyRaw const* const&, std::__h::pair<art::detail::VariantMapKeyRaw const* const, void*>&&)>
  76e5e8: f9400295     	ldr	x21, [x20]
  76e5ec: f8408eb6     	ldr	x22, [x21, #8]!
  76e5f0: b4000316     	cbz	x22, 0x76e650 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x148>
  76e5f4: aa1503f4     	mov	x20, x21
  76e5f8: 14000004     	b	0x76e608 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x100>
  76e5fc: 910022d6     	add	x22, x22, #8
  76e600: f94002d6     	ldr	x22, [x22]
  76e604: b4000176     	cbz	x22, 0x76e630 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x128>
  76e608: f94012c0     	ldr	x0, [x22, #32]
  76e60c: b4ffff80     	cbz	x0, 0x76e5fc <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0xf4>
  76e610: f9400008     	ldr	x8, [x0]
  76e614: aa1303e1     	mov	x1, x19
  76e618: f9400d08     	ldr	x8, [x8, #24]
  76e61c: d63f0100     	blr	x8
  76e620: 3707fee0     	tbnz	w0, #0, 0x76e5fc <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0xf4>
  76e624: aa1603f4     	mov	x20, x22
  76e628: f94002d6     	ldr	x22, [x22]
  76e62c: b5fffef6     	cbnz	x22, 0x76e608 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x100>
  76e630: eb15029f     	cmp	x20, x21
  76e634: 540000e0     	b.eq	0x76e650 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x148>
  76e638: f9400268     	ldr	x8, [x19]
  76e63c: aa1303e0     	mov	x0, x19
  76e640: f9401281     	ldr	x1, [x20, #32]
  76e644: f9400d08     	ldr	x8, [x8, #24]
  76e648: d63f0100     	blr	x8
  76e64c: 36000060     	tbz	w0, #0, 0x76e658 <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x150>
  76e650: aa1f03e0     	mov	x0, xzr
  76e654: 14000002     	b	0x76e65c <art::XGcOption& art::CmdlineParser<art::RuntimeArgumentMap, art::RuntimeArgumentMap::Key>::SaveDestination::GetOrCreateFromMap<art::XGcOption>(art::RuntimeArgumentMapKey<art::XGcOption> const&)+0x154>
  76e658: f9401680     	ldr	x0, [x20, #40]
  76e65c: a9444ff4     	ldp	x20, x19, [sp, #64]
  76e660: a94357f6     	ldp	x22, x21, [sp, #48]
  76e664: a9417bfd     	ldp	x29, x30, [sp, #16]
  76e668: f94013f7     	ldr	x23, [sp, #32]
  76e66c: 910143ff     	add	sp, sp, #80
  76e670: d65f03c0     	ret
