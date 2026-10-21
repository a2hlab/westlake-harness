spec: task
name: "G33 connect locale candidate source and build to API table"
inherits: project
depends: [t30-locale-abi-candidate, t31-native-route-trial-api]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
将已入主线的G30实际源码、最小补丁、两次真实候选构建、函数回归和限制接入API全表，让新增locale兼容实现可查而不冒充真机成功。
## 已定决策
- 以主线e4cd7d753cffc850db374ad47cbd0f13dd07d92a的62条为逐对象不变前缀，仅追加63条。历史315、renderer不改，README只追加。
- 输入是主线8acf1ed61的locale-abi-candidate/final与源/patch/recipes，先核固定56路径已提交。基线d205精确复现，候选两次完整SHA4296f805相同，旧两对象逐字相同。仅3个LIBC导出：_ctype_的8字节OBJECT指针与257表，strtoll_l/strtoull_l转发并忽略locale；不包含__assert2。
- 对应真实host257分类/90整数用例、原native生产函数回归依赖替身、9个ABI守卫及独立ELF检查。44旧动态符号tuple、26旧导出、NEEDED和构造序列保持。候选02的55输入在构建前后相同且有持久副本；不称完整Linux OS闭合或OH实际语义验证。
- G28仍是白屏/退出且_ctype_实际终止；G30仅离线候选，尚未部署、不冻结、不满足2app，不称原神可玩。原失败host01(errno预期)和内环VM入口rc124均保留，不把环境失败称编译失败。原日志归档远端状态只按主线实际回执；没有回执则记录本地持久、远端待核。
- 原renderer生成HTML/CSV/results；G31 checker改严格62前缀允许追加并保留原失败语义，新checker精确63。逐引用SHA、renderer一致性、历史漂移/截断62/追加64/HTML-only假成功/缺引用/哈希漂移均验，不为新行放宽旧语义。
- 仅离线文档/数据/checker/Rust；固定path-only清单和原测试输出。5分钟首片，不设备/REA/运行时构建/G14/T38/push。
## 边界
### 允许修改
- benchmark/2026-10-19-api-progress-update/observations.json
- benchmark/2026-10-19-api-progress-update/observations.csv
- benchmark/2026-10-19-api-progress-update/index.html
- benchmark/2026-10-19-api-progress-update/results.json
- benchmark/2026-10-19-api-progress-update/README.md
- benchmark/2026-10-21-g28-api-observation/check_observation.py
- benchmark/2026-10-21-g28-api-observation/SHA256SUMS
- benchmark/2026-10-21-g30-api-observation/**
- tools/spec-checks/tests/commercial_game_g30_observation.rs
### 禁止
- 不改历史62对象/315、renderer、G30固定源和回执、运行时/门禁/主树，不设备、不push。
## 验收标准
场景: 第63条源码构建和未上板状态对应
  测试: commercial_game_g30_observation
  假设G30固定公开源码构建证据已提交主线
  当追加观测并用原renderer生成页面和表格
  那么所有引用SHA可核且输出一致，真实构建和host测试范围明确，保留未部署未冻结未成功与OS闭合限制
场景: 伪成功与历史漂移拒绝
  测试: commercial_game_g30_observation
  假设原62条不可变且G30没有真机结果
  当篡改历史或仅在HTML声称成功、增加64条、截断62条、丢引用或改哈希
  那么逐项拒绝且既有历史检查继续通过
## 排除范围
实际部署、头条修复、新兼容实现、原神成功和API冻结。
