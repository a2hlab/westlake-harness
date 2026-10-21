spec: task
name: "G03 obtain official Genshin install inputs and exact static identity"
inherits: project
depends: [t1-input-discovery]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
既有输入未命中、macserver不可达后，从原神官方公开入口取得安装包，解除精确静态分析的输入阻塞。
## 已定决策
- 官方起点https://ys.mihoyo.com/，沿实际页面链接/公开资源定位Android下载，不猜CDN版本URL、不使用第三方重包、不修macserver。外环已有网页原件可复用。
- 有界15分钟首片：优先官方base/安装分包，先看大小和本地空间，最多下载2GiB安装输入；完整游戏资源、账号、付费均不在本卡范围。下载不到保留确切URL/错误，不宣称包已取得。
- 实际执行时保存argv/rc/stdout/stderr、下载响应头/最终URL；APK进持久私有目录、不进git。校验ZIP、SHA256、aapt2 manifest、apksigner签名，逐包版本/ABI/split依赖，分安装集与后下载内容。不执行APK。
- 用已有工具，不造下载框架；小记录器/解析脚本入本卡tools并记录SHA。输出README.md、results.json、input-index.json及下载来源链。Rust选择器commercial_game_official_input_receipt验证公开回执及本地输入身份，未实现不得称通过。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/official-input/**
- tools/spec-checks/tests/commercial_game_official_input.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/official-input/**
### 禁止
- 不写主树、不push、不设备调用、不装包、不登录、不REA、不改运行时或既有证据；不提交APK、资产或网页整包。
## 验收标准
场景: 官方安装输入取得
  测试: commercial_game_official_input_receipt
  审核: human
  假设 官方入口提供公开Android安装包
  当 在限额内下载并读取真实包和签名
  那么 来源链、最终URL、SHA、大小、manifest和签名原件齐备且runtime为NOT_TESTED
场景: 下载受阻或超出限额
  测试: commercial_game_official_input_receipt
  审核: human
  假设 来源不可达或安装输入超过2GiB
  当 取得实际响应或失败
  那么 记录未取得原因和已下载部分，禁止假填版本与可安装结论
场景: 资源阶段分离
  测试: commercial_game_official_input_receipt
  审核: human
  假设 安装包已到但后下载内容缺失
  当 记录安装集依赖
  那么 明确安装必需缺项及后下载UNKNOWN，后下载内容不冒充已取得
## 排除范围
完整游戏资源、登录、运行兼容修复、上板和可玩性验收。
