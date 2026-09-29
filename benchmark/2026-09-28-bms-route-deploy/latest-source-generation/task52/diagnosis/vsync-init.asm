
/Users/zhaoyue/orca/workspaces/westlake-harness-bms-deploy/bms/src/.work/b6-latest/platform-link/libvsync.z.so:	file format elf64-littleaarch64

Disassembly of section .text:

0000000000043dfc <OHOS::Rosen::RsFrameReportExt::Init()>:
   43dfc: a9be7bfd     	stp	x29, x30, [sp, #-0x20]!
   43e00: a9014ff4     	stp	x20, x19, [sp, #0x10]
   43e04: 910003fd     	mov	x29, sp
   43e08: aa0003f3     	mov	x19, x0
   43e0c: 39402008     	ldrb	w8, [x0, #0x8]
   43e10: 350001a8     	cbnz	w8, 0x43e44 <OHOS::Rosen::RsFrameReportExt::Init()+0x48>
   43e14: d503201f     	nop
   43e18: 10041288     	adr	x8, 0x4c068 <OHOS::Rosen::ResschedEventListener::ffrtGetHighFrequenceQueueMutex_+0x40>
   43e1c: 52800021     	mov	w1, #0x1                // =1
   43e20: 52800034     	mov	w20, #0x1               // =1
   43e24: 39400109     	ldrb	w9, [x8]
   43e28: f940090a     	ldr	x10, [x8, #0x10]
   43e2c: 7200013f     	tst	w9, #0x1
   43e30: 9a881540     	csinc	x0, x10, x8, ne
   43e34: 9400050b     	bl	0x45260 <dlopen@plt>
   43e38: f9000260     	str	x0, [x19]
   43e3c: b4000740     	cbz	x0, 0x43f24 <OHOS::Rosen::RsFrameReportExt::Init()+0x128>
   43e40: 39002274     	strb	w20, [x19, #0x8]
