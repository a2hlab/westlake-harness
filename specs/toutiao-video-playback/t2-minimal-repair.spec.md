spec: task
name: "Toutiao video first-blocker minimal repair"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-static-evidence]
tags: [media, waiting-for-evidence]
---
## 意图
仅在t1把当前首阻断API归属到精确消费者与提供方后，制作独立可回滚候选；优先移植已验证实现，保持已封板的主窗口和图标路径。当前未选定具体API，不能先重写媒体栈。
## 已定决策
- t1的selected-change.json必须绑定input SHA、源码blob、允许文件列表、预计移走首致命点的key与已验证来源；外环确认后才开建，unknown或external_blocked禁止开建。
- 只在candidate下复制并修改获准的源码单元，不改冻结原件；需要不同文件时先修订契约再lint。
- 保留相同namespace/ABI与未改行为；构建前check_frozen、逐部署件strings/class/open-site对照、工具链哈希和原始stdout/stderr及rc=0都入回执。
- 功能检查按真实修复API增加正例、拒绝例和释放/生命周期测试；不以返回OK、空数据或注册成功代替视频解码/呈现。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/candidate/**
- specs/toutiao-video-playback/t2-minimal-repair.spec.md
### 禁止
- 不上板、不改冻结文件、不改主窗口几何、图标watchdog、启动器或应用数据；不替换完整运行时世代。
## 完成条件

### Rule: evidence-before-verdict — 先绑定证据再判断
场景: 绑定首阻断的可复现候选
  测试: ttvideo_build_receipt
  审核: human
  假设 t1已审查确认且selected-change列出精确允许源码
  当 在candidate目录仅改获准源码、运行check_frozen与namespace扫描后重建并执行API正反例及释放生命周期测试
  那么 记录输入输出SHA、工具链、原始stdout/stderr成功日志、源码差异及未改ABI，产出单变量部署和回滚输入
场景: 未绑定或漂移输入拒绝
  测试: ttvideo_build_receipt
  审核: human
  假设 首致命点unknown或输入SHA与selected-change不同
  当 请求构建
  那么 拒绝发布候选且保留失败回执
场景: 行为桩不冒充修复
  测试: ttvideo_build_receipt
  审核: human
  假设 实现只返回OK或仅有JNI注册且无帧输出
  当 审查行为与差异
  那么 拒绝认定播放修复且不进入成功封板
## 排除范围
- 随机崩溃根因、安全机制改造、用户数据清理和自动远程推送。
