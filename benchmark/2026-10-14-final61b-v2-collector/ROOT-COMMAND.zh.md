# 原V1实际collector的V2参数交件（T0不执行设备命令）

现已填完四组：runtime124、boot36、installation164、overlays505；跨组重复5件保留且SHA相同，unique文件824。原128 manifest加imehost HAP和Boat两个extra package得到130包，文件+实际包archive共954。原collector与adapter fullSHA见collector.readonly.disabled.json；inventory wildcard原V1和原candidate均为[]，原值保留，不新增/豁免目标。

ROOT只有最终capture、同61b128审定和实际outer签名待做；现有game/feed独立有局限UI报告已pin。本包所有路径/schema/pins均已机械对齐现实际stage/running composition/source-map；无snapshot.json或伪造errors[]。先独立审本包，然后root从MAIN/显式WORKSPACES运行：

```sh
P="$WORKSPACES/westlake-harness-t0/benchmark/2026-10-14-final61b-v2-collector"
C="$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final61b-seal-capture-v2"
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-seal-snapshot-adapter/collect.py" \
  --serial 61b0657200000000000000000324012c --groups "$P/groups.actual-derived.json" \
  --manifest "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/demo-manifest.json" \
  --extra-package org.westlake.imehost --extra-package com.Unity3d.BoatAttackDay \
  --hdc /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc \
  --out "$C"
```

C必须不存在；原collect自动写capture.json、全部stdout/stderr/host+remote marker和snapshot.json，接法是demo-seal-snapshot/v1，不用泛用board_state_snapshot摘要。原工具自身不取锁、不写板、不做UI签认，但root必须控制当前窗口和batch责任避免其他板写者。collector首尾boot、所有真实rc/marker保留；输出必须是086d且完整824文件/130包/954匹配现actual composition，否则停。任一异常保留原capture，不重写errors。groups只有目标列表，不带expectedSHA；每个SHA从真实sha256sum回来，BMS顶层版本/真实codePath或entry.hap独立读取，不抄manifest版本。

本地接续（真实collect完成后，root/T0都可离线消费）：

推荐先用本包最小local binding接缝（不是新collector/编译器）：它重新调用原adapter，核实actual capture完整SHA、synthetic=false/boot086d、824/130实际字节/版本全等及两份真正outer admission；全部通过才调用原build_seal并填原running request。

```sh
python3 "$P/consume.py" --capture "$C" --capture-sha256 "$ACTUAL_CAPTURE_JSON_SHA" \
  --routeb-admission "$REAL_OUTER_ROUTEB_ADMISSION" --routeb-admission-sha256 "$ROUTEB_ADMISSION_SHA" \
  --boat-admission "$REAL_OUTER_BOAT_ADMISSION" --boat-admission-sha256 "$BOAT_ADMISSION_SHA" \
  --out "$NEW_OFFLINE_BOUND_V2"
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-exact-realization/realization.py" compile \
  --request "$NEW_OFFLINE_BOUND_V2/request.running.actual.disabled.json" --out "$NEW_RUNNING_V2_PROOF"
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-exact-realization/realization.py" verify \
  --realization "$NEW_RUNNING_V2_PROOF/realization.json"
```

consume.py不读板、不签字，缺capture/admission会rc2且不写输出。actual admission必须admitted=true、approved_by=outer(claude)、actual_reviewer=outer(codex)，绑定exact_members/source/rollback/实际capture.json和已有独立UI原pin。same61b128仍由最终signoff独立绑定，不能以此软件身份准入抵代。新proof仍须root真实最终live954。

下面原CLI顺序保留供独立复验：

```sh
# 可独立重放原adapter，重读全部raw SHA/hostRC/remoteRC/boot和130实际BMS。
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-seal-snapshot-adapter/adapter.py" \
  --capture "$C" --out "$NEW_ADAPTER_REPLAY_SNAPSHOT"
# 独立admission经实际outer复验填写后，用本包overlays.pending为模板，只有两个admission pins待绑定。
# RouteB原9f历史487源索引显式pin+旧24控制rollback（保留runtime/stage，61b未板演练），Boat3989 source/49d7 enabled实际部署双角色及原28个backup/metadata文件pin、provider/helper和18成员roles已完整；不得变member/shas。
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/t5/build_seal.py" \
  --snapshot "$C/snapshot.json" --overlays "$REAL_ADMITTED_V2_OVERLAYS" \
  --manifest "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/demo-manifest.json" \
  --out "$NEW_UNSIGNED_V2_SEAL"
```

RouteB487 admission定义不包含HAP文件成员；HAP始终在原完整824文件及130包链和488保护中。Boat18=11placement+7bind，UID20011207、private3/ADC/f28/bridge/JAR不变。两个独立admission.pending文件已有完整members/source/rollback/live954证据pin和identity_match_verified_offline=true，UI_review已pin本轮真实有局限独立game/feed及root scoped接受报告；但capture/128 review/实际签名仍待填，admitted=false、approved_by/actual_reviewer为null；outer实际完成独立审定才填写旧协议approved_by=outer(claude)、actual_reviewer=outer(codex)，status/accepted只能如实判。build_seal只验证Boat admission pin的结构，不读取其内容；因此不能把待签draft的fullSHA塞进去冒充已准入。本包overlays.pending的admission path/SHA都是null，原compiler应拒绝，生产入口不得使用draft。

最终新的running request用已land命令卡request.running.final-seal.pending模板，填新unsigned seal同一source_identity(kind=seal)/source_seal pin和实际snapshot boot/WMS即可原compile/verify。原collector不采host PID/birth/WMS；本轮已存在086d独立1053dbca完整原观察，可在原validator证明同capture boot/source run SHA并且原参数未变时使用；变boot/WID/owner不能自行变更或借旧观察，需root原R5新实采。新proof最终live954/readback、同61b128及实际outer签名未到前不称SIGNED；已有Boat/feed scoped图审及其限制保持，不覆盖V1，无push。
