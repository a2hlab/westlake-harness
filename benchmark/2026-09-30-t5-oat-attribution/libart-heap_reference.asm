
r155-libart.so:	file format elf64-littleaarch64

Disassembly of section .text:

000000000068e364 <art::gc::collector::MarkCompact::IsNullOrMarkedHeapReference(art::mirror::HeapReference<art::mirror::Object>*, bool)>:
  68e364: a9bf7bfd     	stp	x29, x30, [sp, #-16]!
  68e368: b9400021     	ldr	w1, [x1]
  68e36c: 910003fd     	mov	x29, sp
  68e370: 340000c1     	cbz	w1, 0x68e388 <art::gc::collector::MarkCompact::IsNullOrMarkedHeapReference(art::mirror::HeapReference<art::mirror::Object>*, bool)+0x24>
  68e374: 97ffff97     	bl	0x68e1d0 <art::gc::collector::MarkCompact::IsMarked(art::mirror::Object*)>
  68e378: f100001f     	cmp	x0, #0
  68e37c: 1a9f07e0     	cset	w0, ne
  68e380: a8c17bfd     	ldp	x29, x30, [sp], #16
  68e384: d65f03c0     	ret
  68e388: 52800020     	mov	w0, #1
  68e38c: a8c17bfd     	ldp	x29, x30, [sp], #16
  68e390: d65f03c0     	ret
