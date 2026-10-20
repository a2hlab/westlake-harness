spec: task
name: "Exact installed host closure and minimal page candidate"
inherits: project
depends: [t1-source-triage]
satisfies: [REQ-TTVIDEO]
---
## 意图
按用户新授权完成当前df385638 HAP到ABC/资源/源码/公开开发签名/精确回退件的静态闭合，再以只去开发控件的独立页面候选交root复验，不重开视频修复。
## 已定决策
- [platform-specific] root intake installed-entry.hap必须为df3856387ba6971202b33e4475fde4e0fb1bf7fb33da0f4250429fe6535b014a、53303B、UID20011300/versionCode2/API20。历史5cd-host-install及out-toutiao-host对应真实9members逐SHA比，generic build_apps不算同源证明。
- 用历史JS与已存在SDK实际重编两ABC，必须匹配bb1eccd3338dde573393b24d81e26e67450d5461ba51f73e578d9e42a78cbde9及0755d5df3a17d33f1c94576d2cc326286c6ac03c4d7a63f662cc1ce14d8267c1；不匹配即保留失败并定位编译器/路径差异，不冒称复现。
- 最小候选仅删除Index页面开发标题和TextInput。保留原背景、Column布局、bundle/ability、EntryAbility ABC、module、资源、权限、versionCode和其余成员；唯一程序变化为Index.abc。签名工具生成.pages.info是单列metadata例外，不得借此放宽任意成员。
- 原HAP完整保留为rollback；核原公开开发证书/profile来源及候选签名验证，签名不等于允许上板。禁止新申请权限/提升APL或替换未知证书。
- 本轮显式授权离线实施和构建，不继承t1诊断阶段对本任务的代码禁止；t1原件不改。一次图标到feed复用既有guardian，无法消除等待就如实说明。
## 边界
### 允许修改
- benchmark/2026-10-20-toutiao-launcher-page/**
- tools/spec-checks/tests/toutiao_launcher_page.rs
### 禁止
- 改旧源/留板6态/foreground门；签部署留板结论；HDC、安装、重启、清数据、推送。
## 完成条件
场景: 安装件与历史9成员精确闭合
  测试: launcher_page_closure
  假设 root只读intake和历史回退HAP均可读
  当 比较完整HAP和9member以及历史产物清单
  那么 全SHA相同、记录真实来源和工具pin，缺失或漂移拒绝构建发布
场景: 两ABC源码实际复现及最小候选
  测试: launcher_page_closure
  假设 精确历史JS与SDK已锁定
  当 本地重编基线再编新Index并重新打包
  那么 基线2ABC精确相等且候选只有Index.abc程序变化，其余资源/EntryAbility不变，不把空页当加速
场景: 签名和回退闭合
  测试: launcher_page_closure
  假设 公开签名材料与原profile可验证
  当 原签名工具签署并验证候选及原HAP
  那么 身份/证书/profile权限不漂移，旧完整HAP可回退，新原始argv/stdout/stderr/rc持久化，签名失败不得发布
场景: 漂移拒绝和未知运行边界
  测试: launcher_page_negative
  假设 HAP或ABC或资源或工具SHA漂移或缺少真实构建回执
  当 请求候选准入
  那么 非零拒绝且失败原件保留，无设备动作、不弱化身份门
场景: root后续验证卡
  测试: launcher_page_closure
  审核: human
  假设 离线候选与精确旧HAP已齐
  当 审阅一次图标/宿主窗口/真实feed及原视频保留与回退步骤
  那么 fresh WID与parent环境须一致，未开窗不能称验收通过；WID非29需另审既有恢复范围且不伪造速度改善
## 排除范围
直接跳过宿主、性能承诺、改变音频接受口径、视频runtime重建、其他app及本轮设备操作。
