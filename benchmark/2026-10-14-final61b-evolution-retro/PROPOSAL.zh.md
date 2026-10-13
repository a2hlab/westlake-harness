# 待主外环采认的最小知识增量

建议新增 FLAW 0 条；本轮只推进已有 FLAW-009 一条，FLAW-001/010 只复核覆盖和健康，不改状态、不另立案。

## FLAW-009 追加证据建议（不直接改原记录）

2026-10-14 #91 收尾补充卡将 `foreground(wm, {current_host_pid})` 当成原门，拒绝同 UID 的合法头条焦点。原 BMS `bms_batch.py:767–772` 实际传目标 UID 的全部当前进程；`foreground:376–382` 只做集合归属。同 boot 086d 原 live954 已接受 host4583/WID33 与 focus6789/WID30；静态复核只读函数定义、没有沿真实调用点追到集合来源，会把补充文案变成未授权新门。复审必须核对真实调用参数的对象与集合范围，并对已通过的原始输入做本地消费对照。保留 singleton 失败，新侧件纠正；不修改冻结 consumer 或 expected。FLAW-009 保持 open，本次不因收尾成功关闭。

## DIGEST 一行建议

- 2026-10-14 #91 前台对象：原 BMS `foreground(wm,pids)` 的 pids 是当前目标 UID 全进程集合，非 `{host_pid}`；同 boot086d 的 host4583/WID33 可见、头条6789/WID30获焦点是原954已接受状态，宿主参数/WL_PARENT_ID仍33，不改成焦点30。身份/UID未知或焦点歧义仍停；保留错误 singleton 原失败，按原调用对象纠正后新824文件/130包采集、新proof live954实际PASS，不能据此提前宣称V2已签。证据 `benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-foreground-object-review/`、`outer/final61b-finalization/`、`outer/final61b-v2-realization/`。

## RUNBOOK 一行建议

- 收尾前台核验先沿原 `bms_batch.py:767–772` 取同boot当前目标UID进程集合，再传原 `foreground(wm,pids)`；宿主唯一可见性、UID/GID、PID/birth/rawNUL与宿主WID按原observations独立核。不得把合法同UID应用焦点收窄成host-only，不因child获焦点改WL_PARENT_ID/run.sh；UID未知/焦点歧义照原门拒绝。失败留原目录，纠正只写新侧件；新824精确核对→collector→新proof→实际live954仍全部执行，历史PASS只证明对象语义。

## 可供主外环落板的定式 R2（一条，待采认）

> 外环(codex)·R2 记档(#91): [家族:producer-consumer-interface] 本外环采认的foreground补充卡误传{host_pid}，将同UID合法头条focus拒绝；原BMS真实调用传目标UID当前进程集合，同boot旧954已接受host4583/WID33+头条6789/WID30。WL_PARENT_ID仍宿主33，未改冻结函数/expected；原失败保留，经原集合语义纠正后新824/130与新proof live954通过。归入已有FLAW-009，不新设host独占焦点门、不以历史PASS代新终检、不提前声称V2已签。证据 benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-foreground-object-review/results.json 与 outer/final61b-finalization/host-attempt-result.json。

## 其他候选处置

- EVO-0142：signed/R4/R6 内容态差异属于已有 FLAW-001 的声明必须对照真实对象规则；已有 DIGEST 记录了三方比较和内容未证限制，不新开记录、不篡改原128 verdict。
- FLAW-010：双哨日志已证明真实0140/141/142采集，本轮harvest/retro用于后续正常节拍；是否关闭由主外环依据本报告决定，本任务不自动关闭。
