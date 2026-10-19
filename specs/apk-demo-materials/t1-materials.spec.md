spec: task
name: "APK slides and illustrated inventory"
inherits: project
tags: [presentation, historical-evidence]
---
## 意图
先交16页左右精选PPT，必须包含今日头条和BoatAttack的大标题、用途与真实运行截图。随后交分类PPT、覆盖128个基准键及两项专项演示的图文表和离线ZIP，满足用户急用展示材料。
## 已定决策
- 使用python-pptx生成16:9可编辑PPTX，优先复用2026-10-14实测截图；头条可用2026-10-19信息流图。
- 精选版首先交付；分类版与XLSX、CSV、HTML图文表共用带来源和状态的manifest，ZIP包含原图。
- 大字显示应用名和主要用途；用途与实测验证范围分别表述。115项启动证据与13项排除记录保留，头条和BoatAttack单独注明专项证据。
## 边界
### 允许修改
- benchmark/2026-10-19-apk-demo-materials/**
- specs/apk-demo-materials/**
- tools/spec-checks/tests/apk_demo_materials.rs
### 禁止
- 不操作设备、不修改运行时、不清理用户资料、不推送远程。
- 不伪造截图，不把闪屏、宿主页面或缺图判为功能可用。
## 完成条件
### Rule: portable-evidence — 可展示且可追溯
场景: 精选PPT提前交付
  测试: apk_demo_materials_receipt
  审核: human
  假设 存在今日头条信息流和BoatAttack实测截图
  当 生成精选PPTX并渲染检查
  那么 14至18页中包含这两个应用的独立展示页，标题和用途可读且图片不拉伸不裁切应用内容
场景: 分类与全量清单
  测试: apk_demo_materials_receipt
  审核: human
  假设 基准manifest含128键和排除状态且两个专项演示单独登记
  当 生成分类PPTX和图文XLSX及HTML后打包ZIP
  那么 表格逐键记录名称用途分类验证状态与截图，分类PPT包含头条和BoatAttack，ZIP解压后可离线打开图片与文件
场景: 缺图或异常状态不冒充成功
  测试: apk_demo_materials_receipt
  审核: human
  假设 某键被历史记录排除或缺少有效截图
  当 生成材料
  那么 该键保留真实排除或缺证状态并列出原因，不生成替代实测图片，不计入可演示项
场景: 引用丢失拒绝完整交付声明
  测试: apk_demo_materials_receipt
  审核: human
  假设 ZIP内引用图片缺失或PPTX损坏
  当 校验包和文档
  那么 报告缺失对象并修复后才声明完整包可用
## 排除范围
- 新一轮设备验证、随机崩溃修复、视频播放证明、远程发布。
