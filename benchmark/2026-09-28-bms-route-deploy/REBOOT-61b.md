# 61b 重启取证(#38 ①,2026-09-28)

## 事实(全部只读拉取,原始文件在 VM `~/a2hlab/board/b4-38-reboot-cause/`)

- 板上 `boot_id` 现为 `5a15fcac-f201-4a2f-937e-822e551cb472`,批量窗口(19:53–20:59)时为
  `c254ebe7-927e-43cf-a322-6de47bb98f6d` → 两次 run 之间确实重启过(外环读图结论成立)。
- `/data/log/faultlog/freeze/` 与 `freeze_ext/` 为空;`freezejson/` 仅 3 条应用级 LIFECYCLE 超时
  (fd-notes 20:14、mcdonalds 20:23、ppsspp 20:59 的 foreground timeout,均为 AAFWK 域),
  无 sysfreeze/kernel 记录。
- `dmesg` 尾部是 watchdog_service/nnrt_host/teecd 周期性重启告警(ServiceReap 240s 重试),
  非本次重启的原因;dmesg 环形缓冲只覆盖当前 boot。
- `eventlog/history.log`(145 行)在 `time[20260928205944]`(20:59:44,ppsspp LIFECYCLE_HALF_TIMEOUT)
  之后出现 1970 时间戳条目(第 129 行已有一次 19700101150128,之后 142-145 行连续 1970),
  即系统时钟在 20:59 后丢失,与"约 21:12 重启、RTC 未同步"一致。
- 板上无 RTC 同步:当前 board date = 1970-01-01 19:27(uptime 3631s → 本次 boot 约在 board 时钟 18:06)。

## 结论

无法从板上文件定位重启的直接原因:无 panic/freeze/watchdog 记录覆盖该时刻,时钟跳变使
之后的所有日志时间戳失效。诚实判定:**原因 unknown**;间接证据(20:59 后无任何 2026 时间戳
日志、无 kernel 崩溃记录)与"无日志的硬重启/断电"一致,而非框架 watchdog 触发的有序重启
(有序重启通常会在 eventlog 留 shutdown 痕迹)。批量数据的完整性不受影响(两次 run 都在
c254ebe7 boot 内完成);受影响的是 run2235 复验(跨了重启,点击落在锁屏,已作废)。

## 复验 run2235 作废说明

外环读图:fd-notes/fd-binaryeye 的 t3/final 截图均为锁屏 → run2235 的"点击成功"点在了
锁屏上。根因:复验驱动未校验 boot_id、未校验前台是桌面;desktop_launch 的 layout 搜索
在锁屏页找到了 AppIcon 节点(锁屏下 dumpLayout 仍返回桌面树)并点击,实际未送达。
本条目 ③ 的两道前置门(boot_id 一致 + hidumper 焦点窗口是桌面)就是为此加的。
