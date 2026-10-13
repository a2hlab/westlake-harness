# 最终证据归档与签认：无哈希循环的顺序

结论：**动态原证据E固定 → 证据归档A远端核SHA → 归档回执R固定 → 新最终签认S绑定R的文件SHA → S另作小归档B或Git固定。** A中不得包含S、R或A自身；S不得反向绑定包含自己的B或自己的Git commit。B的回执或Git commit留在独立交付索引/黑板，不回写S。这里仅补依赖顺序，不改原模板、程序、签认要求或任何既有pin；本次零HDC、零归档执行、零签字。

## 原接口与历史依据

r2的FINALIZE第15行已有“已关闭的128、capture/newproof/live954/review归档”，第16行才填签认，但未明确排除签认自身，故需此NOTE。原UI归档器固定SOURCE/NAMES（5–10行），仅从白名单源生成逐件清单（19–32行），打包时加入的是source-manifest（56–69行），逐成员核验及源前后全等（70–94行），远端核SHA/size后才在归档源外写archive.json（105–116行）。沿用这个方法；该脚本不是任意目录CLI，不可直接执行旧UI实例冒称归档了新128。

V1的final-signoff没有引用persistence/archive字段，persistence是独立后置侧件；不能据“历史有整包”推断V2允许互相钉SHA。当前V2明确有 `dynamic_evidence.final_evidence_archive`，应采用以下单向顺序。

## 最短文件集合与执行顺序（仅root在本轮全部结束后执行）

1. **现在不归档W04或运行中的任何128目录。** 原driver全部结束、锁/收尾完成，逐key图审完成，再按已pin前台补充卡完成当前imehost前台与run.sh核验，得到最终capture。保持现有顺序：两份实际admission → consume/build_seal → 新running proof/verify → 新proof真实live954。若中途证据改变，先完成新的真实输入链再固定，不覆盖旧件。
2. **E的精确白名单只选以下已关闭对象**，由root把实际路径列入原归档方式的源清单；动态路径尚未产出不猜名字、不填完成：
   - 本轮同61b完整128运行目录（8窗record/末档截图/身份前后门/原命令日志与rc/收尾）、collect/facts原文、原signed及R4/R6逐key比较、最终演示集合/排除原因与UI review。
   - 最后前台确认/必要桌面恢复证据（当前Focus/PID/WMS、NUL cmdline、截图、run.sh实SHA及参数观察）和最终collector完整目录（capture.json/snapshot/raw/回执）。
   - 实际RouteB487与Boat18 admission；原consume输出目录（snapshot.actual-adapter.json、overlays.actual-admitted.json、seal.unsigned.v2.json、request.running.actual.disabled.json及binding）；新realization/verify结果与其未被前述源覆盖的精确输入；新proof最终live954报告、process/raw evidence目录。
   - 本次最终操作页、known_limits、证据绑定表及其引用的已有归档回执。preinstall/execution/game/UI/fresh487、f28源码/原日志、ADC与rollback已归档的大件不重复打包；通过已固定归档receipt和SHA闭包引用。新产生而未归档的外部raw/输入必须显式纳入E，不能只留失效本地路径。
   **明确排除**：待填或最终S、A与A自己的archive.json/results/上传日志/remote receipt、含这些输出的父目录。逐个白名单目录打包，不对整个outer/final目录无差别递归。保留原private-backup/非regular检查，不借收口扩大数据范围。
3. **生成A及R**：复用现有“源前后inventory完全相等、tar成员逐件SHA、gzip检查、远端独立SHA/size”流程。A可含只记录E成员SHA的 `__archive_meta__/source-manifest.jsonl`；manifest不可记录A自己的SHA。A固定后，源外写R=`archive.json`，含archive路径、sha256、bytes、source_manifest_sha256与实际verified_remote等字段；保留原上传/核验stdout、stderr、rc，不改成摘要假证据。以上流程不改变验收结论。
4. **root签S**：把R的实际 `{path,sha256}` 填入 `dynamic_evidence.final_evidence_archive`（该sha是R文件的SHA；R内部sha才是A的SHA），再绑定实际128/newseal/newproof/live954和真实签字。S只是新的独立侧件，既有V1/r2草稿不改；不得提前签后又“补归档SHA”改动已签字节。
5. **固定S且结束**：任选现有方式：①S和R及归档操作小回执单独进入B，再产生源外B-receipt；②S/R及必要小回执进入普通Git提交，commit由外部交付记录引用。两者均不得把B SHA/B-receipt SHA/自身commit写回S或R形成环。S已经通过R绑定A；B或Git是S的后置载体，不是S的新准入条件。不自动push。

依赖图（箭头表示“包含或以完整SHA引用”）：`B或Git → S → R → A → E`，B也可带R和小操作回执；**没有任何反向边**。如果某份预先UI review/说明文件拟钉最终S，也将该最终交付说明移到B/外部记录，不让它进入E。发布说明可同时列S SHA、R SHA、A SHA及B/commit，但发布说明自身不纳入它所声明的同一归档。

## 本次只读核对的精确来源

- 原r2待填表：`$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-operations-draft-r2/FINALIZE.zh.md`，行15–16，SHA256 `082ce61f0faf8a9bc3e5a60f48ffd71ad7d7ffb0d6d3031bb44988b0dcb59f31`。
- 原r2模板：`$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-operations-draft-r2/final-signoff.pending.json`，行644–650，SHA256 `306e1480eb890408dc768f0834d0e61658582b1d3360403630882f5dfc9f6a12`。
- 既有归档实现：`$WORKSPACES/westlake-harness/benchmark/2026-10-14-final61b-ui-archive/archive.py`，行5–10、19–32、56–94、105–116，SHA256 `2a1f3b1593547df93c90838478d229c223fbb4feea42ccc0154fb5511306f343`。
- 既有归档回执：`$WORKSPACES/westlake-harness/benchmark/2026-10-14-final61b-ui-archive/archive.json`，行1–14，SHA256 `c42c2b05e811e5571c4f8cf32681fb9b5464103cf839d6adba80ef7084aea116`。
- V1签认：`$WORKSPACES/westlake-harness/benchmark/2026-10-12-v1-seal-execution/seal-final-20261013/final-signoff.json`，行完整文件，SHA256 `5ee1f9076052c57a79443686d18dea147446d241231a6ba8844685390ca286c6`。
- V1持久化侧件：`$WORKSPACES/westlake-harness/benchmark/2026-10-12-v1-seal-execution/seal-final-20261013/persistence.json`，行完整文件，SHA256 `e5dbb2dd48dd61a5de761d3fa9b1a1b5a79deba042e7d27fa9b61b308a206780`。
