spec: task
name: "M3 versus M1 GL surface hypothesis"
inherits: project
---

## 意图

Test whether the three signed white GLSurfaceView apps lose their child window through M1's last-session slot, or fail later at EGL JNI conversion.

## 已定决策

- Compare the three white keys with lit shadereditor and the multi-session noice M1 control.
- Preserve session, child producer, TID, JNI registration and EGL pointer timelines.
- A RTLD_DEFAULT lookup inference is not an observed dlsym return value.

## 边界

### 允许修改
- benchmark/2026-10-02-white-m3-glsurfaceview/**
- tools/spec-checks/tests/white_m3_glsurfaceview.rs

## 验收标准

场景: Single-session GL failure is separated from last-session overwrite
  测试: white_m3_glsurfaceview
  假设 Three signed white app runs and two controls with pinned raw evidence
  当 App-PID session and EGL-thread timelines are inspected
  那么 Each white key has one successful session and nonnull dedicated child before the IAE, while the M1 control has two publications and an empty older-session surface

场景: The native proposal cannot be mistaken for a proven three-key unlock
  测试: white_m3_glsurfaceview
  假设 The deployed EGLImpl uses a cached RTLD_DEFAULT lookup
  当 Missing instrumentation and the lit GL-error control are evaluated
  那么 The scope hypothesis, conditional three-key exception movement and zero measured unlocks remain distinct

## 排除范围

- Runtime patches, new native candidates, device windows and changes to the M1 owner file.
