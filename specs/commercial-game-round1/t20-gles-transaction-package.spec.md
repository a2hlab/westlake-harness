spec: task
name: "G20 assemble current-baseline GLES transaction package"
inherits: project
depends: [t18-gles-loader-candidate, t19-loader-deployment-admission]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
把已经实际构建的G18候选与5ea当前基线对齐，生成既有U7事务工具可核验的输入包，直接推进受控上板。复用已验证的组装器，不重建运行时、不另写部署器。
## 已定决策
- G18已合入0dac7115db：baseline b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7，candidate 878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23。候选只改两别名的同一库，保留GLES名称外全部原行为。不得改游戏、errno、GLES实现或其他运行时行为。
- 依据G19既有u7_executor.py的Transaction.apply，真实baseline/hash/mount核对后新建journal，rollback按该journal恢复，不要求伪造历史owned state。保留原U13双别名同件同步发布和回滚规则，唯一动态调用赢家仍unknown但不作为新增前置。
- 先定位已存U13/Boat r4组合基线包，所有基线字节与当前5ea完整目标清单逐项对账；已有只读runtime124/boot36指纹仅其覆盖范围，不宣称全量321。使用outer-readonly-01挂载快照及outer-fingerprint-01；缺少的目标列出精确只读清单，由外环补取。不会以旧boot快照代替本次板身份。
- 复用现有组装与静态门禁，实际运行u7_executor.py --dry-run及需要的原namespace/frozen/native-checks门禁，记录argv/rc/原始stdout/stderr到持久目录。旧boot/JAR/source全部复用无重编；U7若覆盖同SHA成员，必须分别列逻辑变化两别名与实际计划写入项，不称仅两个写操作。
- 不修改既有门禁与允许范围，不代签outer(codex)。缺签名、实验回执或基线输入时输出具体阻塞和待绑定字段，不虚报dry-run通过。输入包与公开配方/来源/SHA/回滚绑定可重建，二进制保存在持久私有目录；最终提交landing-paths。
- 五分钟首片交基线包位置及实际差异/缺项；与G19正在收口的报告重叠部分直接引用，避免重复扫描。此卡只准备包和离线预检，不取得板锁、不写设备。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/gles-transaction-package/**
- tools/spec-checks/tests/commercial_game_gles_transaction_package.rs
- 私有当前卡目录下.private/**
### 禁止
- 不修改现有部署器/冻结登记/旧源码包；不生成首启自动编排或重做G14/T38被拒步骤；不设备写、不读取environ、不hook/注入、不推送。
## 验收标准
场景: 精确基线与双别名候选
  测试: commercial_game_gles_transaction_package
  假设G19指出既有U7入口和可用基线来源
  当组装包并比较完整目标表
  那么逻辑变化仅两个libnativeloader别名且SHA同878c，所有其余目标和原始行为保持基线，配方与输入可追溯
场景: 实际离线门禁及恢复绑定
  测试: commercial_game_gles_transaction_package
  假设现有工具和完整包可核
  当运行原u7_executor.py --dry-run及静态门禁
  那么保留实际结果与恢复输入SHA，列出真实写入项，无板写且不把dry-run当游戏成功
场景: 缺输入或漂移拒绝
  测试: commercial_game_gles_transaction_package
  假设任一当前目标未观测、输入哈希漂移或缺真实签认
  当计算准入
  那么明确缺项并保持未准入，不伪造owned state或签名、不放宽门禁，不声称原神加载或游戏画面通过
## 排除范围
实际部署、实际启动、头条部署、资源下载、图形重写、游戏可玩与通用工具重构。
