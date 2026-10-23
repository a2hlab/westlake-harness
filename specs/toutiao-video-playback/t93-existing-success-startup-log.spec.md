spec: task
name: "T93 existing successful process startup log"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t92-successful-launch-ui-latency]
---
## 意图
T92完整UI区间无法解释spawn后约34秒无相关marker的时段。只读已有成功进程6291的普通stderr起始片段，寻找实际带时间的启动阶段；不再做部署预检，不重启或重现白屏。
## 已定决策
- 外环仅用已可用HDC收取固定日志，Codex内环负责分析；CC不分析。仅61b0657200000000000000000324012c，先held和boot确认；他人holder或boot非61aa5791-fd69-4bbb-a7b5-333b5d913c81立即停止。
- 仅stat并读取/data/service/el1/public/appspawnx/adapter_child_6291.stderr的前300行且最多128KiB。路径来自T86已核普通日志命名及T87实际PID，不读其他PID，不读faultlog/内存/配置/监督器源码，不做退出归属。原件只存持久home，公共输出只选无敏感数据的小片段和哈希。
- 采集总限60秒，每命令<=15秒，记录argv/起止/rc/stdout/stderr，检查正文错误。零设备写入、零UI、无trace、无重试。日志可能含旧行或无时间戳，不能仅由文件名或mtime推本次身份。
- cx-reentry-peer结合已核T87同boot时段，仅提取可绑定时间/PID的普通阶段记录，与第一条trace marker对照。无时间就unknown，不补猜的阶段耗时，不看被拒对象；最多4分钟交一页结果，有明确可优化的自有API调用再报，否则给精确缺口。
## 边界
### 允许修改
- benchmark/2026-10-23-success-startup-log/**
- 私有 $HOME/.local/share/westlake/success-startup-log-20261023/**
### 禁止
- 设备写入/新启动/重启/部署、其他日志路径、T91预检、此前被拒源码、退出/信号/内存分析、CC分析任务
## 验收标准
场景: 普通日志片段有可绑定时间
  审核: human
  测试: success_startup_log_review
  假设目标同boot且日志存在
  当限时收取片段并离线核对时间与PID
  那么只对有依据的阶段给出时刻/区间和原行，不把日志缺失当未执行，无设备改动
场景: 身份不符或读取失败
  审核: human
  测试: success_startup_log_review
  假设holder存在、boot改变、文件缺失或命令错误
  当停止条件触发
  那么保留失败原件且不重试、不换路径补证，结论unknown
## 排除范围
修复部署、故障归属、冷启动签认与重试受阻任务。
