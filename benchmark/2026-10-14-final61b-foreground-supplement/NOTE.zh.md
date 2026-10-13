# final 前台恢复补充（独立件；冻结6件不改）

**需要恢复并确认 imehost 前台，放在128 driver 完全结束后、最终 collector 之前。** 原 `integration/final61b-execution-20261013/handoff/POST-STAGE.md:48–88` 明确 controls 后重复原 BMS desktop_launch/capture，再做 final954；此前遗漏已发生真实 nonfile failure。若当时只读证据已确认 imehost 在前台，可避免无意义重复点击；否则走原桌面入口，不能 aa/manual/cold-stop/reinstall。旧 final-host record 只证明历史调用成功，不能当本轮末尾前台证据。

复用该 POST-STAGE 原 Python snippet，只换实际 serial/boot/HDC、**当前有效责任授权**和独立 `HOST_OUT`；旧 stage 已归档，不能写回、不能借已过期 window-authorization。保持当前真实持锁 owner，原 `Board.ready()` 按 held 首token核 owner、设备和boot；不偷锁，不在运行中128旁路操作。源码 `bms_batch.py` fullSHA：`f41efa6ae2450adadda1f02c3c09335b74479c7d025872bbf95b3c8a444b177c`。实际调用保持：

```python
b.desktop_launch(board, {'package': 'org.westlake.imehost', 'launch_activity': 'EntryAbility'}, remote, out, record)
record['capture'] = b.capture(board, remote + '/host.jpeg', out / 'host.jpeg')
b.save(out / 'record.json', record)
```

原方法通过桌面精确图标 `AppIconCommonView_org.westlake.imehost.EntryAbility` 点击，保存意图、原命令/真实remote marker及截图双端SHA；`clicked=true` 不是上屏签认。调用后保存同boot只读 `hidumper -s WindowManagerService -a '-a'`、当前host的status/stat/NUL cmdline及run.sh SHA。用原 `observations.parse_window` 确认唯一可见imehost0并绑定当前PID，再用原 `bms_batch.foreground(wm, {current_host_pid})` 确认 Focus window 归属；原parse_window仅要求ZOrd≥0，不证明有焦点。最终屏幕仍由root读实际snapshot_display截图。原 shell/marker/传输失败、ambiguous focus或截图不符均停止，不以alive代替。

**先核 run.sh 实际SHA与冻结824预期，再 collector→consume→compile→R5。** desktop_launch 本身不改run.sh；但若host重建导致WID/相关文件变化，不能假定所有SHA仍等。WID变化且run.sh未变化也不能直接认最终R5通过：原R5按实际WMS派生的一字段SHA仍须等于真实板上run.sh。若run.sh任何字节变化，consume的824精确集合门先拒，后续R5动态归一化无权跨过。

失败退路：保留本次host/capture/raw/rc，不重标1053、不抄现读为expected、不改当前round/pins或冻结consume；向root报具体WID/run.sh差异。仅当原独立parameter reader证实新boot/UID/GID/WMS，且原bind_request→compile_selfcheck/prepare_sources证明仅原允许的单一WL_PARENT_ID变化后，root才可另立经审定的source/expected/admission兄弟输入与新capture，重走原消费者；其他变化按原门拒绝。无法恢复前台或来源不能闭合时停止封板，由root按既有授权恢复入口收尾；不自行重启/写run.sh/解锁。T0本次零设备执行，无新runner。
