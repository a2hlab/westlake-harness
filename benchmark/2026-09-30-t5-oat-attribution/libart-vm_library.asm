
r155-libart.so:	file format elf64-littleaarch64

Disassembly of section .text:

00000000003db6bc <art::VMRuntime_vmLibrary(_JNIEnv*, _jobject*)>:
  3db6bc: f9400008     	ldr	x8, [x0]
  3db6c0: 90fff201     	adrp	x1, 0x21b000 <art::VMRuntime_registerNativeFree(_JNIEnv*, _jobject*, long)+0x5f4>
  3db6c4: 91395821     	add	x1, x1, #3670
  3db6c8: f9429d02     	ldr	x2, [x8, #1336]
  3db6cc: d61f0040     	br	x2
