# G13 外环执行卡（当前 disabled）

唯一实现路线：`bms_batch.collect_app` + 本卡 guarded Board + G06 before/restore。不用第二套 board_run。唯一目标5ea；候选7c24、原库51e1、原APK abd3。G12已证345个maps完整读取、birth/parent稳定、0消费者，init ondemand及SA511 profile一致；runtime-fresh-01新boot夹持、READY true、124+36逐项等价。不修runtime、不预停foundation。

## 准备及签定输入

实际离线准备命令（本车道仅执行此类host命令）：

```sh
python3 "$G13/prepare.py" --repo "$REPO" --out "$PRIVATE_PLAN_DIR" \
  --window "$WINDOW" --candidate "$G09_NATIVE03/candidate/libinstalls.z.so" \
  --lane "$LOCK_OWNER" --transaction g13-native03-01
python3 "$G13/run_window.py" inspect --plan "$PRIVATE_PLAN_DIR/plan.disabled.json"
```

输出固定本轮G06输入、160成员、本轮boot、单库kit与SHA。`execution_enabled=false`；`approved_by=outer(codex)`只是指定审核者，尚未执行。外环取得锁后，将完整`lane pid ISO-time`绑定到holder，复核所有pins与新目录/事务，启用自己的审定副本。无需改候选或源码。每次改代码后重新prepare新目录；旧plan pins会拒绝。kit manifest两键集必须且只能是libinstalls.z.so，manifest和库均local_pins。

## 阶段 argv（在同一外环串行通道）

```sh
python3 "$G13/run_window.py" before  --plan "$SIGNED_PLAN" --execute
# 如需本轮首启：此时执行生成plan中的control_argv（原G06 launch-only ZigZag），外环读实际t20截图。
python3 "$G13/run_window.py" apply   --plan "$SIGNED_PLAN" --execute
python3 "$G13/run_window.py" install --plan "$SIGNED_PLAN" --execute
python3 "$G13/run_window.py" restore --plan "$SIGNED_PLAN" --execute
```

任何apply/install失败都停止新试验，按下面状态决定恢复，不重放未知写。这里不自动获取或释放板锁；外环持锁、1800秒收口，1200秒后拒绝新的apply/install/launch。单个命令超时会标unknown，杀host HDC不代表remote停止；必须只读reconcile。

- before：源码冻结 `check_frozen.py --git "$REPO"`、160原件SHA、alias元数据/ro、现有按需声明，再复用G06 before捕获设置与11目录不存在。两alias各自收到持久host备份并核51e1；记录原inode。G06旧boot/config不复用。
- apply：重复holder/boot、完整maps空消费者、原inode、160原件SHA，随后本卡事务适配。两文件各自原子rename，不声称双路径一起原子。候选期间160项仅两libinstalls期望值可变7c24，其余原样。读回metadata与rootro。
- install：直接复用collect_app，reinstall=False；临bm再次确认原神不存在。已知bm body/rc立即独立保存；随后loader采样失败记unknown，provider仍写安装记录，bm本身unknown不吞掉。od读取cmdline并host侧还原NUL；核sa_main/profile、boot/PID/birth、maps dev/inode、process-root SHA。先保留install-hilog和body，再走首启条件。任何非零错误body均失败，不因HDC0通过。
- 首启默认关闭；安装成功但缺对照或loaded证据时保存`installed_launch_not_tested`。启用需`control_review`文件含reviewer=outer(codex)、actual_t20_lit=true、本轮boot_id、完整holder；审核者须引用实际control record和截图。对照在apply之前做，避免原G06 smoke固定指纹与候选两处差异冲突。通过后复用5/20/60截图与facts，遇资源/登录/同意页停，不承诺可玩。
- restore：每次新attempt目录。先按需闲置退出180秒并由外环安排实际只读复核，不靠sleep宣称已退出；若仍有消费者，默认拒绝。只有审定`restore_live_installs_action=stop-bound-installs`且实际loader匹配候选/准确profile时，才执行`begetctl stop_service installs`，绝不停止foundation/杀未知PID。两个本轮备份恢复后核51e1/rootro/160成员。若按需无loader，明确`unobserved-demand-idle`；若存在则核原件实际加载。G06 restore在独立attempt内保留包及数据、复原设置。成功恢复不是游戏成功，不自动解锁。

## 不确定执行的恢复

```sh
python3 "$G13/run_window.py" reconcile --plan "$SIGNED_PLAN" --execute
```

此阶段只读mounts、ps、alias/临时文件与完整消费者；日志独立保留。`g13-transaction.json`为`UNKNOWN_*`时不自动backup写、不自动reseal、不允许stop消费者。外环必须证明原命令已结束且无pending remote writer，再给`resolved_unknown_write`绑定`reviewer=outer(codex)`、`transaction_state_sha256`、`pending_remote_writer=false`、真实`evidence_path/evidence_sha256`，才可恢复。这不是可填假的布尔豁免，必须原件佐证；未确定就保留锁移交，不再写。已知remote失败则自动只收口RO，之后外环显式restore原件；任何RO失败仍未恢复。

恢复attempt会复制原G06 context和安装record/bundle作恢复输入，不覆盖先前失败回执；原transaction state持续记录当前恢复状态。保留每个attempt日志。原件host备份不覆盖，候选不修改，数据不清理。

## 交件/实测边界

当前只有离线8用例+语法/路径检查；没有上板、截图、安装、游戏成功回执。外环运行后以`run_facts.py "$WINDOW"`原样输出计数并读实际截图。安装首fatal要保留原hilog并注明覆盖范围；无日志不写“没有fatal”。G09/G10旧件未动。Git/板写已知拒绝，目标分支task/g13-installer-device-window由外环landing，不push。
