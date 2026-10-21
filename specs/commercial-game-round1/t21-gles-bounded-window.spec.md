spec: task
name: "G21 bounded paired-loader observation on 5ea"
inherits: project
depends: [t20-gles-transaction-package]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
使用原有 U7 事务把 G18 两别名 GLES 可见性修复放到 5ea，观察原神普通桌面入口是否越过已实证的装载失败。保留完整原始执行记录，在同一窗口恢复当前基线；本次实验不签永久封板，也不承诺游戏可玩。
## 已定决策
- 仅 5ea34a4500000000000000001123012c；61b、5cd 和头条 T38 不动。复用原 scripts/lab/u7_executor.py 的 apply/rollback，不写新的部署器、首启 wrapper 或被拒的 G14/T38 编排。
- 基线采用 G20 assembly-02 的 319 目标及另列三件 Boat 私有库；本次逻辑变化仅两个 libnativeloader 别名 b8be63d2→878c7019。原 U7 实际绑定 32 件，其中 30 件 SHA 不变。所有游戏代码、数据、权限和保护行为保持原样。
- 外环逐项审签当前 package/inputs 的 N1/N2 有界例外，保留未解析 namespace/初始化闭包限制，不沿用历史 N10b/U10.1 窗口签名。只在独立新包将 rollout_ready 设为 true；旧 assembly-01/02 不改。原全套 preflight 必须通过，build receipt 有效且 deployable 为 true。
- 写前只读重核串号、boot、锁、进程、挂载、完整基线和供回滚的包；持锁后重核。使用原 OrbStack a2hlab 执行入口，工具和门禁不修改。若原工具拒绝当前父进程形态，保留拒绝，不放宽守卫。
- 窗口从取得板锁开始不超过 1800 秒；1200 秒前开始恢复。原事务 journal 记录实际操作，并由其回滚，不造历史 owned state。临时电源保活保存并精确恢复；不依赖重启恢复。
- 候选生效后只用已有普通桌面 UI 操作点击原神图标，保存真实截图、boot/PID/birth 和本次完整选定日志。不上账号、不下载游戏资源、不 hook/注入、不读 environ。出现登录或资源下载页时只记录页面。
- 结果按首个实际致命点与截图判定：原 GLES 可见性错误消失仅算越过这堵墙；白/黑屏、进程存活和 JNI 日志不算游戏画面通过。无新证据则写 unknown，保留失败输出。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/gles-bounded-window/**
- benchmark/2026-10-21-commercial-game/gles-outer-native-admission/**
- knowledge/gates/native-predeploy-exceptions.json
- 私有持久证据目录和独立新 rollout 包
### 禁止
- 不改运行时源码、原门禁/部署器、游戏 APK 或冻结行为；不重试已被拒的 G14/T38 操作，不跨板。
## 验收标准
场景: 精确准入后使用原事务
  测试: u7_executor
  审核: human
  假设当前包与实际基线一致且原全套门禁通过
  当在 5ea 持锁执行原事务
  那么以原始 journal 和完整 SHA 证明两别名生效且其余目标保持基线，原 U7 单测只证明状态机行为不替代设备证据
场景: 身份漂移或门禁失败拒绝
  测试: u7_executor
  假设 boot、串号、基线、包、输入或门禁任一不匹配
  当原事务核验准入
  那么拒绝继续写入并保存原始错误，已发生写入按原 journal 恢复，不绕开拒绝
场景: 普通图标观察与同窗恢复
  测试: u7_executor
  审核: human
  假设候选事务已生效且窗口未到恢复时限
  当执行一次普通图标启动并采集截图与日志后回滚
  那么分别记录装载墙结果和真实页面，核对完整基线、原挂载、三件 Boat 私有库及电源恢复后解锁，不把单测或离线门禁当运行成功
## 排除范围
头条修复、永久部署、游戏资源下载和登录、反作弊或授权绕过、其他公共 API 修复、跨板验证。
