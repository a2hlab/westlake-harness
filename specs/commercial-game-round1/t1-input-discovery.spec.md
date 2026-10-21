spec: task
name: "G01 locate exact commercial game inputs across existing stores"
inherits: project
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
补齐旧本地搜索的manifest和远端范围，定位原神base、splits及资产。交付精确输入或有边界的缺项，供后继静态扫描消费。
## 已定决策
- 复用旧genshin-static-intake记录，先解析现存APK索引中候选manifest而非重复全树搜索。记录本地/OrbStack/hw248/macserver每个实际搜索根、命令及结果；远端只用已有配置，不输出凭据。
- 搜索与首轮分析有界15分钟；无输入就交实际覆盖与下一动作，不继续等空任务。包名com.miHoYo.Yuanshen及国际版com.miHoYo.GenshinImpact都可记录，版本/签名/分包不同不得混合；优先既有国服输入。
- 找到后记录SHA256/size/manifest package/version/minSdk/targetSdk/ABI和资源索引；可从已有远端存储复制目标到持久私有目录并核两端SHA，记录空间；不拷贝整套用户数据。不能解析的项标UNKNOWN。
- 输出README.md、results.json、input-index.json、source-index.json。补最小Rust选择器commercial_game_intake_receipt转调实际输出校验；该选择器当前未实现，不能报通过。
## 边界
### 允许修改
- benchmark/2026-10-21-commercial-game/intake/**
- tools/spec-checks/tests/commercial_game_intake.rs
- 私有$HOME/.local/share/westlake/commercial-game-20261021/intake/**
### 禁止
- 不改运行时、旧证据、API表、主树或其他车道文件；不调用HDC/ADB、不安装、不下载新游戏、不登录、不执行包代码、不用REA。
## 验收标准
场景: 找到精确输入
  测试: commercial_game_intake_receipt
  审核: human
  假设 已有环境含可读取的原神包
  当 用现成离线工具读取真实文件及manifest
  那么 每个包及资产有输入SHA和来源别名，版本和split关系分别记录，runtime_verdict为NOT_TESTED
场景: 未找到或远端不可达
  测试: commercial_game_intake_receipt
  审核: human
  假设 部分范围无匹配或访问超时
  当 15分钟定位结束
  那么 区分MISSING与INACCESSIBLE及未搜索范围，保留失败回执并给明确next_action，不断言全环境不存在
场景: 改名包与分包不完整
  测试: commercial_game_intake_receipt
  审核: human
  假设 文件名不含原神或只有不同版本split
  当 检查manifest与签名关系
  那么 以真实包名识别并按版本分组，缺base或资源记PARTIAL且不生成安装命令
## 排除范围
上板、构建、运行修复、登录及可玩性验收。
