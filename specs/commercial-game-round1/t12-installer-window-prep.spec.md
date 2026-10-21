spec: task
name: "G12 prepare one-library install and startup window"
inherits: project
depends: [t6-first-launch, t9-extractor-build]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
在G09构建期间准备5ea安装器单库修复的部署、安装验证和失败恢复入口，避免产物出来后再串行找操作方法。本卡只生成离线可审计划，不使用设备，不把占位候选SHA当准入。
## 已定决策
- 复用G06真实first-launch/execution与恢复hook、installation_chain.py及仓内已验证libinstalls替换记录，按本地索引查，不另造整代部署；必须列来源路径/commit和未验证假设。
- 唯一目标5ea34a4500000000000000001123012c；已知原件51e1b525、进程实际maps在/system/lib64/libinstalls.z.so，fingerprint也有platformsdk同名件。具体inode/链接关系/服务身份必须未来fresh核；不凭同名或旧PID部署，不动61b/5cd。
- 候选必须G09真实baseline等价及candidate编译链接rc0、输入APK精确abd3c4d5、源4068fdba、工具链和原始日志完整。SHA待定字段使计划拒绝执行；部署前重新核冻结与单板锁、备份、恢复方法及30分钟预算。
- 计划覆盖只读fresh→实际加载对象与路径→原件持久备份→最小部署/服务重新加载→加载SHA核验→对照app与原神安装启动→实际截图facts→失败回滚原SHA及设置→释放锁。服务重启方法从已验证记录取，不猜命令，不终止未知进程。
- 只读板状态不可用也不阻塞离线准备；把缺证写入fresh-required字段，不造完成回执。非零安装body即失败，不能只看hdc rc0；保留first fatal及截图为0情况。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/apk-extractor/window-prep/**
- tools/spec-checks/tests/commercial_game_installer_window_prep.rs
### 禁止
- 不访问设备、不部署、不构建、不重启、不修改G09或旧运行目录、不改APK或用户数据、不push。
## 验收标准
场景: 真实执行链可追溯
  测试: commercial_game_installer_window_prep
  假设仓内存在G06安装和恢复记录
  当生成单库短窗方案及argv模板
  那么操作对应已验证来源、精确板和文件，加载SHA/安装body/facts都在验收范围
场景: 候选或fresh身份缺失拒绝
  测试: commercial_game_installer_window_prep
  假设候选SHA或进程身份或路径关系未知
  当检查执行准入
  那么拒绝执行并列具体缺项，不以旧身份或占位值通过
场景: 失败恢复证据要求
  测试: commercial_game_installer_window_prep
  假设部署或安装或启动失败
  当评估恢复路径
  那么原件与加载对象及配置需逐项复核，缺恢复证据不能释放为成功，不修改61b和5cd
## 排除范围
实际签认、部署和游戏可玩验收另由外环审核候选与fresh后执行。
