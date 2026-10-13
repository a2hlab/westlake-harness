# 61b V2 后继执行链（T0离线预审；T4唯一板写者）

用户授权已生效：主树 `outer/final61b-user-authorization.json`，不再请求重复解封。此文件只列原命令，不由T0执行设备命令。原V1签认、源码map和恢复前像保持原件。5ea full128只作候选先验，不能抵61b本轮128。

API增量精确landing：T0提交 `27ecb28c6`，`benchmark/2026-10-13-api-progress-r6-full128/landing-paths.txt` 共38新文件；freeze SHA `447f7aaf4edddcb29602e1195be08aec6be4c8135126395f0b1cc6ef0a8f3f9f`。

## 第一可用原命令链

从主树根目录执行，`WORKSPACES`为实际workspace父目录。以下大写输入变量必须由真实同61b回执赋值，未知仍null；不能把占位符执行成实值。`OUT`必须是全新目录。先完成T4已领的安装/部署/单boot及独立host/WMS采集，再跑原driver；不能在当前部署锁未释放时重取锁。

```sh
P=benchmark/2026-10-09-demo-boatattack/v2-20261013/integration
SERIAL=61b0657200000000000000000324012c
AUTH=benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final61b-user-authorization.json
INDEX=benchmark/2026-10-09-demo-baseline/t3/install-index-final.json
INDEX_SHA=f123249f9670c2af5cb6b1d6ed7aef0f7b803af2ea8d69e4f74009d46005f63b
# 原bind_request将actual plan/source940/newboot参数绑定到一个disabled请求。
python3 "$P/final-v2-f28/selfcheck/bind_request.py" \
  --template "$P/final-v2-f28/selfcheck/request.61b.pending.json" \
  --plan "$ACTUAL61B_PLAN" --base-selfcheck "$ACTUAL61B_SOURCE940" \
  --base-observation "$ACTUAL61B_SOURCE940_RAW" \
  --running-parameter-evidence "$ACTUAL61B_NEWBOOT_WMS" \
  --current-boot "$ACTUAL61B_CANDIDATE_BOOT" --out "$BOUND_REQUEST"
python3 "$P/final-v2-f28/selfcheck/compile_selfcheck.py" \
  --request "$BOUND_REQUEST" --out "$COMPOSED"
# 独立审定实际composition完整SHA之后，绑定原954身份和原128八窗。
python3 "$P/final-v2-identity-f28/prepare_identity.py" \
  --composition "$COMPOSED/composition.json" --composition-sha256 "$COMPOSITION_SHA" \
  --install-index "$INDEX" --install-index-sha256 "$INDEX_SHA" \
  --boot-before "$ACTUAL61B_DEPLOY_ORIGIN_BOOT" --out "$OUT"
# 仅T4执行；整个driver连续运行，不是逐窗手工拼记录；本命令本身不部署/重启。
python3 "$P/final-v2-identity-f28-61b/run_candidate_post_reboot.py" \
  --out "$OUT/round" --execute --serial "$SERIAL" --authorization "$AUTH"
```

原61b index静态已核：完整128 key，全部原record同61b、SHA pin正确、APK全等canonical manifest、install return_code0及success_text=true。可复用历史真实安装provenance；不能称这些record是本轮新安装。实际当前全部APK另由full954 prelock/read验证。使用该原index，不调用硬5ea的compile_index.py，也不复制5ea安装信用。INDEX_SHA见独立program/input pins回执。

## 必需真实字段和门

- actual plan：同61b，真实Boat UID、11 members/7 binds、实际target mode/UID/GID/label，原940 source-R5和plan.boot_id一致；T4实际capture产出前保持null。
- 候选boot：部署后真实UUID；部署origin是这次部署前真实UUID，不是旧v1 boot常量。原identity要求候选boot不同origin，并以独立WMS derivation的current_boot和observed-post-reboot-boot.json锁定全部8窗同boot。
- 独立host/WMS：完整raw、host UID/GID/PID/birth、WID及首尾boot；原running_files只派生唯一run.sh的WL_PARENT_ID。不得猜UID/WID或借另一板参数。preboot composition只到禁用态source准备，finalboot必须重新绑定/recompile。
- 原128/121t10+7t20/8窗，完整954 SHA、507 metadata、5目录、原319=315keep+4replace、RouteB487+HAP、所有真实原始rc/marker和包UID门保留。
- 原helper的`pending: user unseal`文字是旧静态模板提示，已由真实新用户授权满足，不是新增执行门。原driver的authorization参数只检查非空，不会解析授权JSON；outer/T4应事先核本记录完整SHA和范围并另满足原deployment/entry的实际有期限/held协议，不能把该参数当成全部授权检查。

## 分窗锁、失败与恢复

原driver每窗先Orb输入解析/host探针/pre-lock954，再只开启该窗plan，Mac原demo_board_run取得该窗独占锁，after_lock954、原smoke、launch-only/shards/records、finally before_unlock954。每窗≤45min，35min停止新key；一窗完全退出/UNLOCK之后才下一窗。T4是实际唯一板写者；原plan逻辑owner为cx-t0，不能与当前部署阶段不同owner的锁混用。所需批次授权/恢复责任应覆盖整个八窗，单窗预算不改。

任何hook/smoke/infra/boot漂移或缺record即stop，原collect保留partial facts；不能删除失败app或改raw foreground_unconfirmed/rc。before_unlock非0时原board_run保锁，父driver不自动rollback。必须等当前子进程真实结束；T4查真实held：同owner只能同锁原provider rollback→原验证/必要恢复boot→HW/ZZ及完整原基线核验后按owner解锁；无锁可用原entry新授权副本恢复；未知/他人owner保锁报outer，不抢锁，不并发恢复，不沿用5ea retained entry。原candidate provider的实际事务/backup/rollback回执须由T4绑定；目前未知，仍null。成功路径不得自动回V1后再宣称f28已封。

原故障回滚CLI（仅T4、原子进程真实结束后；各未知变量仍null）：

```sh
python3 "$P/final-v2-f28/board61b/provider/installer.py" \
  --plan "$ACTUAL_ENABLED_PROVIDER_PLAN" --action rollback --execute \
  --authorization "$FRESH_SAME_OWNER_ROLLBACK_AUTH" \
  --authorization-sha256 "$ROLLBACK_AUTH_SHA" --out "$ORIGINAL_PROVIDER_TRANSACTION"
```

rollback auth必须含approved_by=outer(codex)、实际enabled plan SHA、同61b、origin_boot_id=plan原部署origin、boot_id=实际当前候选boot、action=rollback、有效expires_epoch、holder=真实held输出完整整行；不能只传owner token。rollback允许不同于origin的新boot，但不能篡改源plan；`--out`是原已有backup事务目录，不是新空目录。必要恢复boot仍走T4原singleboot入口的新当前boot授权，绝不复用旧origin/expiry。恢复entry/HWZZ参数未交付，保持null，不能用猜出来的命令替代。

## 最终824文件+130包消费者（原编译器）

```sh
python3 benchmark/2026-10-13-final61b-source-map/prepare_sources.py \
  --composition "$COMPOSED/composition.json" --composition-sha256 "$COMPOSITION_SHA" \
  --out "$FINAL_SOURCE_MAP"
python3 benchmark/2026-10-09-demo-baseline/t5/build_seal.py \
  --snapshot "$ACTUAL61B_954_SNAPSHOT" --overlays "$ACTUAL_ADMITTED_V2_OVERLAYS" \
  --manifest benchmark/2026-10-09-demo-baseline/demo-manifest.json --out "$NEW_UNSIGNED_V2_SEAL"
python3 benchmark/2026-10-12-exact-realization/realization.py compile \
  --request "$ACTUAL_FILLED_RUNNING_V2_REQUEST" --out "$NEW_V2_REALIZATION"
python3 benchmark/2026-10-12-exact-realization/realization.py verify \
  --realization "$NEW_V2_REALIZATION/realization.json"
```

824 source_files是文件集合，130 APK另走原package/nonfile链，合计954；不把APK混进source_files、不改原V1。新seal仍unsigned，需同61b本轮954 live原始回执、Boat/RouteB/control真实图和同61b128原facts/ownPID致命点/图审，outer实际签认后才称V2完成。新running request的source_identity(kind=seal)/source_seal pin同一新seal，phase=running/execution=false；两个parameter evidence字段绑定实测新boot，完整824 source pins及同boot源run SHA必须对应snapshot。

原最终954 binary-safe R5核验：live模式仅T4调用原入口，独立明确HDC路径；T0只能静态/离线消费其原始observation。以下两个模式不可互换：

```sh
# T4 live；ACTUAL_HDC为已审真实本机可执行工具路径，FRESH_LIVE954_OUT全新。
python3 benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py \
  --checker realization --realization "$NEW_V2_REALIZATION/realization.json" \
  --serial "$SERIAL" --boot-id "$ACTUAL61B_CANDIDATE_BOOT" \
  --hdc "$ACTUAL_HDC" --out "$FRESH_LIVE954_OUT"
# T0可离线重放真正采集到的observation；其mode只能offline-comparison，不能记live PASS。
python3 benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py \
  --checker realization --realization "$NEW_V2_REALIZATION/realization.json" \
  --serial "$SERIAL" --boot-id "$ACTUAL61B_CANDIDATE_BOOT" \
  --observed "$ACTUAL61B_954_RAW_OBSERVATION" --out "$FRESH_OFFLINE_REPLAY"
```

原signoff工具不自动产生新用户/outer签名；保留待签消费者槽，不借原V1的new_61b128_required=false或5ea full128来满足新授权明确的same61b128。source-map原helper任何旧pending解封文字以本包user_unseal_pending=false及权威授权为准，真实证据门不变。

确切接口差异：原realization编译器要求user_approval文件`status=APPROVED, approved_by=user`；新权威记录字段为`status=USER_APPROVED_EXECUTION, authorized_by=user`。不能直接把权威记录传给原编译器，亦无须再问用户；本包提供独立schema映射receipt，保留权威完整pin及用户原话，不改原compiler门。其余actual composition/boot/UID/WMS/deploy/snapshot/admission/61b128/signoff字段都保持null。
