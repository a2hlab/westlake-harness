# 硬件 watchpoint 实验:抓写坏 GrGLContext/GrGLInterface 指针字段的写坏者(cc-wiki #80,offline prep)

## 目标
Skia 动态根因(SKIA-DYNAMIC-ROOT.json)定出:GL 家族崩在 `GrGLGpu::onResetContext` 的
`blr x9; x9=[x8+0x730]`,其中 `x8 = *(*(GrGLGpu+0xb0)+0x8)` 是 GL context/interface 指针链,
崩溃时 `x8=0x7f34b12bbf`(**misaligned**,与 this 同 heap 区)。即**某个指针字段被运行时写成错位值**。
本实验用**硬件写 watchpoint** 盯住那个 8 字节指针槽 `A`,在**第一次被写坏时**记下写入 PC + 栈 =
写坏者(真修目标)。这是 SKIA-DYNAMIC-ROOT 里"需硬件 watchpoint / MTE"那步的落地。

## 关键难点:目标地址 A 每次不同(ASLR + 堆)
`A = *(GrGLGpu+0xb0) + 0x8`。GrGLGpu 是 `RenderThread::requireGlContext` 里 `GrDirectContexts::MakeGL`
建的堆对象,地址每次跑都变。所以 **A 必须运行时解析**,不能硬编码。

## 判据(什么算抓到写坏者)
- watchpoint 在一次 **写** 命中,写入值是 **misaligned / 非法指针**(奇地址、或不在 libskia/heap 合法区)
  → 该次的 PC + 回溯 = **写坏者**。判定成功。
- 若命中的写入值都是**合法对齐指针**(正常 re-init/赋值)→ 是良性写,继续等下一次;记录良性写点做排除。
- 若整个观察窗内 A 从未被写成坏值、且进程正常存活 → 本轮没抽到崩(崩~1/3);重复。
- 若 A 被写坏但 watchpoint 没触发 → 说明写不是普通 store(可能 memcpy/DMA/跨映射);转退路 C。

## 方法 A(首选):hdc + lldb-server(利用 libskia 符号)
libskia_canvaskit(2f7219f2)带符号(崩溃栈可符号化)。
步骤(step0 先在板上确认 `which lldb-server` 或 OH SDK 的 lldb;无则转方法 B):
```
# 1. 起 app(背景安装器已放行),等首帧后 RenderThread 存在
# 2. lldb attach 到 RenderThread(按 threadName=RenderThread 选 tid)
# 3. 在 onResetContext 入口下断(它每帧/换 context 时进,拿到有效对象):
#    (lldb) b GrGLGpu::onResetContext
#    命中后读 this=x19,算 A:
#    (lldb) p/x *(void**)((*(char**)((char*)$x19+0xb0))+0x8)   # 打印当前(合法)指针值,确认对齐
#    (lldb) p/x (void*)((*(char**)((char*)$x19+0xb0))+0x8)     # A 的地址
# 4. 删 onResetContext 断点,改设 8 字节写 watchpoint:
#    (lldb) watchpoint set expression -w write -s 8 -- <A>
#    (lldb) c
# 5. watchpoint 命中即停,记:
#    (lldb) p/x <A 处新值>     # 判是否 misaligned/非法
#    (lldb) bt                 # 写坏者栈 = 真修目标
```
判据同上;命中 misaligned 写 → bt 即写坏者。

## 方法 B(退路,无 lldb):ptrace + NT_ARM_HW_WATCH 小程序(arm64)
自写 arm64 ptrace helper(见 watchpoint_helper.c):PTRACE_SEIZE 到 RenderThread tid,
用 `PTRACE_SETREGSET(NT_ARM_HW_WATCH)` 设 DBGWVR0/DBGWCR0(写、len=8、EL0 enable)盯地址 A,
命中 SIGTRAP 后 `PTRACE_GETREGSET(NT_PRSTATUS)` 读 pc/lr + 走 fp 链出迷你回溯。
A 的解析(无符号 lldb 时):
- B1:先跑一次到崩,从 tombstone / core 读 x19(GrGLGpu)与 A —— 但 ASLR 使下次变,需**关 ASLR**
  (`hdc shell param set ... ` 或 `setarch -R`,OH 若支持)后地址稳定,再设 watchpoint 重跑。
- B2:堆扫描——RenderThread 的 GrGLGpu 对象由其 vtable 指针识别(libskia 里 GrGLGpu 的 vtable
  符号地址 + libskia 加载基址),扫 `/proc/<pid>/maps` 的 heap 段找该 vtable 值定位 GrGLGpu,再算 A。
- B3:onResetContext 软件断点法(不用 lldb):helper 在 onResetContext 入口(libskia 基址+0x123d230)
  设 PTRACE 断点,命中读 x19 算 A,撤断点、设 A 的写 watchpoint、continue。**等价方法 A 但纯 ptrace**。B3 最稳,优先。

## 退路 C(watchpoint 都不行):周期扫描(定 WHEN 不定 WHO)
helper 每帧间隙 PTRACE 读 A,校验是否 misaligned;发现即记录当前所有线程栈快照 +
最近若干帧的调用序列,缩小到"上一间隔内"的写点。弱(无精确写者),但能界定时间窗与并发上下文。

## 安全/纪律(板上执行时)
- **绝不 kill -9 / 不动 appspawn-x**;attach 用 SEIZE、结束用 PTRACE_DETACH 干净脱离;app 生命周期走 begetctl。
- ptrace RenderThread 会暂停该线程——**短窗**,做完立即 detach;若暂停导致看门狗杀进程,记录并转退路 C(只读扫描)。
- 只对白名单序列号、持锁车道;U0 不改(纯挂载观测,无 /system 写);完后释放锁。
- 判进程计数不用裸 pgrep -f。

## 产物
- 命中 misaligned 写 → 写坏者栈写入 `WATCHPOINT-RESULT.json`(PC/栈/写入值/A 地址/libskia 基址偏移),交 cx-t0 真修。
- 排除的良性写点也记(缩小范围)。
