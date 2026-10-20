spec: task
name: "Locate existing Genshin inputs and compare static evidence"
inherits: project
satisfies: [REQ-GENSHIN-STATIC]
tags: [genshin, offline, intake]
---

## 意图
定位现有原神APK、splits及资源，产出可追溯的静态输入清单和BoatAttack复用对照，供外环决定下一步；本任务不实现桥接或验证可玩性。

## 已定决策
- 先读现有WORKSPACES下westlake-inputs与仓内制品索引，再按索引指向的本地Westlake/00.Workspace/real-work/vm-copies路径核文件；不扫整个家目录、不联网找包。外部路径不可访问记录UNKNOWN，不以文件名断版本。
- 对用户已授权工作区现有输入只读分析，来源未知不阻塞普通静态读取：核完整SHA256/size、manifest package/versionCode/versionName/minSdk/targetSdk、签名可比信息、base/split关联、实际native ABI及assets/OBB索引；资源是否足够运行另为UNKNOWN，不能由存在文件推完整。
- 复用现成离线manifest/zip/ELF工具，不安装工具、不构建、不执行包代码。记录JNI声明/可见导出或注册线索、DT_NEEDED/动态加载线索、GLES/Vulkan/Unity及图形扩展证据；不可解析或加密项保留UNKNOWN，不作绕过或新REA。
- 复用specs/demo-baseline/t2b-boatattack.spec.md及其实际源码/构建/运行证据索引；逐项区分公共API可复用候选、BoatAttack特有补丁、版本/ABI/namespace差异、未证项。源码或旧PASS不能替代当前原神运行证据。
- 固定输出README.md、results.json、input-index.json、static-matrix.json、boatattack-comparison.json、source-index.json。results含status(LOCATED/PARTIAL/MISSING)、scope、elapsed、limits、unknowns、next_action；每个证据ref含alias/sha256/size，命令回执另含argv/rc/raw_refs。
- input-index逐文件记录role/base或split关系/来源记录（可UNKNOWN）/metadata/sha256/size；两个matrix逐项记录input_ref、观察、证据级别、可复用条件及unknown。没有输入时保留空数组和实际搜索范围，MISSING仅指该范围，next_action明确未搜索的OrbStack/hw248及其他范围，不推断全环境不存在；本轮无运行记录，runtime_verdict固定NOT_TESTED。

- 测试选择器genshin_static_intake_receipt是待实施车道补齐的最小Rust回执校验入口，当前尚不存在、未执行、不得报通过；只核六个输出及ref一致性，不造APK解析框架。最终证据质量仍由human审核，未签认保持pending_review。

## 边界
### 允许修改
- benchmark/2026-10-21-genshin-static-intake/**
- tools/spec-checks/tests/genshin_static_intake.rs（仅最小回执校验入口）
- 私有持久证据仅限$HOME/.local/share/westlake/genshin-static-intake-20261021/**，公开引用用该别名，不写个人绝对路径。
### 禁止
- 不改specs、requirements、源码、构建配方、API主表、冻结登记、历史证据及主树；所有输入只读。
- 不调用设备、下载、登录、安装工具、解密或绕过保护、不执行REA、不把分析继续扩成运行修复。

## 验收标准

场景: 已有授权输入形成精确静态清单
  测试: genshin_static_intake_receipt
  审核: human
  假设 用户已授权工作区有可读取的现有base APK及关联文件，来源可明确或UNKNOWN
  当 在15分钟边界内使用现成离线工具整理六个输出文件
  那么 每项版本ABI SDK JNI graphics观察都有精确输入SHA和原始命令回执，base splits assets关联及未确定资源完整性分开记录
  并且 BoatAttack对照列出实际源码构建运行证据与复用条件且runtime_verdict为NOT_TESTED

场景: 缺包或缺资源不冒充完成移植
  测试: genshin_static_intake_receipt
  审核: human
  假设 索引与允许路径内没有原神包或只有不完整split及资产
  当 有界定位结束
  那么 status为MISSING或PARTIAL并列实际本地搜索范围、缺项和未搜索范围的下一动作，不下载、不生成部署任务、不声明可玩

场景: 来源不明或静态工具失败保留未知
  测试: genshin_static_intake_receipt
  审核: human
  假设 文件来源不明或工具缺失超时或同包存在多个不一致版本
  当 整理结果
  那么 保留原始失败rc及所有已得证据，已授权输入来源不明仅记UNKNOWN且可继续普通只读分析，版本不混合且无法判断项为UNKNOWN而非PASS

场景: BoatAttack成功不替代原神动态证据
  测试: genshin_static_intake_receipt
  审核: human
  假设 仅观察到相似Unity JNI或图形符号并有BoatAttack旧成功记录
  当 给出下一动作
  那么 仅提出带输入SHA和差异的有限静态问题，不宣称原神实际provider绑定首致命点或动态播放通过，也不改设备及冻结状态

## 排除范围
- 原神启动登录联网游戏性能、安装资源补全、反作弊/授权绕过、运行时修复、API冻结、任何板上实验和t2实现。
