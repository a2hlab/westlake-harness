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

## 更新(offline T4-prep 勘查 R155 libart 二进制,cc-wiki)

对本地 R155 libart.so(sha 59e1bb45,板上同一文件,`westlake-generation-*/payload/route/libart.so`)勘查:
- **有全 .symtab(17566 符号,含 `ClassLinker::CheckSystemClass` @0x339840)**,但 **DWARF 极小**(仅 musl crt CU,0 个 mirror 类型)、**mirror 访问器内联**、**无 `CheckAsmSupportOffsetsAndSizes` 符号** → **per-field mirror 偏移无法直接从 R155 二进制取**。
- **二进制可取的 ground truth = 版本常量**:`art\n108`(ImageHeader kImageVersion,另经 `ImageHeader::kImageVersion` 符号 .rodata 字节 `31 30 38 00` 交叉核)、`oat\n230`(OatHeader kOatVersion)。

因此 T4 布局闸门分两层:
- **A 二进制交叉核(现可跑,非循环)**:`t4_layout_compare.py compare <r155-libart.so> <new-libart.so>` —— kImageVersion/kOatVersion 必须与板上 R155 一致(108/230)。基线 `r155-expected-layout.json`。
- **B 源码 offsetof(等 T3 树)**:6 个 mirror 类 + Thread + ImageHeader/OatHeader 全字段偏移,用 ART 自带 `cpp-define-generator`(T3 构建即产)在 (r1 + 本目录 series) 与 T3 树上各跑一次、逐项 diff==0。R155 源基线 = (r1 + T1 series)(T1 已证逐字节复现 art-hanbin);A 层把格式版本钉到真板二进制,使 B 不纯自证。

**给外环的一条**:R155 libart 二进制因无 mirror DWARF、访问器内联,不能直接吐出 CheckSystemClass 那 6 类的字段偏移期望;能二进制钉死的是 image/oat 格式版本(108/230)。全字段布局比对须在 T3 交出 ART 树后走 cpp-define-generator 源码级 diff(脚本与基线已备)。T3 请一并交出其 `out/.../asm_support_gen.h`(或允许我在其树跑 cpp-define-generator),我即出布局差异表。

## 更新 2(layer C:art_quick_* 反汇编抽偏移立即数,非循环)

外环指出 layer B 循环(比 (r1+series) 对 T3 树而 T3 就是 r1+series,diff 恒 0)。补 **layer C**——从 R155 libart(59e1bb45)反汇编 `art_quick_*` 汇编入口(244 个,全在 .symtab),读它们把 asm_support_gen.h 偏移编成的 `ldr/str [Xt,#imm]` 立即数,是**非循环的板级 ground truth**;T3 交 asm_support_gen.h 后逐项对、不一致=0 才过 T4。

已验证 4 锚点(art_quick_aput_obj + lock_object,精确吻合 quick_entrypoints_arm64.S):
`MIRROR_OBJECT_CLASS_OFFSET=0`、`MIRROR_CLASS_COMPONENT_TYPE_OFFSET=12`、`THREAD_CARD_TABLE_OFFSET=152`、`THREAD_ID_OFFSET=8`。
脚本 `t4_asm_offsets.py`(dump/compare)+ 基线 `r155-asm-offsets.json`;ANCHORS 可扩(LOCK_WORD/STRING_COUNT/ARRAY_LENGTH/THREAD_FLAGS 等,每条锚到已核 .S 指令)。

必查(cppcrash-9465,libart 8c2796fc):CheckSystemClass+544(0x339a60)拒 r16 镜像;6 类全在范围,backtrace 未点单类(在 DumpClass hilog)。

**T4 三层**:A 版本(108/230,现)、B 源码 offsetof(等 T3 树,自证)、**C art_quick 立即数 vs T3 asm_support_gen.h(非循环,现基线已抽)**。过 T4 = A∧C 不一致=0(B 作辅助全字段视图)。
