spec: task
name: Independent remote recovery rehearsal
satisfies: [REQ-ARTIFACT-RECOVERY]
depends: [t1-store, t2-demo-intake]
---
## 意图
把已验证对象发布到独立服务器，并从服务器回下载到空store后恢复到新目录，证明不依赖原worktree。恢复验收保留原始传输日志与哈希，不把同Mac隔离演练说成另一台Mac实测。
## 已定决策
- scripts/lab/artifact_fetch.py使用现有SSH/rsync，不安装服务；manifest来自Git主线，远端alias/store由参数或任务专用环境变量指定。
- 每轮使用不存在的cache/dest，拒绝本地回填；下载只包含manifest所需SHA对象；从缓存完成artifact_store verify再restore，失败不得产生完成dest。
- receipt保存manifest SHA、原始传输argv/rc/stdout/stderr、verify/restore结果；不覆盖旧receipt；stdout只输出JSON，错误返回非零。
- 外环真实上传并远端全对象验证；新消费目录使用独立导出的工具/manifest，macOS sandbox拒读所有原workspaces与原本地CAS后从服务器恢复。负例删去远端测试集合一对象，即使本机有原件也必须失败；不删除正式对象。
- 所需运行集合以独立历史指纹required_members为准；缺少任何必需成员必须阻止完整范围声明，build引用按归档路径或missing逐项列明。
## 边界
### 允许修改
- scripts/lab/artifact_fetch.py
- scripts/lab/artifact_publish.py
- scripts/lab/tests/test_artifact_fetch.py
- scripts/lab/tests/test_artifact_publish.py
- tools/spec-checks/tests/artifact_remote_recovery.rs
- tools/spec-checks/tests/artifact_recovery_intake.rs
- benchmark/2026-10-26-demo-artifact-recovery/**
- knowledge/artifacts/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md
### 禁止
- 删除现存worktree或正式CAS对象、写设备、自动回填本机缓存、公开商业APK、改历史证据
## 验收标准
场景: 远端空缓存恢复
  测试: artifact_remote_recovery
  假设远端对象齐全且本地原worktree和原CAS禁止读取
  当下载到空cache并恢复新dest
  那么全部manifest对象hash匹配并保留实际SSH与传输收据
场景: 远端缺失不使用本机原件
  测试: artifact_remote_recovery
  假设远端测试集合缺一个对象而本机原件存在
  当执行获取
  那么退出非零且dest不存在且不从本地原件回填
场景: 原目录保护与非法参数
  测试: artifact_remote_recovery
  假设cache或dest或receipt已存在或remote含非法字符
  当执行获取
  那么退出非零且既有文件不变
场景: 未声明成员不能漏检
  测试: artifact_recovery_intake
  假设独立required_members含一个未被收集的运行依赖
  当核对manifest完整性
  那么差集非空并拒绝完整演示版恢复声明
## 排除范围
真正另一台Mac及整板重装实测、自动定期备份服务、全源码重编。
