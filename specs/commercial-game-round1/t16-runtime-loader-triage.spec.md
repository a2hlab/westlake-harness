spec: task
name: "G16 reconcile observed Genshin library load failure with providers"
inherits: project
depends: [t4-exact-static, t13-installer-device-window]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
根据normal-ui-01实际图标启动的首错链，将已有REA与BoatAttack实现映射到实际provider和namespace，缩小可验证修复范围，不重复上板盲试。
## 已定决策
- 精确APK仍为abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc。现场PID10029/UID20011077：__errno加载失败后继续，libyuanshen依赖libGLESv2在westlake.anl.app.10029.2失败，最后Unity JNI未绑定退出1；不把最后异常直接当根因。
- 先消费exact-static/rea-method-findings.json和rea-ledger.json中已成功的5方法、既有ELF扫描与BoatAttack公共实现；核原始Evidence SHA，不为重复统计重新反编译。
- 用源码和现有精确产物静态核namespace创建/搜索/继承/动态库映射，列出GLES和__errno的候选provider、源和构建链、部署同源是否已证。未见实际对象不能把源码候选当正在运行的实现。
- 若仅靠源码和符号仍不能判断具体二进制调用，Codex可用REA定点读取最小目标，保留原始Evidence与工具/产物SHA；未执行写NOT_EXECUTED及理由。不做整包反编译，不运行目标，不修改游戏保护机制。
- 交README.md/results.json/provider-matrix.json/evidence-index.json，包含预计移走的首个致命点key=genshin及因果确定程度；缺证写明最小所需对象。10分钟首片。此任务只静态取证，不产部署编排或G14/T38被拒步骤。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/runtime-loader-triage/**
- tools/spec-checks/tests/commercial_game_loader_triage.rs
### 禁止
- 不调用设备、不修改runtime/APK/冻结项、不重做G14/T38被拒内容、不push；不将日志或库名命中当API冻结或游戏运行成功。
## 验收标准
场景: 实际失败链与来源一致
  测试: commercial_game_loader_triage
  假设normal-ui-01保存真实启动日志
  当按时间和PID对照库加载与退出
  那么保留早期可恢复错误和最终致退异常区别，所有引用带精确路径行号SHA
场景: 已有REA和公共实现复用
  测试: commercial_game_loader_triage
  假设已有5方法REA及BoatAttack证据
  当核provider与namespace
  那么已执行和未执行明确，静态候选与实际加载明确，不搬app私有补丁或补无行为空桩
场景: 缺证不升级
  测试: commercial_game_loader_triage
  假设部署同源或搜索配置缺失
  当输出修复建议
  那么列出最小所需对象和unknown，不声称修复或游戏画面通过
## 排除范围
上板、修改游戏、登录下载、保护机制修改、头条部署编排和游戏可玩验收。
