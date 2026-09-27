# 头条崩溃收官 + speed 合体交付（#48/#50，2026-09-27）

本轮把"点了崩溃"的非钩 mallocng 堆损坏攻坚到**诊断天花板**，并交付了 **speed+自愈+真名真图标**的合体可用版本。这是**收官综合页**；权威定论见 `.octos/KNOWLEDGE-DIGEST.md` **A.20/A.21 + B.15-17**；逐步细节在下方分支目录。**读这一页就够，别重造已证死路。**

## 一句话结论
非钩 mallocng 崩溃 = **全堆随机野指针/非线性写**，写坏者用现有 **in-process 手段全穷尽、不可根治**；交付 = **可用 + 提速(AOT+JIT) + 真名真图标 + 自愈兜底**（残余 ~15-20%/冷启崩，~26s fresh 重启回 feed，**不是零崩**）。

## 崩溃：已证死路（别返工）
| 手段 | 结果 | 为什么死 |
|---|---|---|
| 三种 user-alloc guard（canary 后区 / page-guard ≤4KB / 全尺寸） | 全 0 命中 | guard 搬块进私有池改变 musl-group 相邻性（海森堡）；被踩的是**共享 musl group/meta**，非线程本地 user chunk |
| 全局 slack-padding（SLACK 64/128/256） | 非单调 19%→6%→19% | 有界溢出应越 padding 越趋零；实际回基线 → **野指针写**，空间 padding 天花板；6% 是小样本变异 |
| 受害者侧符号化栈 | 跨 6 子系统各异 | 受害者=下一个 free 到毒块的线程，非写坏者 |

**要真消除需换赛道**（周级/大工程）：①Bionic/hanbin（若是加密/安全层 metasec/ttcrypto/sscronet 按 Bionic 布局算指针的野写——"never fixed metasec on musl"，一个 a_crash 样本 17 帧全 libsscronet，首嫌）；②长期符号化采样三角定位；③musl mallocng 加固重建。

## 能力：crash42 fp-walk 符号化记录器（攻破 EACCES 墙，留存复用）
整场 DFX 因 `/proc/self/mem` EACCES 拿不到 backtrace；此记录器解决。**四 gotcha**（否则 EVENT=NONE 静默死，见 A.21）：记录器静态链在 **libart**（非独立 libsigchain）→ isolated48 管线重链 baseline **ae2cb182**；目录 init 挂 **`AddSpecialSignalHandlerFn`** 非 `SigchainStartReassert`；信号内**绝不取加载器锁**（dl_iterate_phdr 非 AS-safe，符号化离线）；ART sigchain 拥有 SIGSEGV → 改进 crash42。产物 v3 libart `c6fa9f32`。**留档非交付**（交付基线用 78e34445）。

## 交付：speed+crash+name/icon 合体（4/4 验收 PASS）
| 项 | 状态 | 铁证 |
|---|---|---|
| feed 渲染 | ✅ | 新闻+图+双列视频 |
| 速度 AOT+JIT | ✅ | `Loaded oat/arm64/toutiao.art` + file-JIT `dual RW/RX views`；WebView 重文章 **0.83s vs 14-24s ≈17-29x** |
| 名字图标 | ✅ | iconId 16777218（红头条+今日头条），source-host.hap df385638 |
| 自愈 | ✅ | kill→~26s fresh 重启回 feed，恢复实例仍带 AOT+JIT |

**合体态**：run.sh=#50（webview shim + art-volatile file-JIT）、libart=78e34445、oat/arm64 c7ad2a0b active、#50 watchdog 常驻、host HAP 名图不变。**#50 AOT 预建件与板 39 运行时输入哈希全匹配**（同基线 selfheal-48 eed2d1e）→ 直接复用免重建。回退：`select_arm base` + baseline 备份。

## 分支细节目录（committed，在 merged48 / speed-delivery50 worktree 分支）
- `westlake-harness-merged48/benchmark/2026-09-27-operator-gwp-interposer-48/` — 三种 guard（canary/page-guard 左右/全尺寸）+ v4 观察者，全失手证据。
- `westlake-harness-merged48/benchmark/2026-09-27-crash42-fpwalk-48/` — crash42 fp-walk 记录器（v1 死锁→v2 AS-safe→v3 定死错管线→修好），src/crash_snapshot.c + scripts/symbolize_fpwalk.py + V3-SYMBOLIZED-STACKS.txt。
- `westlake-harness-merged48/benchmark/2026-09-27-slack-pad-48/` — 全局 slack-padding A/B（64/128/256 非单调=padding 天花板）。
- `westlake-harness-speed-delivery50/benchmark/2026-09-26-operator-speed-delivery50/` — #50 AOT+file-JIT+selfheal 候选（本轮合体交付所用）。

## 待续（用户已点：加密/hanbin 研究）
省钱前置判定实验：用本记录器 + **选择性 neuter 安全/加密库**（非 feed 必需者）测崩溃率是否降 → 降=坐实加密层野写=hanbin 值得投；不降=另有其源。几小时级，是"hanbin 长线值不值得"的最省钱前置。
