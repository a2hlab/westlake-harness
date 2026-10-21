spec: task
name: "G32 prepare existing transaction for locale ABI candidate"
inherits: project
depends: [t30-locale-abi-candidate, t28-native-route-window]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
与G30候选构建并行准备下一次原神原U7离线输入，复用G28的完整source/owner绑定，避免候选完成后重新找清单。此卡不执行设备操作。
## 已定决策
- 先只读审查G28已提交主线78ea9794196的admission/public-v2与原持久assembly，复用G27已验证组装器。基线仍为G28实际恢复的319项及Boat3，旧例外已撤销，不继承旧窗口签字。
- 候选拟保持G26 host/ANL及G24 policy，只替换已有native ABI中的G30三项locale实现。先枚举实际manifest中的所有ABI别名、消费者、源profile和真实写入成员；不猜目标数，不新增搜索根、namespace或GLOBAL操作。
- G30基线已在外环g30-outer-baseline-01精确重建d205。候选尚未固定时仅准备输入表和组装入口，显式pending；只有外环给出G30固定清单、实际编译回执、ELF SHA及复验采认后才消费候选。缺失或同库别名漂移必须拒绝。
- 源绑定不能退回G27旧profile错误。逐项引用当前源、产物、构建原件及精确hash，保留G28原先未签门禁失败与所有历史件。没有完整闭合的输入明示缺口，不伪造来源。
- 复用原静态/native/frozen门禁，不修改门禁、全局exceptions或签字。默认rollout_ready=false；生成新的unsigned finding表，按当前inputs重新核，不沿用318条计数或上窗签认。Linux入口需要外环执行时交固定argv与SHA，不与外环竞争执行。
- 5分钟首片交真实ABI别名/消费者/源profile表及待补列表。代码和小证据保存在本卡独立目录，原始日志与大制品留持久私有目录；交path-only固定清单、实际测试输出和英文README。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/locale-transaction-package/**
- tools/spec-checks/tests/commercial_game_locale_transaction_package.rs
- 私有持久locale-transaction-package目录
### 禁止
- 不设备、不首启、不修改运行时源码/历史包/共享主树/冻结登记/例外表/部署器，不重试G14/T38，不push。
## 验收标准
场景: 当前产物与完整恢复输入对应
  测试: commercial_game_locale_transaction_package
  假设G28恢复证据和G30固定构建均可核
  当按原组装器形成新独立输入
  那么实际所有别名和消费者有精确SHA与source profile，319基线与Boat3恢复输入不变，真实写入数来自清单
场景: 未固定候选与漂移拒绝
  测试: commercial_game_locale_transaction_package
  假设候选尚未采认或同库别名与源输入发生漂移
  当生成或验收包
  那么明确pending或拒绝，不用旧件或半写文件代替，不声称可部署
场景: 当轮门禁与设备状态区分
  测试: commercial_game_locale_transaction_package
  假设离线包完成但没有当轮签认或fresh设备身份
  当运行原门禁并交件
  那么保存真实rc及完整原始输出并保持unsigned和rollout_ready=false，不继承旧签字或宣称游戏成功
## 排除范围
设备窗口、游戏保护或资源修改、新ABI实现、头条部署、永久保留候选。
