# 61b v1 封板操作说明

61b（`61b0657200000000000000000324012c`）已签认并登记为演示板。最终签认在 [final-signoff.json](final-signoff.json)，源码指纹在 [seal.json](seal.json)。外环签字字段按现有协议填 `outer(claude)`，实际审查者为 `outer(codex)`。

日常演示按 [演示顺序与逐项跳过规则](../../2026-10-13-final-demo-booklet/OPERATIONS.zh-CN.md) 操作。该早期手册的待签状态由本目录最终签认补齐。头条已在61b确认信息流、文章、返回和刷新；当前10项非游戏清单只承诺已观察的界面，10个游戏全部不列为可玩演示。v1不含BoatAttack。失败时跳过该应用并记录实际画面。

启动就绪须看屏幕；READY或进程存活不能替代实际信息流。随机SIG11尚未根治，已有恢复最多3次。出现停止或持续黑白屏，保留日志并报告，不清数据、不清stop、不重装、不手工拉起spawner。演示板的运行时、安装和配置保持封存态；维护性重启或解封须用户批准。

从仓库根目录执行61b只读自检（HDC设为现有可执行文件路径，输出必须是新文件）：

```bash
export WORKSPACES="$(cd .. && pwd)"
FINAL="$PWD/benchmark/2026-10-12-v1-seal-execution/seal-final-20261013"
SERIAL=61b0657200000000000000000324012c
BOOT_ID="$("$HDC" -t "$SERIAL" shell cat /proc/sys/kernel/random/boot_id | tr -d '\r\n')"
bash scripts/lab/demo_selfcheck.sh \
  --realization "$FINAL/realization-61b/realization.json" \
  --serial "$SERIAL" --boot-id "$BOOT_ID" --hdc "$HDC" \
  --out "${TMPDIR:-/tmp}/demo-61b-selfcheck-$(date +%Y%m%dT%H%M%S).json"
```

此入口使用R5保留NUL的只读采集。任何未批准差异都应失败并保留回执；重新启动后宿主参数若变化，应产生新的精确派生证明，不能修改旧seal或排除文件来消除差异。`--observed`仅离线比较，不能记为live PASS。

5cd备机恢复已实做487件原事务，另以r4b补建缺失空目录，重启后940项自检通过。重用入口为 `bash scripts/lab/demo_restore.sh --directory-recipe <新配方> --help`；真正执行须按 [r4b恢复配方](../../2026-10-12-exact-realization/r4b-directory-logdir/README.md) 重新绑定目标板、当前boot、源件、前像、独占窗口和有效授权，采用 `restore-then-complete`。旧授权、旧事务目录和旧boot不可重放。61b不作为恢复实验目标；恢复不复制用户数据。完整原始执行记录见本目录 `persistence.json`。

5cd当前仍停在“个人信息保护指引”，用户亲自选择后才能另验备机交互；当前仅签认其指纹恢复，不宣称已通过文章/返回/刷新。原487件回滚及空目录回滚都有前像/所有权限制，未实测整板回滚，不得强行覆盖后续变化。

API全图另见 [API进度表](../../2026-10-12-api-progress/API-PROGRESS.zh.md) 与 [可筛选表格](../../2026-10-12-api-progress/index.html)。表中版本未知、间接证据和未验证APK继续保留原标记。
