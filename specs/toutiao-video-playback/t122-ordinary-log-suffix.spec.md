spec: task
name: "T122 ordinary startup log suffix identity and collection"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t113-ordinary-startup-log-diff]
---
## 意图
补齐T109失败启动普通日志未采的后缀，供公共API/初始化错误对照。文件身份与旧前缀不匹配则交不匹配证据，不归因旧启动。
## 已定决策
- 仅5cd1e3dd00000000000000000923012c；只读list targets、boot_id、uptime、已知日志stat及head，不操作UI、不改设备状态、不重启服务。命令各10秒超时，总窗口60秒，失败不自动重试。
- 两个固定文件 /data/service/el1/public/appspawnx/adapter_child_7011.stderr 与 adapter_child_9860.stderr；每文件最多512KiB。先stat并与T109的inode/size/mtime核对，后stat再核；大小超过上限停止读该文件。
- 新采内容的前131072字节必须与T109原始payload逐字节相同；前后stat稳定才能绑定历史启动，当前boot另记，不将当前boot当旧文件出生boot。任何缺失/变更均写unknown或identity_mismatch，不扩展到其他PID。
- 私有原始日志及命令stdout/stderr/rc/开始结束时间存持久目录；仓库仅收脱敏README/results、字节数/SHA、前缀匹配和身份回执。不分析内存/信号/保护机制，不读取或重做T71/T74/T91/T121停止对象、执行器或watchdog实现。
## 边界
### 允许修改
- benchmark/2026-10-24-ordinary-log-suffix/**
- tools/spec-checks/tests/ordinary_log_suffix.rs
### 禁止
- 设备写操作、部署、随机崩溃归因、其他运行时源码、全量私有日志提交
## 验收标准
场景: 后缀属于历史文件
  审核: human
  测试: ordinary_log_suffix_identity
  假设已知文件小于512KiB且旧前缀回执存在
  当只读采集并核前后stat及131072字节前缀
  那么结果保留完整字节数SHA及身份匹配依据，后缀可交普通API日志分析
场景: 身份不匹配或设备不可用
  审核: human
  测试: ordinary_log_suffix_identity
  假设文件缺失变化或命令超时
  当核验该回执
  那么保留失败原件并标unknown或identity_mismatch，不使用该日志解释旧启动且不扩大设备动作
## 排除范围
部署、封板、执行器修订、内存故障和安全保护分析、修改任何启动控制逻辑。
