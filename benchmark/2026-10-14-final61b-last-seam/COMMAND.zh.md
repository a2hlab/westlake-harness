# 最终 consume → 原 compile → 原 R5 命令卡

静态接缝 READY；未发现新增离线阻断。冻结 collector `main 8cf3a7c059` 不变。原 validator 已离线实跑 rc0，1053 原始回执的8项 readings/SHA/双 rc/boot/UID/GID/PID/birth/NUL/WMS 均通过；这只是 `recorded-evidence-validation-only`，不证明最终时刻进程仍在运行。当前 round/pins 未改，T0 不执行以下设备命令。

1. 最终 collector 实采后，root 在独立新目录复制两份 pending admission，填写 `snapshot_capture={path,sha256}` 和 **同61b** `same61b128_review={path,sha256}`。保留全部 exact_members/source/rollback/UI 原 pin；依据真实审定填写 ACCEPT 判词及实际签名，旧协议 `approved_by=outer(claude)` 与实际 `actual_reviewer=outer(codex)` 分开。T0 不预填 `admitted=true`。consume 不检验128判词内容，最终 signoff 必须独立绑定该实际128报告及限制。

2. 设置下列变量为实际独立签认文件和全SHA；`V` 是全新兄弟输出，不能放入已归档的 `final61b-approved-execution`。`C` 保持已审独立采集路径。逐条 rc0 才继续，异常保留原始输出，不复用半成品目录。

```sh
set -eu
M="$WORKSPACES/westlake-harness"
P="$M/benchmark/2026-10-14-final61b-v2-collector"
C="$M/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/final61b-seal-capture-v2"
: "${ACTUAL_CAPTURE_JSON_SHA:?}" "${REAL_OUTER_ROUTEB_ADMISSION:?}" "${ROUTEB_ADMISSION_SHA:?}"
: "${REAL_OUTER_BOAT_ADMISSION:?}" "${BOAT_ADMISSION_SHA:?}" "${V:?fresh independent output directory}"
test ! -e "$V"
mkdir "$V"
python3 "$P/consume.py" --capture "$C" --capture-sha256 "$ACTUAL_CAPTURE_JSON_SHA" \
  --routeb-admission "$REAL_OUTER_ROUTEB_ADMISSION" --routeb-admission-sha256 "$ROUTEB_ADMISSION_SHA" \
  --boat-admission "$REAL_OUTER_BOAT_ADMISSION" --boat-admission-sha256 "$BOAT_ADMISSION_SHA" \
  --out "$V/bound"
python3 "$M/benchmark/2026-10-12-exact-realization/realization.py" compile \
  --request "$V/bound/request.running.actual.disabled.json" --out "$V/proof"
python3 "$M/benchmark/2026-10-12-exact-realization/realization.py" verify \
  --realization "$V/proof/realization.json"
```

原 compile 自动调用 `observations.validate`，不需要另造 validator。源与目标两份 parameter evidence 都保留原1053 fullSHA `1053dbcae05b269c08a82ef5f31da2c0aad64d3d4308ba3856ffd0efc5c7abe1`；它证明已存086d观察与 request 参数一致。consume 要求实际最终 capture 同086d且完整824源+130包全等；原 `validate_source_rows` 进一步验证源 run.sh 只有独立WMS证明的单个 `WL_PARENT_ID` 数值差异，其余字节不能改。完整源码 pin 已齐，不需要重新建编译器。

3. **仅 root 在当前128结束、独立确认最终 boot 后执行原 R5 live 入口**。`ACTUAL_FINAL_BOOT_UUID` 必须来自本次独立现场，不能仅抄旧1053。当前被冻结 consume 只接受086d；若最终 capture 已换boot，停在 consume，交 root 用原 fresh 参数采集/绑定重新审定独立输入，不能改旧 pin 或把旧观察改标成新boot。

```sh
: "${ACTUAL_FINAL_BOOT_UUID:?independent current full UUID}"
python3 "$M/benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py" \
  --checker realization --realization "$V/proof/realization.json" \
  --serial 61b0657200000000000000000324012c --boot-id "$ACTUAL_FINAL_BOOT_UUID" \
  --hdc /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc \
  --out "$V/final-live954.json"
```

`V` 必须已存在，receipt 和 `final-live954.json.evidence` 必须全新；不传 `--observed`。入口先 verify 新 proof，然后重新采集当前 owner/HAP/WMS/PID/birth/NUL、完整SHA、原非文件门和首尾boot。原 `running_files` 仅由新真实WMS派生 run.sh 的一个数值，不要求最终PID/WID等于旧4583/33，也不允许据新WID忽略实际SHA。要求 rc0、mode=live-readonly、passed=true、完整机械集合954及原nonfile检查通过；新proof路径与全SHA写入真实receipt。

4. root 最终签认绑定实际 capture、两个 admission、新 unsigned seal/新 proof/最终 live954、同61b128判词及已pin有局限UI报告。`compile/verify` 成功不等于 V2 已签；仅实际 outer 完成审定后填最终签名。不覆盖 V1、不借5ea128，不制造 snapshot/errors/PASS。
