# c-route-dex2oat-108 r16(waiver 版,过 InitWithoutImage)

OC-T4 黑板 #91 修复轮。2026-09-30。更新 30e9d16a 的记录。

## 丢失片段真相(决定性)

A15 patch 的 `CheckSystemClass` 豁免(FATAL→WARNING "(continuing for standalone dex2oat)")——A15 host 线从来不是"过"String 检查,是**放行**;r5-r12 换 108 原生时丢的就是它。r13-r15 试图整文件换 yao 的 A15 副本 = 伪链(class_linker.o 编译失败被 `find` 链接配方静默跳过,sha 恒 944ac691,产物缺整个 ClassLinker)。

## r16 变更

108 原生 `class_linker.cc` 为基 + 两处最小豁免(mismatch FATAL→WARNING 带诊断、not-found FATAL→return),`CL_PATCH_SRC` 指回 patches/。链成:exit=0,FAIL=0,`class_linker.o` 800,352B 在位。

## qemu 验收(hw248)

- `--version`:正常参数解析(不再 Signal 11)
- 最小 1-jar(core-libart):死于 `thread.cc:4727 new_exception`(豁免未触发,死在更早的类装载异常路径——与板上 r12 死点同源)
- **5-jar(qemu,09:56 起)**:**过 `InitWithoutImage`**——豁免触发 `CheckSystemClass: Class mismatch for Ljava/lang/String; (continuing for standalone dex2oat); c1.objectSize=0`,此后 8 段文件全落盘(vdex 有实内容:framework 39.5M/icu4j 2.5M/stubs 180K;oat 0 字节待写),死于 **dex2oat 内部 570s 看门狗**(`did not finish after 570000 milliseconds`)——qemu 仿真慢,非代码墙;板上原生速度是秒级,预计不触发。

## 哈希与位置

| 文件 | sha256(前 16) |
|---|---|
| `dex2oat`(r16) | `ab69cfacf3c2ed68` |
| `patches/runtime/class_linker.cc`(108 基+豁免) | 见 hw248 `/home/alvin/c-route-dex2oat-108/` |

hw248 `/home/alvin/c-route-dex2oat-108/`(含 r16 日志 + `qemu-run16-5jar.log`);构建树 `/home/yao/c-route-dex2oat/`。

## 待办

黑板申请板 → 上 r16 → 原 5-jar 重编 9 段(板上原生速度,看门狗应不触发)→ 拉回逐段比 checksum;通过才做 tagsoup 1.2.1 版。
