# 原消费者收口卡（只填实际动态证据；未执行）

本交件不签字、不触板。用户持续执行授权已存在，不要求重复解封批准。所有旧签字、原始失败组与冻结程序保留。`final-signoff.pending.json` 是原签认模板的独立草稿，不是admission、seal或可执行recipe。复制到独立最终目录后填写，保持本冻结稿不变。

## 待填位置与责任

| 字段（最终签认JSON） | 必须填入的真实对象 |
|---|---|
| `scope.same61b128_executed/review`、`primary_demo_61b.final_128_round/facts/comparison_and_review` | root本轮同61b完整128、原8窗收尾与每key record/末档截图/own-PID；facts原文；原signed基线比较＋peer对R4/R6的逐key图审。121t10+7t20不删减，缺末档不得用t5代替。run旁batch-apps必须恰128；alive、same_class、driver rc0不是图审PASS。 |
| `primary_demo_61b.control_and_popup_review.final_same61b128_popup_review` | 本轮Seal/StudyTracker/DropCount控件及ClipboardEditor形变分级、LifeCounter等对照的实际图审，可指完整128比较表中的相应行。不复跑已经通过的门。 |
| `demo_set.ordinary_app_keys/excluded_keys_with_reasons/final_demo_list` | 从本轮签认逐key机械选取，失败按t4首致命点/画面原因skip；不套旧112或借5ea名单。实际验证过交互的游戏才列交互演示，普通首屏不升级为完整功能。 |
| `dynamic_evidence.capture/routeb487_admission/boat18_admission/consumer_binding` | 原collector最终真实824文件＋130实际包；两份真实准入绑定相同capture SHA、完整exact_members/source/rollback与现有UI pin；消费产物绑定回执。 |
| `source_seal`、`primary_demo_61b.new_seal_realization`、`dynamic_evidence.newproof_verify` | 原consume/build_seal生成独立unsigned V2及原running realization compile/verify的精确pin。来源kind=seal，source_identity/source_seal同一完整SHA。 |
| `primary_demo_61b.final_live954` | **新proof对应**原R5真实live954＋nonfile/参数门及raw。已填 `known_initial_live954/known_ui_closeout_candidate954` 仅为已完成候选证据，不能移填。 |
| `dynamic_evidence.final_evidence_archive` | 已关闭的本轮128、最终capture/newproof/live954及review的持久归档与remote SHA receipt；已有preinstall/execution/game/UI/fresh487归档已填，不包含后来动态数据。 |
| `primary_demo_61b.ui_acceptance_by_outer`、顶层 `approved_by/approved_at/actual_reviewer/status` | outer最终亲自审定后填真实签认；协议literal为 `outer(claude)`，实际reviewer为 `outer(codex)`，时间真实。已存在scoped UI接受不等于完整V2签认。任何缺口保持pending，不能把null替为假PASS。 |

## 128结束后的前台与来源前置（collector之前）

按已land补充卡 `[foreground_supplement]` 原顺序执行，路径和完整SHA钉在 `evidence-bindings.json`。**128 driver全部结束并完成收尾 → 独立只读确认当前imehost Focus/PID/WMS → 必要时原BMS desktop_launch/capture → root真图确认 → run.sh实际SHA先与冻结824预期核对 → collector。** 旧1053及历史final-host只证明历史状态，不是当前前台证据。

只读确认须同boot读取WMS和当前host status/stat/NUL cmdline：原 `observations.parse_window` 绑定唯一可见imehost0及当前PID，再用 `bms_batch.foreground(wm, {current_host_pid})` 核Focus归属；ZOrd≥0或alive不等于焦点。若已确认前台可不重复点击；否则复用补充卡指向的原POST-STAGE BMS `desktop_launch` / `capture`，使用当前有效责任授权、真实锁owner及新的HOST_OUT，不能写旧stage、借过期授权或旁路正在运行的128。随后保存原raw、marker、rc、双端截图SHA，root亲读实际图；clicked=true不替代上屏。不得aa/manual launch、cold-stop、reinstall或自行重启。

前台确认后，先核实际run.sh完整SHA与冻结824预期。传输、焦点、图片或SHA任一不符即停止并保留原证据。WID变化而run.sh未变化仍不保证R5通过；R5实际WMS单字段派生必须与真实run.sh相等。run.sh变化不能绕过consume的824门，不抄现读为expected，不改原pin/冻结consumer。

只有原独立parameter reader证明实际boot/UID/GID/WMS，且原bind_request→compile_selfcheck/prepare_sources证明仅允许的单一WL_PARENT_ID变化，root才按补充卡另建经审定的source/expected/admission兄弟输入与新capture，重走原消费者；其它变化拒绝。无法闭合则按既有恢复授权收尾，不自行写run.sh/解锁。下列collector命令仅在这个前置已完成后调用。

## 原命令最短链

运行前核 `evidence-bindings.json` 中工具/模板SHA；root等待当前128结束，并负责并发与锁，不改正在运行的输入。以下均为原消费者参数，不引入新部署工具。`NEW_*` 为独立不存在路径；`HDC` 为root已批准的原native可执行文件。

```sh
MAIN="$WORKSPACES/westlake-harness"
P="$MAIN/benchmark/2026-10-14-final61b-v2-collector"
SERIAL=61b0657200000000000000000324012c
python3 "$MAIN/benchmark/2026-10-12-seal-snapshot-adapter/collect.py" \
  --serial "$SERIAL" --groups "$P/groups.actual-derived.json" \
  --manifest "$MAIN/benchmark/2026-10-09-demo-baseline/demo-manifest.json" \
  --extra-package org.westlake.imehost --extra-package com.Unity3d.BoatAttackDay \
  --hdc "$HDC" --out "$NEW_CAPTURE"
```

原collector是只读且自身不取锁；真实bookend/raw/remote rc必须保留。当前原consumer预期086d；若实际boot或独立host/WMS变化，先走原精确参数派生，不能硬改expected/忽略SHA。不要复制expected成snapshot。用两个原 `*-admission.pending.json` 模板填写新的真实admission：status以ACCEPT开头、admitted=true、approved_by=`outer(claude)`、actual_reviewer=`outer(codex)`，snapshot_capture钉真实capture.json；保留exact_members/source/rollback/UI_review/independent_UI_review/root_scoped_UI_acceptance和Boat backup_objects完整pins。结构合法不代表准入，未审不能填true。

```sh
python3 "$P/consume.py" \
  --capture "$NEW_CAPTURE" --capture-sha256 "$ACTUAL_CAPTURE_JSON_SHA" \
  --routeb-admission "$REAL_ROUTEB_ADMISSION" --routeb-admission-sha256 "$ROUTEB_ADMISSION_SHA" \
  --boat-admission "$REAL_BOAT_ADMISSION" --boat-admission-sha256 "$BOAT_ADMISSION_SHA" \
  --out "$NEW_BOUND"
python3 "$MAIN/benchmark/2026-10-12-exact-realization/realization.py" compile \
  --request "$NEW_BOUND/request.running.actual.disabled.json" --out "$NEW_PROOF"
python3 "$MAIN/benchmark/2026-10-12-exact-realization/realization.py" verify \
  --realization "$NEW_PROOF/realization.json"
bash "$MAIN/scripts/lab/demo_selfcheck.sh" \
  --realization "$NEW_PROOF/realization.json" --serial "$SERIAL" \
  --boot-id "$ACTUAL_CAPTURED_BOOT" --hdc "$HDC" --out "$NEW_FINAL_LIVE954_JSON"
```

`consume.py`调用原adapter/build_seal，生成 `seal.unsigned.v2.json` 和 `request.running.actual.disabled.json`；原realization为same-board-selfcheck、restore_allowed=false，不是恢复recipe。原appendix的candidate-fingerprint通路不适用于本处kind=seal，不能套错签认。最终signoff没有自动签字命令；outer填写独立侧件，不运行旧 `demo_seal_61b.py` 的裸reboot/reinstall流程。数字824+130=954及RouteB487+Boat18=505是当前精确对象union；今后对象改变须重编，不能用计数相等替逐件检查。

## 已完成5cd恢复与未来恢复入口

`evidence-bindings.json` 的 restore5_* → spare_* 固定了实际链：362f新前像487文件＋29目录完整恢复、释放；第二独立窗原R5→Boat11件7bind→62目标snapshot/policy→单次冷bootc943→真实954与HW/ZZ。5cd隐私对话框未点、Boat游戏未在该板测试；这是完整备机恢复实演，不是仅verify-existing，也不抵本轮61b128。

精确可复用入口为 `integration/routeb-fresh-restore/{prepare.py,executor.py,prepare_stage.py,restore_entry.py}`，参数schema/授权格式钉在原 `ENTRY.md`、`AUTHORIZATION.md`。历史362f/43bc前像、inode、holder、expiry不可热重放。未来执行先由root用实际板/当前boot/完整前像与目录metadata重新调用原prepare；全部487备份/CAS/atomic与目录inode/rollback门保留。第一窗只做487、零boot，批量≤45分钟；完成释放后第二窗Boat与一次冷boot，按现有20分钟执行＋10分钟恢复预算独立授权。不能把两窗塞进旧45分钟，也不能把source回滚称已恢复运行态。

下面仅对root新采并已完成的新恢复对象作离线prepare/preview；无 `--execute` 不会写板。用新部署包对应新serial/UID/control/WID，绝不复制61b参数给5cd。

```sh
CORE="$MAIN/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/routeb-fresh-restore"
python3 "$CORE/prepare_stage.py" \
  --directory-recipe "$FRESH_RECIPE" --directory-recipe-sha256 "$FRESH_RECIPE_SHA" \
  --completed-receipt "$ACTUAL_RESTORE_RECEIPT" --completed-receipt-sha256 "$RESTORE_RECEIPT_SHA" \
  --deployment "$FRESH_DEPLOYMENT" --deployment-sha256 "$FRESH_DEPLOYMENT_SHA" \
  --seal "$MATCHED_CANDIDATE_SEAL" --seal-sha256 "$MATCHED_SEAL_SHA" \
  --hdc "$HDC" --hdc-sha256 "$HDC_SHA" --out "$NEW_STAGE"
python3 "$CORE/restore_entry.py" --v2-recipe "$NEW_STAGE/recipe.disabled.json" \
  --recipe-sha256 "$NEW_RECIPE_SHA" --out "$NEW_STAGE/preview-output"
```

正式执行由原authorizer新有效授权和enabled plan/deployment/recipe精确pins控制，再用同entry的 `--execute`；本页不生成授权。原 `demo_restore.sh --v2-recipe` 仍指旧61b/r2入口，`--v2-5cd-recipe` 指旧5cd sibling，**均不可当上述fresh f28入口的自动别名**。签认绑定实际已验direct entry，防止用户误走旧版本；wrapper本轮未修改。

失败按原provider/事务回滚：已授权UID子家族停止与所有权核对后再卸载；不杀system父、不删除用户数据或未知目录。Boat保留实际11件备份/intent/partial与审计终态，原RouteB回滚索引只24controls、runtime/stage retained；必须区分这两个范围和5cd恢复实演。后boot需要新current-boot授权及严格恢复复核，不能把前boot receipt当完成。具体原pins见 `boat_rollback`、`routeb_rollback`、`restore_authorization`，不新造回滚命令绕原门。
