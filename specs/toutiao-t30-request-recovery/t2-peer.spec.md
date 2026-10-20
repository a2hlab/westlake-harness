spec: task
name: "T30 real route independent recovery replay"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-recovery]
---
## 意图
复用原T29真实test_route驱动验证一次Q无资源失败是否造成永久拒绝；同一场景以后接作者实际派生源。
## 已定决策
- 只在外部Request seam注入第一次40601000与bufNULL/fd-1，第二次返回正常buffer；不重写pair/R14/R26业务方法。
- 原版必须实际观测首-5、次-16与一次Request；候选须首-5、次成功及一次unlock成功，原错误和ref/callcount持久保留。
## 边界
### 允许修改
- benchmark/2026-10-20-t30-recovery-peer/**
- specs/toutiao-t30-request-recovery/t2-peer.spec.md
### 禁止
- benchmark/2026-10-20-t29-window-observation/**
- knowledge/frozen/**
## 完成条件
场景: 原源码持续拒绝可复现
  测试: ttvideo_t30_request_recovery
  层级: integration
  替身: 只有外部JNI无关OH/provider/resolver/sink，业务为实际T29实现
  假设 原生产源码和真实路由fixture均逐SHA保存
  当 执行首次无资源失败及下一次正常请求
  那么 原版第二次-16且Request只调用一次，并保留owner refs和原始stdout/stderr/rc
场景: 候选缺失不能声称修复
  测试: ttvideo_t30_request_recovery
  假设 作者派生window_module尚未完成
  当 基线单场景完成
  那么 报告仅BASELINE_FAILURE_REPRODUCED_CANDIDATE_PENDING，不运行生产构建或设备、不把离线场景升级真机成功
## 排除范围
不改作者文件，不实现logger，不做宽泛测试或新增设备窗口；选择器由作者真实集成测试提供，本交件提供独立replay入口。
