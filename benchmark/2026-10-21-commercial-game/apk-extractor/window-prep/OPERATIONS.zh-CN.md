# G12：给外环的最小可审短窗

仅离线准备；本车道没有设备、构建或服务操作。`plan.disabled.json` 保持关闭。native-03 独立复核 baseline 对象完整 SHA `2e2a6247d73b981cc530653a411f7b29f531eabac19a1c564e8c30391eb8481b`、原库 `51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5`；候选 `7c24bd11190b0728b81ecd958519f01c688efb2533ef26c9b7ae4eefc82151db`，1286024 字节，13 步 rc0、52 份 raw 引用见 `build-proof.json`。原件在 cx `native-build/.private/native-03/candidate/libinstalls.z.so`。

## 外环现在可做的只读采样

`next-reads.json` 的 8 条 argv 已完整可执行，仅需把数组第一个元素 `$HDC` 换成实际可执行文件路径，逐条执行、保存未截断 stdout/stderr/argv/时间/transport rc 和 `__REMOTE_RC`。不要把 JSON 交给 shell eval。45 秒 maps 超时或任何拒绝均停止，不重试。此文件不执行命令。

- boot 必须前后为 `a1d869b4-69a2-40a4-937e-4860f5b54239`。其他 boot 重新绑定。
- 全进程 maps 扫描不依赖 NAME，逐进程保留 stat 前后及 maps rc。解析 starttime 时从 stat 最后的 `)` 后数，不能直接按整行空格 split。退出/不可读/PID 复用/新增进程未覆盖都是缺口；不能据此宣布无消费者。
- 若 maps 命中 `libinstalls.z.so`，用 `python3 fresh_argv.py --pid 实际PID` 生成该 PID 的身份/maps/process-root SHA 第二组；不使用历史 13171，也不将 fresh foundation 878 当作 installs。
- init 读取只查仓内 `board_state_snapshot.py:19` 已声明的三个 init 根的现有 cfg。读出服务声明后，继续读取它实际引用的 SA profile/import 路径并保留 SHA；未找到或只看名字不算按需证明。命令不启动服务。
- `runtime-preimage-reads.json` 用 G05/G06 的 124+36 个**路径**生成 8 条 fresh SHA 读取 argv，不复用旧 SHA 作为本轮前像。还需与本轮 mountinfo/init/current-generation 清单对齐，补齐新增路径、bind 源及其持久恢复输入。

## 已读 fresh 原件

`fresh-review.json` 固定 `$HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/fresh-20261021T1722` 的原件哈希。14 条 transport/remote 均0；两 alias 独立 regular、nlink1、device66336、inode5576/3342、owner0:0、0755、system_lib_file、SHA51e1，覆盖它们的根挂载 ro。runtime 另有多处 bind，存在 bind 不等于当前运行时已正确恢复。

Wi‑Fi 回执 connected/2.4GHz/`UpstreamLabs_Compatibility`，实际名仅是只读观测；外环保持用户当前配置，不声称用户明确接受名字差异，`upstreamlabswifi` 是网络意图；不因名字差异阻塞、不改网络。这里只复用5ea证据，未访问61b。power SLEEP/30000/10000；完整设置仍须锁下重新捕获。`bm dump -n` body 是错误，即使 rc0也不能单独判包不存在；需正确包清单及11个既存数据目录检查。

## 单库方案：先判消费者，不默认停 foundation

1. 外环在5ea锁下复核 boot、完整持有者/start、冻结门、全量前像、两 alias 元数据、原神未安装且11目录不存在；备份两份原件到持久 host 并复核51e1，保留设备事务备份。绑定当前 generation 的恢复文件、SHA、准确 argv，验证 ZigZag 对照输入。预算1200秒停止新测试、1800秒收尾；不能只杀 runner 留安装子进程。
2. **优先空消费者路径**：完整 maps 无 libinstalls 消费者，现有声明及引用 profile 明确按需启动。在同一锁/boot下临写前复核仍为空，双 alias 各自原子 rename 替换，不调用 stop/start foundation。锁并不能阻止系统自身启动安装服务；发现并发活动或中间状态漂移即停止测试并重新核身份，不能声称双文件切换具备跨路径原子性。
3. kit 仅 `manifest.json`（取本目录 `one-lib-manifest.json`）和真实 `libinstalls.z.so`。复核候选SHA后，已审入口是 `python3 "$REPO/scripts/lab/swap_installer.py" dry-run --serial 5ea34a4500000000000000001123012c --kit "$ONE_LIB_KIT" --transaction-name "$FRESH_TRANSACTION" --lane "$LOCK_OWNER"`。外环完成绑定后才将 action 换为 `apply`；所有变量须准确绑定。使用唯一未占用事务名，保留 state。`--accept-baseline` 不适用于此单库。
4. 单次真实原神安装触发按需服务；在串行设备通道的最早可采样点核新 loader 的 boot/PID/birth/exe/maps dev+inode/process-root SHA7c24、无 deleted；安装前不存在 loader 不是失败，但安装后的磁盘SHA不替代实际加载证据。服务太快退出且没采到时，记 loaded unknown，不虚报候选验证通过。若原先有消费者，则先绑定其准确服务回收方式；未绑定时不能部署。历史 pair 重启命令仅留作来源，不用于此默认路径。
5. `swap_installer.py` 自身 verify 偏向 foundation/libbms，不能替代上述核验；它 remount ro 的 finally 非强制成功，需额外核根ro、alias元数据及全指纹只有预期两处变化。apply/rollback都要核。
6. ZigZag launch-only 对照；原神 exact APK `abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc`，安装前再核不存在。保留 bm body+两层rc、包UID/nativeLibraryDir、ABI成员SHA；任何非零错误码/失败body即安装失败。先收安装日志/首fatal，再允许清日志启动。成功后同一次launch取t5/t20/t60实际截图；facts原样引用，不按计划写张数。遇资源/登录/同意页停止。G06 原神0张是真实旧结果，不能沿用为本次计数。
7. 回滚先停本窗可证明所属的目标；不卸载、不删数据。复核全maps：候选消费者已退出则不需服务动作，直接从**本轮**事务两份51e1备份恢复；仍活着才使用已绑定的准确服务回收。`swap_installer.py rollback` 使用同一 kit/transaction/lane；不回到旧2c9、不整代替换。恢复双alias SHA/元数据/根ro、原实际加载对象与完整runtime/boot/mount前像，再按 fresh 设置恢复 power/focus/hilog，做恢复对照并复核设置。若服务仍按需休眠，loaded-baseline明确unobserved；G13可分别判文件/设置恢复，不写已加载或游戏成功。
8. 缺任何恢复证据均移交外环、保持恢复未完成，不报告成功解锁。unexpected reboot 先重新采样和当前generation恢复，不调用旧G06或#79的旧代重放命令。

## 当前关键缺项

| 缺项 | 最小补件 |
|---|---|
| 完整消费者状态/按需声明 | `next-reads.json` + 实际被引用的profile/import；随后锁下复核 |
| 当前运行时是否恢复及本轮恢复前像 | `runtime-preimage-reads.json` + fresh mountinfo/current-generation对齐、持久输入及准确恢复argv |
| 原件持久备份/精确事务 | 两alias独立host备份51e1，唯一事务、state、锁holder/start/boot |
| 现存消费者分支 | 只有存在消费者时才补准确服务回收argv及来源；无消费者分支明确填“不需要”，不是泛重启 |
| fresh设置、数据和对照 | 完整G06 before语义、11目录不存在、ZigZag输入与恢复smoke；不复用旧config/fingerprint |
| 执行与恢复闭环 | 外环组合锁/安装/采样/rollback/before_unlock；原件与loaded/config缺证不得成功解锁 |

`first-launch/recovery_hook.py` 可复用语义，但其旧配置/期望值不能直接执行；应先恢复库再检查 original fingerprint。`board_run.py` 的 shard 会带 `--reinstall`，不直接照搬到可能已有包的窗口。此交件不是已签名设备 runner。
