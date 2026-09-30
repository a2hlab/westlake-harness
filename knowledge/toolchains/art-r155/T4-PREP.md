# T4 布局对照 — 预备(cc-wiki #80,offline;T4 depends: t3-build-art)

T4 要比对**新编 libart(T3 产物)**与**板上 R155 libart(59e1bb45)**的系统类布局;CheckSystemClass 对不上就回 T1 补补丁。T3 未完(需 T2 hw248 同步 r1 树→编译),T4 不能完成。本文件是可离线先定的比对清单与探针方案,T3 产物一到即跑。

## 比对清单(d4_mirror_layouts_match_board 覆盖)

### 1. CheckSystemClass 覆盖的 6 个 mirror 类(源:art-hanbin/runtime/class_linker.cc:602 定义,:830-968 调用)
逐类比 **对象大小(sizeof / class object size)+ 全部实例字段偏移**:
| descriptor | mirror 类 | 头文件 |
|---|---|---|
| Ljava/lang/Object; | mirror::Object | runtime/mirror/object.h |
| Ljava/lang/String; | mirror::String | runtime/mirror/string.h |
| Ljava/lang/DexCache; | mirror::DexCache | runtime/mirror/dex_cache.h |
| Ldalvik/system/ClassExt; | mirror::ClassExt | runtime/mirror/class_ext.h |
| Ljava/lang/Class; | mirror::Class | runtime/mirror/class.h |
| Ljava/lang/ref/Reference; | mirror::Reference | runtime/mirror/reference.h |

CheckSystemClass 内部(class_linker.cc:602+)比 c1(运行时类)对象大小与字段——这 6 类的 mirror C++ 布局若新编 libart ≠ 板上 R155,CheckSystemClass 就 abort(= oc-t4 cppcrash-9465 的死因)。

### 2. Thread 偏移(runtime/thread.h;thread.cc/thread.h 在 T1 补丁 #18/#19 内,R155 有改动 → 高风险)
比 ThreadOffset 常用槽(tls32_/tlsPtr_ 关键字段偏移),尤其 T1 patch 改到的字段。

### 3. ImageHeader / OatHeader 布局(runtime/image.h / oat.h)
比字段偏移 + kImageVersion(108)/kOatVersion(230)——项目底座已定 r1 同这两版。

## 探针方案(复用 DIGEST B.23 的 offsetof/sizeof 双源比对)
- **新编 libart 侧**:用 T3 的 art 源(r1 + 本目录 series 补丁)编一个 offsetof/sizeof dumper(同 B.23 手法,arm64 或 x86_64——mirror 类多为指针/uint32 字段,LP64 布局跨 arch 一致;但 mirror 有 32 位引用压缩 heap_reference,需 `-DART_USE_...` 与板上一致的编译宏,照 T3 的 build flags),打印上述 3 组的 sizeof/offsetof。
- **板上 R155 libart 侧(59e1bb45)**:libart.so 无完整调试符号时,从 `CheckSystemClass` 的**反汇编**读它对每个系统类断言的 expected size/offset 常量(它把编译期布局烧进了检查代码),或从板上 boot.art 的 ImageHeader/类对象实际布局读回;两条都可给"板上期望值"。
- **比对**:两侧 sizeof/offsetof 表逐项 diff,不一致项必须为 0(Thread、ImageHeader/OatHeader 同)。有不一致 → 回 T1 定位缺的补丁(某 mirror 头/thread.h 的 R155 改动没补到)。

## 验收(d4_mirror_layouts_match_board)
新编 vs 板上 R155:6 系统类 size+字段偏移不一致=0;Thread + ImageHeader/OatHeader 偏移不一致=0。

## 待 T3
需 T3 产出新编 libart(及其 art 源树 + build flags)才能编 dumper;板上 R155 libart 59e1bb45 的期望值可先离线从反汇编/boot.art 预取。
