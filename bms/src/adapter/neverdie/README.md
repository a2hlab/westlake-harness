# adapter/neverdie — 永不死机增强

把 `16.16-NeverDie`(D200 daemon 的「出错不死」运维基建)的思想移植到 **adapter 源码+构建工作区**。

## 它解决什么(补位,不重复 `restore_after_sync.sh`)

| | 守护对象 | 死了怎么救 |
|---|---|---|
| `restore_after_sync.sh`(已存在) | `~/aosp/`、`~/oh/` 源码树 | 用 adapter 的权威输入(patches/framework/build…)**重建**进去 |
| **`neverdie/`(本增强)** | adapter 自己的**权威输入**(上面那批「恢复弹药」) | 用 golden 快照**回滚**它们 |

> 缺口:`restore_after_sync.sh` 的弹药本身没人保护。一次坏 edit / 坏 patch / 坏 `repo sync` / 误删,一键恢复自己就「死机」。本子系统给这批输入做 golden 快照 + 完整性校验 + 一键回滚。

对应 16.16 的:**R3/R13** golden A/B 双 slot · **R2** 失败计数 fallback · **R17** 磁盘配额 + 坏副本轮转 · **R14** metrics/log。(R1 watchdog 不适用——这里没有长驻进程。)

## 保护范围(白名单,见 `nd_common.sh` 的 `ND_PROTECT`)

**纳入**:`framework/ aosp_patches/ ohos_patches/ build/ app/ appspawn/ config/ deploy/ doc/` + `CLAUDE.md readme.txt build.sh bundle.json restore_after_sync.sh appspawn_x_design.html`

**排除**(用白名单天然排除,绝不误纳):`out/`、`oh-build-*.tar.gz`、`prebuilts/`、`build/out`、`*.log`、`.git`、正在复制的 OH 产物。

## golden 仓库位置

刻意放在 `adapter/` **之外**的兄弟目录,理由:能扛住整个 `adapter/` 被删/被覆盖,且不污染 Local↔ECS 同步。

- 默认:`<adapter 的父目录>/.adapter-neverdie`
- **GZ05 建议**:`export ND_GOLDEN_ROOT=/data/.adapter-neverdie`

## 用法

```sh
# 确认当前输入是 known-good(典型:一次成功编译后)→ 拍 golden
bash neverdie/nd_backup_golden.sh

# 体检:工作区 vs active golden(0=健康 1=有漂移 2=还没 golden)
bash neverdie/nd_verify.sh

# 出事回滚(回滚前自动把当前内容隔离到 corrupt/,绝不直接删)
bash neverdie/nd_restore_golden.sh          # 交互确认
bash neverdie/nd_restore_golden.sh --force  # 无人值守

# 接进编译生命周期
bash restore_after_sync.sh && <build 命令> \
    && bash neverdie/nd_guard.sh --mark-success \
    || bash neverdie/nd_guard.sh --build-failed

# 状态
bash neverdie/nd_guard.sh --status
```

`--mark-success` = 清零失败计数 + **自动拍一张新 golden**(捕获新的 known-good)。

## 兜底策略(重要差异)

inputs 是**手写**恢复弹药,不是可重生的产物。所以达到失败阈值(`ND_FAIL_THRESHOLD`,默认 3)时:

- **默认**:只**响亮告警**指向 `nd_restore_golden.sh`,**绝不自动覆盖**正在修的改动。
- `ND_AUTO_RESTORE=1`:才真的自动 `nd_restore_golden.sh --force`。

## 可调环境变量

| 变量 | 默认 | 含义 |
|---|---|---|
| `ND_GOLDEN_ROOT` | `../​.adapter-neverdie` | golden 仓库位置 |
| `ND_ADAPTER_ROOT` | neverdie 的父目录 | 被守护工作区(演练时可指副本) |
| `ND_FAIL_THRESHOLD` | 3 | 连续 build 失败几次触发兜底 |
| `ND_AUTO_RESTORE` | 0 | 达阈值是否自动回滚 |
| `ND_MAX_CORRUPT_COPIES` | 5 | 坏副本保留上限 |
| `ND_MAX_GOLDEN_ROOT_MB` | 2048 | golden 仓库总大小上限 |

## 三性(遵守 adapter CLAUDE.md「一键恢复规则」)

- **自包含**:只依赖干净源码树 + 本目录脚本。
- **幂等**:所有脚本可重复跑;A/B slot 保证任何时刻都有一份完好 golden。
- **可追溯**:每步落 `$ND_GOLDEN_ROOT/nd.log`,`set -euo pipefail` 失败即退,不静默吞错。

## 同步登记(需补)

`neverdie/` 是架构师本机新增的恢复基建,按 CLAUDE.md「`restore_after_sync.sh` 例外条款」属于允许的一次性 Local→ECS 推送。建议在 `readme.txt` 同步表 + `CLAUDE.md` 加一行登记(Local→ECS,push only),避免成为「孤儿改动」。
