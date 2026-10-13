# 61b V2最终封板命令卡（离线/disabled；原V1不覆盖）

root唯一设备写者；T0零HDC。用户执行授权已收到，不能当最终封板签认。已有实际boot `086db6c7-a7e7-40ce-a336-9608adc05afc`、BoatUID20011207、hostUID/GID20011206、hostPID/birth4583/5171、WID33；参数均来自本轮独立原始observation。若后续boot/host参数变化，只能用新实采重新bind/compile/map，不能以这里的数值作永久常量。

| 参数/对象 | 实际来源与当前状态 | 最终准入填写方式 |
|---|---|---|
| 候选boot/READY56/BOUND7 | MAIN `outer/final61b-approved-execution/stage/candidate-boot-result.json` | 已有；首尾boot必须与最终954/图/128关联，不以READY代UI |
| 实际954及独立参数 | 同stage `postboot-selfcheck954.json` live PASS954、`.evidence/parameter-observation.json` | 已有；保留全部raw；若最终epoch变动需新最终收尾采集 |
| running composition | T0 `final61b-next-binding/actual-running-086db6c7/composed/composition.json`，SHA `db98d75cb86c622fef7942548e46a3bd2c9ff343389e597fd4b93150b894610a` | 已有；原postinstall940 base保持，独立WMS绑定新boot |
| 824 source_files/130包 | 原prepare_sources消费上述actual composition；package/nonfile链分离 | 源映射可现在准备；实际snapshot不可抄expected充作实采 |
| 最终snapshot | 原schema `demo-seal-snapshot/v1` | **null**：实际终态首尾boot、captured_at带时区、四文件组、runtime/boot原fingerprint_lines、system_params、130实际包版本/APKhash、完整inventories、errors=[]、mode=live-readonly、remote_write_operations=lock_operations=0；完整性true须实采证明 |
| V2 overlays/admission | 原schema `demo-overlays/v1`、seal_stage=v2，保留RouteB487及Boat18 | **null**：RouteB原artifact/location/source销账链、Boat实际18件/包与独立admission pin。不能把composer overlays.pending的admission=None改称已准入 |
| 同61b128最终结果 | 原8窗121t10+7t20，固定原install-index-final | **null**：原records/各窗hook/同boot marker、完整128 collect/facts.txt原文、图审/own-PID first-fatal比较和保留限制。5ea全量/旧V1的new_61b128_required=false不能抵用 |
| Boat/RouteB/feed/control最终审定 | 本轮同61b真正图/操作record | **null**：Boat原7pin/samePID-birth、圆HUD/无紫及方向/加速/LAP/reset；头条信息流/文章/返回/刷新按原口径；原控制和限制记录，不能以alive/PASS替代 |
| 最终签认 | 原协议的独立新V2 signoff JSON | **null**：完成后approved_by写旧协议字面量`outer(claude)`，actual_reviewer写`outer(codex)`，保留signature_role_note。不是模型身份声明，不伪造签字或先称SIGNED |

从MAIN或指定工作树执行，显式WORKSPACES，所有输出都是独立NEW路径且必须不存在。CARD_DIR为本卡所在新目录；COMPOSITION变量指向上述实际running composition，HASH取完整SHA。

```sh
# 1. 可立即离线派生完整实际源文件map（始终disabled）。
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-13-final61b-source-map/prepare_sources.py" \
  --composition "$COMPOSITION" --composition-sha256 "$HASH" --out "$NEW_SOURCE_MAP"
# 2. FINAL_SNAPSHOT和ADMITTED_OVERLAYS只能在最终真实采集/独立准入后填。
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/t5/build_seal.py" \
  --snapshot "$FINAL_SNAPSHOT" --overlays "$ADMITTED_OVERLAYS" \
  --manifest "$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-baseline/demo-manifest.json" \
  --out "$NEW_UNSIGNED_V2_SEAL"
# 3. 用原next-execution的request模板填实际source_identity/source_seal/全部824源和参数。
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-exact-realization/realization.py" \
  compile --request "$FILLED_V2_RUNNING_REQUEST" --out "$NEW_V2_REALIZATION"
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-exact-realization/realization.py" \
  verify --realization "$NEW_V2_REALIZATION/realization.json"
# 4. T0仅离线重放真正新proof对应的最终raw observation（不是live PASS）。
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-toutiao-recovery-review/r5-binary-collector/selfcheck_entry.py" \
  --checker realization --realization "$NEW_V2_REALIZATION/realization.json" \
  --serial 61b0657200000000000000000324012c --boot-id "$FINAL_CAPTURED_BOOT" \
  --observed "$FINAL_V2_RAW_OBSERVATION" --out "$NEW_OFFLINE_REPLAY"
```

schema接法：build_seal输出`demo-seal/v1`且seal_stage=v2，是unsigned源码身份，不是最终签认；realization输入`exact-realization-request/v1`、phase=running、execution_enabled=false。source_identity={kind:seal,path:NEW_UNSIGNED_V2_SEAL,sha256:完整实际SHA}，source_seal等于同一path/sha256；source_files必须完整824（APK130不混入），parameters来自最终独立host/WMS，parameter_evidence与source_parameter_evidence必须与新seal capture boot/source run SHA对应，继承原v6精确pins不改。user_approval用已land next-execution `user-approval.realization.json`（由真实user授权映射APPROVED/approved_by=user）；不能把它当outer signoff。realization输出`exact-realization/v1`、candidate/not_sealed、same-board-selfcheck、restore_allowed=false；verify通过也不是SIGNED。

最终live核验仅root通过原binary-safe R5入口新采集；其proof SHA、mode=live-readonly、完整954/raw及首尾boot须绑定最终new realization，不借旧proof的preseal954结果作“新proof已实测”。最终签认另写NEW_FINAL_SIGNOFF，绑定新seal/proof、实际954、新同61b128、Boat/feed/control、授权、artifact/build闭包和恢复索引，当前所有未到pin为null。原`final-signoff.json`没有自动签认CLI，不能跑旧V1 step脚本伪装新V2封板；原appendix要求candidate-fingerprint来源，当前seal-source running proof不符，直接走原running compile/verify，不套错appendix。保留所有原V1文件与限制，不覆盖、不推送。
