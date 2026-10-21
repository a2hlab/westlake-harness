spec: task
name: "G04 exact Genshin startup, graphics and audio static triage"
inherits: project
depends: [t2-reuse-static, t3-official-input]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
对已取得的精确原神安装包扫描首启动链、native依赖和图形音频入口，以BoatAttack及头条已有实现为对照，交可用于最小上板的阻塞预测而非兼容承诺。
## 已定决策
- 输入APK SHA256 abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc，513290344字节，私有official-input/apk/yuanshen_7.1.0.apk；先重新校验，并引用G03真实manifest/签名原件。G03未验签成功不做安装准入结论。
- 首片20分钟：manifest Application/launcher/required features、DEX loadLibrary与native绑定、各ABI ELF/DT_NEEDED/导入、Unity/IL2CPP身份、图形Surface/EGL/Vulkan和音频AudioTrack/OpenSLES/AAudio路径。引用不是执行；间接/动态代码未知单列，不推断首个运行致命点。
- 先用现有扫描器和LLVM；REA仅Codex/octoscode可用。对具体启动或音频疑点选最小类/函数分析，保留原始完整Evidence/工具版本/对象SHA；不全量反编译巨型库。已知音频REA证据直接复用，无必要不得重复。
- 列出映射：目标需求→当前候选provider/namespace→既有源码/构建/验证证据→缺口。signal shim保留ART handler策略与仅guest namespace限制、Boat私有C7/C4不得直接搬；头条AudioTrack有声不代表原神音频可用。
- 输出README.md、results.json、startup-matrix.json、reuse-map.json、rea-ledger.json与小证据；工具源码和原始执行回执持久化。Rust选择器commercial_game_exact_static_receipt验证身份及报告，不把测试通过当上板或可玩。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/exact-static/**
- tools/spec-checks/tests/commercial_game_exact_static.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/exact-static/**
### 禁止
- 不调用设备、不运行APK、不下载游戏资源、不登录、不改游戏/运行时/冻结项、不push、不提交APK或反编译整包；只交范围内代码和小报告。
## 验收标准
场景: 精确目标消费
  测试: commercial_game_exact_static_receipt
  审核: human
  假设 输入SHA及签名原件可核
  当 读取真实manifest和ELF依赖
  那么 所有分析绑定该输入，入口与provider映射注明观测或推断，运行结果NOT_TESTED
场景: 二进制疑点需REA
  测试: commercial_game_exact_static_receipt
  审核: human
  假设 源码和普通静态工具无法确定一个具体启动或音频调用路径
  当 用REA分析最小目标
  那么 保留完整原始Evidence和地址基准；不可用时记录错误及未知，不以摘要冒充工具执行
场景: 已验经验有条件复用
  测试: commercial_game_exact_static_receipt
  审核: human
  假设 BoatAttack图形输入及头条音频实现已有证据
  当 对照原神实际引用和provider
  那么 区分公共机制与app私补，未绑定音频后端或namespace时不能声明通用可用
## 排除范围
动态执行、保护机制修改、游戏资源下载和设备封板。
