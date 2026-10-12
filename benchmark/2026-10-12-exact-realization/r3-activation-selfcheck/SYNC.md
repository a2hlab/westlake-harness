# R3 交接（仅转述，不发送 lane）

此前冻结 placement proof 使用 disabled startup 字节；成功激活后只允许启动目录内
startup.env 与 startup.expected.sha256 两个完整 SHA 换为冻结 prepare 的 enabled
结果。R3 不修改旧 proof、旧 executor 或 r2 restore。其余 487 目标、metadata、前像
以及最终 seal 附加静态件均严格绑定并纳入只读核对。

外环顺序：等待新 exact-5cd-transaction-r2.realization-receipt.json 的 executor_rc=0，
并同时存在 transaction.json、placed.json、placed-000.json 至 placed-486.json；用
build_binding.py 生成 pin 后才能调用 selfcheck.py。原 900 秒失败路径 executor_rc=-15
必须拒绝，不得拿 transaction.json 初现当完成。完整命令见 README.md。

单一 --activation-binding + --binding-sha256 绑定 prepared manifest、历史 admission、
实际父执行与487逐件回执、origin candidate proof、final proof 和 appendix。历史
admission 过期只作为审计信息保留，不能重新执行；不调用锁工具，只核原 lock_tool SHA。
当前 boot 可不同于放置 boot，但 UID/GID、HAP、PID birth、cmdline、WMS WID 都由当前
独立只读证据确认。最终 appendix 的5静态件不得遗漏；seal 非文件判据也原样保留。

交件正例全部 synthetic、仅 OFFLINE_MATCH；actual positive 尚待外环新事务完成。
本地测试 subprocess 被禁用，零设备、零锁操作、零事务执行。不签 seal，不报告上屏。
