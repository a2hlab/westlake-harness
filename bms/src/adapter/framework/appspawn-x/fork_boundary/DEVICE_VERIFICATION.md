# fork_boundary — 02e 合并 + ARM64 device_verified 记录

> 来源：`02e.AppSpawnX/L04.appspawn-process-birth/work/`（HP-AppSpawnX-Fork host oracle）。
> 本文件记录合并进 `02.unity.cardwords/adapter/framework/appspawn-x/fork_boundary/` 后，
> 第一次针对 OH arm64 (musl) 交叉编译 + D600-B 真机执行的结果，并记录 codex headless 对抗
> 挑刺门第 1 轮 FAIL 后做的修复与第 2 轮复核。此前合并动作声称"9/9 真机通过"，但仓内没有任何
> 文件能证明这件事发生过（无 push 记录、无设备 stdout、无 exit code）——第 1 轮 codex 审查把
> 这一点判为 `UNVERIFIABLE_NO_EVIDENCE`。本文件是补齐的第一份真实证据。

## 环境
- 交叉编译：Gz02（`ssh gz02`），OH 源码树 `/data/source/oh-p7885-wukong100`（wukong100 arm64 平台树），
  clang15：`OHOS (dev) clang version 15.0.4 (llvm-project feef13a36e78b7a2ff3e9e3f180a958f2782be1e)`。
- 设备：D600-B `5eab586000000000000000001123012c`（HDC
  `/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc`）。
  设备身份：`OpenHarmony 6.1.0.31`，`Linux 5.15.180 aarch64`，`SELinux Permissive`，
  boot_id `598fadfc-a160-4b12-b0df-31d436bc3ac0`。

## 编译命令（`--target=aarch64-linux-ohos`）
```bash
OH=/data/source/oh-p7885-wukong100
SR=$OH/out/wukong100/obj/third_party/musl/usr
ML=$SR/lib/aarch64-linux-ohos
CC=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang
BUILTINS=$OH/prebuilts/clang/ohos/linux-x86_64/llvm/lib/clang/15.0.4/lib/aarch64-linux-ohos/libclang_rt.builtins.a
ROOT=adapter/framework/appspawn-x/fork_boundary
CFLAGS="--target=aarch64-linux-ohos --sysroot=$SR -I$SR/include/aarch64-linux-ohos \
        -std=c11 -D_GNU_SOURCE -Wall -Wextra -Werror -I$ROOT/include -I$ROOT/tests/host"
LIBS="-B$ML -L$ML -lc -ldl -lpthread $BUILTINS"
SRC_FILES="$ROOT/src/epoch_registry.c $ROOT/src/nonce.c $ROOT/src/fork_capability.c \
           $ROOT/src/child_entry.c $ROOT/src/spawn_oracle.c $ROOT/tests/host/fixtures_games.c"
for t in test_us1_success test_us2_reject_replay test_us2_reject_pidmismatch \
         test_us2_reject_doublefork test_us2_reject_fields test_us3_orphan_reconcile \
         test_edge_timeout test_edge_child_error test_edge_fd_leak test_edge_private_channel; do
  "$CC" $CFLAGS $SRC_FILES "$ROOT/tests/host/$t.c" $LIBS -o "out/$t"
done
```
10/10 built cleanly (`BUILD OK`, no warnings under `-Wall -Wextra -Werror`).

## 真机执行结果（第 2 轮，修复后的源码，含新增 `test_edge_private_channel`）
```
$ HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
$ SERIAL=5eab586000000000000000001123012c
$ for f in test_us1_success test_us2_reject_replay test_us2_reject_pidmismatch \
           test_us2_reject_doublefork test_us2_reject_fields test_us3_orphan_reconcile \
           test_edge_timeout test_edge_child_error test_edge_fd_leak test_edge_private_channel; do
    "$HDC" -t "$SERIAL" shell "/data/local/tmp/fork_boundary_probe_fixed_20260712b/$f; echo __EXIT__=\$?"
  done

test_us1_success:        === ALL CHECKS PASSED === (10/10 game fixtures SPAWN_SUCCESS)  __EXIT__=0
test_us2_reject_replay:  === ALL CHECKS PASSED ===                                       __EXIT__=0
test_us2_reject_pidmismatch: === ALL CHECKS PASSED ===                                   __EXIT__=0
test_us2_reject_doublefork:  === ALL CHECKS PASSED ===                                   __EXIT__=0
test_us2_reject_fields:      === ALL CHECKS PASSED ===                                   __EXIT__=0
test_us3_orphan_reconcile:   === ALL CHECKS PASSED === (US3-a, US3-b both observed)       __EXIT__=0
test_edge_timeout:           === ALL CHECKS PASSED ===                                   __EXIT__=0
test_edge_child_error:       === ALL CHECKS PASSED ===                                   __EXIT__=0
test_edge_fd_leak:           === ALL CHECKS PASSED ===                                   __EXIT__=0
test_edge_private_channel:   === ALL CHECKS PASSED ===                                   __EXIT__=0
```
**10/10 device_verified, 0 failures.** All 10 temp test binaries pushed to
`/data/local/tmp/fork_boundary_probe_fixed_20260712b/` were removed after the run
(`hdc shell rm -rf ...`); device left with zero residue.

## First device run (round 1 gap-closer): raw output, pre-fix binaries

This is the run that first closed round 1's `UNVERIFIABLE_NO_EVIDENCE` finding — same
device/boot as above, but using the **pre-fix** 9 binaries that were already sitting in
`out/adapter/fork_boundary_arm64/` before this codex-gate round started (i.e. built from
source *before* the round-1 fixes below). Full raw stdout, verbatim:

```
=== device identity ===
OpenHarmony 6.1.0.31
OpenHarmony-6.1.0.31
Linux localhost 5.15.180 #1 SMP PREEMPT Fri May 8 13:07:13 UTC 2026 aarch64 Toybox
Permissive
598fadfc-a160-4b12-b0df-31d436bc3ac0

=== RUN test_us1_success ===
[US1] 10.unity.run01endlessrunner      -> SPAWN_SUCCESS pid=5735 bundle=com.sample.run01
[US1] 13.unity.capybaraadventure       -> SPAWN_SUCCESS pid=5736 bundle=com.sample.capybara
[US1] 14.unity.daggerfall              -> SPAWN_SUCCESS pid=5737 bundle=com.sample.daggerfall
[US1] 15.unity.slidingpuzzle           -> SPAWN_SUCCESS pid=5738 bundle=com.sample.slidingpuzzle
[US1] 17.unity.mathpiratesar           -> SPAWN_SUCCESS pid=5739 bundle=com.sample.mathpiratesar
[US1] 18.unity.archerschallenge        -> SPAWN_SUCCESS pid=5740 bundle=com.sample.archerschallenge
[US1] 19.unity.vitalslayer             -> SPAWN_SUCCESS pid=5741 bundle=com.sample.vitalslayer
[US1] 02.unity.cardwords(canonical)    -> SPAWN_SUCCESS pid=5742 bundle=com.CardWordsStudio.CardWords
[US1] apk_out MiniGame                 -> SPAWN_SUCCESS pid=5743 bundle=com.sample.minigame
[US1] apk_out BenchGame                -> SPAWN_SUCCESS pid=5744 bundle=com.sample.benchgame
=== ALL CHECKS PASSED ===
__EXIT__=0

=== RUN test_us2_reject_replay ===
=== ALL CHECKS PASSED ===
__EXIT__=0

=== RUN test_us2_reject_pidmismatch ===
=== ALL CHECKS PASSED ===
__EXIT__=0

=== RUN test_us2_reject_doublefork ===
=== ALL CHECKS PASSED ===
__EXIT__=0

=== RUN test_us2_reject_fields ===
=== ALL CHECKS PASSED ===
__EXIT__=0

=== RUN test_us3_orphan_reconcile ===
[US3-a] orphan pid=5769 exited status=0x0 (no lingering orphan)
[US3-b] orphan pid=5771 exited status=0x9 (dead-parent detected)
=== ALL CHECKS PASSED ===
__EXIT__=0

=== RUN test_edge_timeout ===
=== ALL CHECKS PASSED ===
__EXIT__=0

=== RUN test_edge_child_error ===
=== ALL CHECKS PASSED ===
__EXIT__=0

=== RUN test_edge_fd_leak ===
=== ALL CHECKS PASSED ===
__EXIT__=0
```

SHA256 of the pre-fix binaries used in this first run (from
`out/adapter/fork_boundary_arm64/`, kept locally, not in git):
```
cc522feb36ddcf4670a72110b32d17b73dc4e6beccdaf2b791e99bfc2d051bbe  test_us1_success
5372da8d7b92f1ea44dc12dea3deeda598aa90087ca84cdbf5a5a74e279a56ac  test_us2_reject_replay
6018a62f72ea32b13d7bb0460f2307b65b5942a6c89958c993eaecb8a39e0ba4  test_us2_reject_pidmismatch
309c0c9a40e3c1a9824b170b86593492604c25f3ac7ea22603d8e05edb2e64c4  test_us2_reject_doublefork
ed30981f38fd2a12214e2d63d47cb3bcfc9c11fb34787c9db3ae65d60e8ecc94  test_us2_reject_fields
3618becd654cffbd1aaf600f3bb5c818657515b708ed0eef3b115a016ac6031e  test_us3_orphan_reconcile
21dfe786f1da38d736947f11b85ff9d2243113124ca85b307f04e2ab8fe780c8  test_edge_timeout
f560c0299fb43d9d46ec461385536d81f5a2a6d7ba5bca1767463febe2af4a8a  test_edge_child_error
e36f0e8cf356cc4a520df30cef9033910be1236a18fac6675f9ae926ac02dbc1  test_edge_fd_leak
```
(This first run only exercised the original 9 tests — `test_edge_private_channel` did not
exist yet at that point in the session. The **second run below, against the fixed source,
is the authoritative one** going forward; this first run is kept only as the literal
evidence that closed round 1's evidence gap.)

## Second device run (round 2): SHA256 of the device-verified ARM64 binaries (post-fix, 10/10 run above)
```
8644438a5fa0d3874eedf4f17d435df0ca856f7d1a06e27394887a9d046ebeba  test_us1_success
27cbd28a6dc38035f27a23b9003aba7ff14fb858bd85e7564ed85e6d9b951504  test_us2_reject_replay
f417cb9a0c315db61a4935e961d74476f700f60a89a785c97feb0db5387dfbdf  test_us2_reject_pidmismatch
6b2340c464ea23e5a1e4faa3e1f2a5d986d9561046af392e89f70633184dd018  test_us2_reject_doublefork
899b813151ad5cfb2b560d7140eda7c5c8efa2fe828a40a97981c36e6c55e0ff  test_us2_reject_fields
e96d1aae183b3e8f4892562f290536cda4c7430e057dfc87208b9b3acb66123e  test_us3_orphan_reconcile
92dda43f75e0c264028dd7fe970ea6eb4638ca314c13b46c430b9347d6a0f900  test_edge_timeout
fd098985bc7ca04106da38b6f7900c523f53f69aa1aa80cbee9e8ff76596c81e  test_edge_child_error
b58b264201647169d6723fb7472ad16eeacaf77c1d892d9f59b459cc48633614  test_edge_fd_leak
59f90a9df8c978e681502600d1ee0e66dbd642cf1364ff1f1820793943bb79ec  test_edge_private_channel
```
Local copies kept at `out/adapter/fork_boundary_arm64_fixed/` (outside git — `out/` is
gitignored — for anyone who wants to re-push without recompiling).

## SHA256 of the source tree the second run's binaries were compiled from
(`fork_boundary/{src,include,tests/host}`, excluding `tests/host/.build/`; recompute with
`find fork_boundary/{src,include,tests/host} -type f -not -path '*/.build/*' -exec shasum -a 256 {} \;`
to check for drift against a later state of this tree):
```
0afbad6f695c80db4a5cb96403b8ef7aa8f976a0fa0c08c59f126a7387cb30d8  src/spawn_oracle.c
10d8ac92a4e5aff168355752c5476bf9e9f65fe807010c86c1b5a1c916f5e1f8  tests/host/run_all.sh
1257807a4b1038c8b217108d9c64875f25ea33af27bdfee806ff47001ece370b  include/spawn_oracle.h
1511b0c0782fab891ec0a7ff9a74d39fbafaea240af788b812fd237ce19b8d5e  tests/host/test_us2_reject_fields.c
1be4013862e42fb3526768c9355999b7bd451f073df690316ea0465cd762ba4a  tests/host/test_us2_reject_doublefork.c
22cd9d43b071c57898255e86d8ecd995bf7f9f82a00a1d067369f27a61bd4690  tests/host/test_us1_success.c
3795116b660478e2c2ae3192a88a2449091ead7afe71a56afd2b65a4435570e9  src/nonce.c
4ce15954e0a502cd453132a38604e60a157d64eca5c204530deafb11f0daba2d  tests/host/test_edge_fd_leak.c
5fa7e5352781a27240a60901d010612a385a59d0093bd43d74e6a0320f605f5a  include/nonce.h
64dbc1efea0042faa62cd95caca027d7321a6ba867c6e3fbbcacd3efa9561eee  tests/host/test_edge_timeout.c
777726338c42d03070f4de6b04a9920888c1c405e618d158c9ca649948a9e4c9  tests/host/test_us2_reject_replay.c
79b08640241a232ec3f06f4054b77cd55efa26e1a96cb108970d5dd0c73bd6da  tests/host/fixtures_games.c
7b8c0b9063d6340dbf5d555dd6af5d64d5683b881824bdefd34076588b47672a  include/child_entry.h
7ea7f1d46c668e5d077f0679272ef888db11438032369000b846da08e28761b8  include/fork_capability.h
54a1cce22ed06c3191306633794593c518b8204134a1c232d457ac354c2f0381  src/epoch_registry.c  (round-2-fixed; superseded 7ffdda4c... above)
8d408d667d44389919d4502e9efef9e2b024066c1d5482bd200745d935b9d712  include/epoch_registry.h
916271ac0e5bf35e31ae62f756da0f117c0a39caae616347f8bb82be4da34cbb  tests/host/test_util.h
97e7cefb03c6e91beb7a96360e99e0b9e3176183acd912cb99f87d4715b02ead  tests/host/test_edge_child_error.c
9fb9eb859cc661145dd8736e094e0be33f8666ee4574e604b7b0f49cbc254f91  src/fork_capability.c
ab829825f3adab321393157c5014bc5713ade614659ed4a39180d7e97210ed06  tests/host/test_us3_orphan_reconcile.c
b15b841086808cff640f3179285d2f0a635a25e36a821b18a2249317c9b34290  tests/host/test_us2_reject_pidmismatch.c
b64065dcbb53a8c2d10c0c4893f995ba7f5816b3ae46d111b6aa04532758d088  tests/host/test_edge_private_channel.c
d48267f22ab366cc015d0e20669ad9431fd154d08c145b15ffe1fcf330a7bcc7  tests/host/fixtures_games.h
f2dd45c96d16facb855fb1fcc694091be676dad501324f166d934c136e71664a  src/child_entry.c
```
**Update — third device run, after the round-2 `epoch_registry_reconcile()` fix**: the
SHA above (`7ffdda4c...`) was superseded within the same session. `src/epoch_registry.c`
was re-synced to gz02, all 10 binaries recompiled (same command as above, unchanged flags)
and re-pushed/re-run on D600-B (same boot_id `598fadfc-a160-4b12-b0df-31d436bc3ac0`):
**10/10 `ALL CHECKS PASSED`, `__EXIT__=0` for every test, including `test_us3_orphan_reconcile`
(which exercises `epoch_registry_reconcile()` directly).** New binary SHA256s:
```
1491d76377d710addc94e652428099c5b60c1fab66b6c15f9b9acd73dbd6296a  test_us1_success
0ae39c9f55cb3b6b5e96ad64e129af2fd7b17566a02eb342ba651ee2453ce838  test_us2_reject_replay
44285432991427578ca4229de17dd06f4ded72a9f7d9425c14222ec9e4df70d3  test_us2_reject_pidmismatch
b9e301af64d0fe08bb79733b7e9479488fcf5c625bcfe353c3129ad322817ae4  test_us2_reject_doublefork
65a81670eeee33c1a3298fb895953ab536dc54cab0bfebe831ca393b443413b2  test_us2_reject_fields
0830e7a6efdc8c51009033d4b0cc6799d91ba856c9f6a1edc7ee40b563413cfc  test_us3_orphan_reconcile
622ba3fbec79c672b800fa6c72090bd88a3e7b518b4fdf12d52c4db09004d5bc  test_edge_timeout
9a0cebb5f949791658962f25c6c0e8874d2b02039aabaf92ef9cfeee9eb18b63  test_edge_child_error
09cfa5269c2fd7a1361a5b9815b8a6107ba744d4489289c8afa9c976f12a08cc  test_edge_fd_leak
ae95edfc4ee5bb5172f95110737502fbb0f1ce582b3317ad7e0971199402145b  test_edge_private_channel
```
These (not the "second device run" ones above) are the **current, up-to-date
device-verified binaries** matching the present `src/epoch_registry.c`. Local copies at
`out/adapter/fork_boundary_arm64_fixed/` were overwritten with this third build; the
second-run SHA256 table above is kept only as a historical record of what round 2
actually reviewed.

## codex headless 对抗挑刺门 — round 1 发现并已在本轮修复的问题
1. **`spawn_oracle.c` nonce 消费顺序**：`validate_and_finalize()` 原先在确认 epoch/PID/
   nonce-value 之前就调用 `nonce_registry_try_consume()`，导致一条 epoch 或 PID 都不匹配的
   非法 ACK 仍会把合法 nonce"烧掉"，使真正的 child 之后发出的合法 ACK 被误判
   `REJECT_NONCE_REPLAYED`。修复：只有当 `epoch_ok && pid_ok && nonce_value_ok` 全部成立后才
   消费 nonce。
2. **`epoch_registry_destroy()` fd 泄漏**：处于终态（`ACKED_SUCCESS`/`REJECTED`/`RECONCILED`）
   的请求，其 parent 端 `channel_fd` 从未被关闭。修复：`destroy()` 时遍历全部 request 关闭
   仍打开的 `channel_fd`。
3. **`epoch_registry_reconcile()` 吞掉 `kill()`/`waitpid()` 错误**：原逻辑无论 `kill()` 因何
   失败都直接标记 `RECONCILED`。round 1 修复：只有 `kill()==0` 或 `errno==ESRCH`
   （进程已经不存在）才标记 `RECONCILED`；其它 errno（如 `EPERM`，PID 被复用给不相干进程）
   保留原状态，不再冒充"已 reconcile"。
4. **FR-001（private per-fork channel）零 mutant 覆盖**：新增
   `tests/host/test_edge_private_channel.c` + `MUTANT_FR001_SHARED_CHANNEL`（用
   `fstat()` dev/inode 身份断言两次独立 `fork_capability_channel_create()` 不共享底层
   socket）。
5. **FR-008（fd 清理）零 mutant 覆盖**：新增 `MUTANT_FR008_LEAK_CHILD_FD_IN_PARENT`，复用现有
   `test_edge_fd_leak.c` 的 fd 计数断言作为 target test。
6. **`run_all.sh` 注释路径未随合并更新**：示例命令仍写着旧的 `02e.AppSpawnX/...` 路径，已改成
   合并后的路径（并加一行说明脚本本身用 `BASH_SOURCE` 动态解析 ROOT，两个位置其实都能跑）。

修复后 host 结果：**10/10 PASS、10/10 ASan/UBSan clean、13/13 mutant killed**（原 11 个 +
新增 2 个）。

## codex headless 对抗挑刺门 — round 2 发现并已修复的问题

round 2 复核判定三项仍 FAIL，但确认 host/ARM64 产物事实成立、round 1 的两处 handoff 措辞
矛盾已消除。round 2 指出的、**代码层面**的剩余硬缺口，已在 round 2 之后修复：

7. **`epoch_registry_reconcile()` 的 `waitpid()` 返回值未被检查**：round 1 的修复只区分了
   `kill()` 的返回值/errno，但 `kill()==0` 分支里，`waitpid()` 调用完之后完全没检查 `w`
   是否等于目标 PID——任何非预期的 `waitpid()` 结果（不只是 EINTR 重试后的正常情形）都会
   直接落到"标记 RECONCILED"的代码路径。修复：只有 `w == target`（确实 reap 到了目标）或
   `w == -1 && errno == ECHILD`（目标已被别处 reap，同样代表"已消失"）才算
   `confirmed_gone`；`kill()` 失败且非 `ESRCH` 时同样不算。任何一种"不确定"的结果，`req`
   保持 `PENDING_ACK`（不冒充 `RECONCILED`），并显式把 `req->outcome` 设为
   `REJECT_CHILD_ERROR`（防御性写入——正常调用路径本就该先查 `state` 而不是直接读
   `outcome`，但这样即使有调用方绕过 `state` 检查直接读字段，也不会因为
   `SpawnRequest` 是 `memset` 归零、`SPAWN_SUCCESS` 恰好是枚举值 `0` 而被误读成"成功"）。
   见 `src/epoch_registry.c` 里 `epoch_registry_reconcile()` 的 `confirmed_gone` 变量。
8. **`DEVICE_VERIFICATION.md` 本文件的几处不准确措辞**（round 2 指出）：把"9 boot-image
   temp files"改成准确的"10 个临时测试二进制"；给第一轮设备跑（pre-fix 9 个二进制）补上
   了逐项原始 stdout 和对应二进制 SHA256（此前只有摘要）；补上了源码树的 SHA256 manifest
   （此前完全没有）；把已经过时的"`kill()==0`（已杀+已 reap）"措辞改为准确描述（见上面
   第 7 点）。

修复后（round 2 之后）host 结果：仍是 **10/10 PASS、10/10 ASan/UBSan clean、13/13 mutant
killed**（第 7 点是防御性加固，不改变任何测试的通过/失败结果，已重新跑过 `run_all.sh`
确认零回归）。**第 7 点的代码修复尚未重新交叉编译/推送真机**——上面"第二轮设备跑"记录的
`src/epoch_registry.c` 哈希是修复前的版本，见该节末尾的 round 3 跟进说明。

## 仍未证明（Not Proven，本轮范围之外——codex round 1/2 已列出，非本轮试图掩盖）
- **生产集成**：`src/*.c` 仍是独立 host-only 协议模型，尚未接入
  `framework/appspawn-x/src/{main.cpp,spawn_server.cpp,child_main.cpp}` 的真实 fork/ACK 流程。
  映射表见
  `research/architecture-six-way/handoffs/L03-A01-fork-boundary-to-appspawnx-codex-r1.md`。
- **FR-003 epoch 单调性未强制**：`epoch_registry_create()` 接受调用者传入的任意 `uint64_t`
  值（含相同值、下降值），没有跨"parent 重启"持久化机制强制新 epoch 必须大于旧 epoch；
  这是 handoff 文档已经标注的"未决问题"（epoch 如何跨真实进程重启持久化），不是本轮能在
  host-only 模型里独立解决的（需要生产集成阶段的持久化设计）。
- **FR-010 未完全闭合**：`SpawnSuccessInfo` 没有独立于 `bundle_name`/`adapter_entry` 字符串
  之外的进程身份证据；`adapter_entry` 目前只是"即将 handoff"的意图占位符，不是"handoff 已
  发生"的事实证据（child 发送 ACK 后立即 `_exit(0)`，从不真的执行 runtime handoff）。
- **SC-003 要求的 TSan 未实现**：`run_all.sh` 目前只有 normal + ASan/UBSan 两个 phase，没有
  TSan phase。
- **`recv()` 未使用 `MSG_TRUNC`**：对超长 `SOCK_SEQPACKET` 报文的检测处理与代码注释的表述不
  完全一致（codex round 1 指出，未在本轮修复）。
- 本文件之外，`atom.yaml`/`COMPARISON_DATA.md` 的正式回写属于另一个决策——本次合并只做了
  `src/tests/device` 三层证据闭环，architecture atom 记录的更新由 game Codex/架构 owner 在后续
  轮次处理（见 handoff 文档 Next evidence 一节）。
