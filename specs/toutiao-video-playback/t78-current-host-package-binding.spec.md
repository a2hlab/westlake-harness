spec: task
name: "T78 current installed host package identity"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t77-launch-path-evidence-comparison]
---
## 意图
REA 已恢复，但已分析的 HAP 仍是历史样本。核实当前 61b 安装的自有宿主包身份和入口元数据，避免拿历史样本解释当前白屏。
## 已定决策
- 仅 61b0657200000000000000000324012c，先读锁和 boot，若其他任务持锁则不访问。只读 bm 包信息及其声明的安装 HAP 路径、sha256；不得遍历用户数据。保存 argv/start/end/rc/stdout/stderr。
- 若 SHA 等于 b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0，复用已执行 REA 库存，不重复开同一包。若不同，允许将自有 HAP 拉到本机持久目录，用已授权 open_binary、inspect_artifact complete、close_binary 核包库存及入口元数据；其他 REA 工具不在本卡范围。
- 比对桌面 bundle/ability 与包中声明入口及既有生产记录，列出确切匹配、差异、unknown；不能将匹配或库存完整推成启动成功。限时 8 分钟交件，取包失败直接交原文，不改权限。
- 不运行头条、不改设备、不继续 T71/T74 被停止的故障或 guardian 源码诊断。只交 README/results/原始回执路径，不重试既有 git ref 权限失败，不推送。
## 边界
### 允许修改
- benchmark/2026-10-23-current-host-package-binding/**
- 私有 $HOME/.local/share/westlake/current-host-package-binding-20261023/**
### 禁止
- 设备写入、重启、点击、部署、运行时改动、配置或权限变更、其他板、用户数据和故障记录
## 验收标准
场景: 当前宿主安装包与历史样本匹配
  审核: human
  测试: current_host_package_binding_review
  假设 61b 在线且无其他板锁
  当从包管理器定位自有 HAP 并采集实际 SHA 和入口
  那么报告带 boot/命令回执的匹配或差异，不将包一致当作白屏已修复
场景: 样本不同或读取失败
  审核: human
  测试: current_host_package_binding_review
  假设 HAP 的 SHA 不同或读取被拒绝
  当进行有限包库存检查或归档错误
  那么仅成功读取时提供新 REA 证据，否则保留 unknown 和原始错误，不变更设备或审批
## 排除范围
修复实现、运行期诊断、冷启动验收、反虚拟化、原神、全量 APK。
