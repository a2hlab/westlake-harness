spec: task
name: "G19 qualify existing paired loader deployment and restoration"
inherits: project
depends: [t18-gles-loader-candidate]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
为G18公共loader候选找到当前5ea可直接复用的部署及恢复入口，消除构建完成后等待上板的空档。交付实际工具、实际状态回执与双别名的对照，不新造通用部署系统。
## 已定决策
- 基线libnativeloader为b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7；G18候选为878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23。实际child10946同时映射system与route74d1两份不同inode的同SHA库，不能断言唯一调用赢家。
- 优先复用scripts/lab/deploy_generation.py及既有U13双别名发布/回滚实现；先检查它是否适配当前boot和原生包状态，不伪造owned state，不沿用旧boot回执，不修改门禁。只读核现有本地状态、包清单、当前板的boot/mountinfo/SHA/进程；不读environ。
- 对照system路径/system/android/lib64/libnativeloader.so和route路径/system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac/libnativeloader.so，核sealed manifest、库哈希消费者及父进程复用影响，保留原始依赖和单份ART要求。若现有工具不能安全完成双别名一致切换，具体指出代码位置及最小缺口，不生成假准入。
- 交付静态admission.json、带file:line的英文README、原始只读执行回执、landing-paths。前5分钟先报可复用入口或实际缺口；不扩展新构建、不下载、不生成自动首启或T38部署编排。
- 这张卡不进行设备写入；后续窗口由外环根据实际准入再绑定锁、30分钟上限、20分钟开始恢复、原电源值和signed rollback。批准人只能实际外环outer(codex)签，不提前代签。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/loader-deployment-admission/**
- tools/spec-checks/tests/commercial_game_loader_deployment_admission.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/loader-deployment-admission/**
### 禁止
- 不修改设备、G18候选、冻结登记、现有部署器及其他树；不重做G14/T38被拒步骤，不hook/注入/二进制补丁，不推送。
## 验收标准
场景: 双别名与原生状态可复用
  测试: commercial_game_loader_deployment_admission
  假设G18候选和现有U13双别名方案可核
  当检查实际包与工具
  那么每个目标均有原件SHA、候选SHA、真实切换及恢复入口、父进程影响和证据引用，且未执行写入
场景: 旧状态或单别名缺失拒绝
  测试: commercial_game_loader_deployment_admission
  假设回执boot不匹配或任一别名恢复证据缺失
  当计算准入
  那么不得报ready，逐项列缺口，不伪造state或退化为只改一处
场景: 哈希消费者或动态归属仍未知
  测试: commercial_game_loader_deployment_admission
  假设精确源码与ELF不足以证明当前消费者接受候选
  当生成报告
  那么保留unknown与所缺证据，禁止以host单测或同SHA推定实际游戏加载成功
## 排除范围
实际部署、图标启动编排、头条任务、修改游戏、资源下载及游戏可玩验收。
