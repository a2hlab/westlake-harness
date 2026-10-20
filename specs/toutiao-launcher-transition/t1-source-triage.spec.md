spec: task
name: "Toutiao host transition source triage"
satisfies: [REQ-TTVIDEO]
---
## 意图
在已留板视频候选不变的前提下，用现有源和历史原件说明正常图标为何先显示开发宿主页，再显示头条；交可回退的最小源码修订建议，不把替换启动页称为加速。
## 已定决策
- 本阶段只读MAIN、既有VM源码副本和activation原件；只新增本任务证据和契约。保留T31与实际留板签认，不新增设备窗口。
- [platform-specific] OH EntryAbility页面、前景窗口门、parent/child启动、真实feed截图分别绑定file:line及SHA；历史源码符合截图不等于已装HAP可逐字复现。
- 既有空黑页面只作为复用候选；HAP签名/UID/资源/SDK与旧HAP回滚来源未闭合则不得称可部署。WID和WL_PARENT_ID变化必须列为视频窗口归属风险。
- 人工截图是可见性证据；稀疏截图仅给采样区间，禁止把首次采得feed时间当精确首帧、把READY当feed或隐藏宿主页当启动加速。
## 边界
### 允许修改
- specs/toutiao-launcher-transition/t1-source-triage.spec.md
- benchmark/2026-10-20-t31-launcher-triage/**
- tools/spec-checks/tests/toutiao_launcher_source.rs（仅声明只读Python检查选择器，本轮不编译Rust）
### 禁止
- 禁止HDC、设备命令、构建、部署、推送、修改旧源码/冻结记录；不实现新的启动器或绕过前景身份门。
## 完成条件
场景: 页面内容与启动链分离
  测试: t31_launcher_source_review
  审核: human
  假设 旧宿主页面和后续空黑页面源码可读
  当 对照实际host截图与控制脚本SHA
  那么 明确页面绘制和Android启动的不同责任及精确来源，不伪造已装HAP源码等价
场景: 时序证据不扩大
  测试: t31_launcher_source_review
  审核: human
  假设 实际点击记录和host及feed采样时间可读
  当 计算相对时间并核原图
  那么 只陈述采样时可见状态，缺首帧事件保持unknown，不把等待区间全归因guardian
场景: 最小修订与恢复范围
  测试: t31_launcher_source_review
  审核: human
  假设 后续宿主源码已去除开发控件但未验证在本留板版本更新
  当 交修订位置及回退建议
  那么 保持EntryAbility身份/生命周期/前景门，列旧签名HAP与WID恢复先决，视频不回归仍待独立验证
## 排除范围
本轮实现/编译/设备验证、启动耗时优化、随机退出调查、视频候选重新验收及公共API冻结变更。
