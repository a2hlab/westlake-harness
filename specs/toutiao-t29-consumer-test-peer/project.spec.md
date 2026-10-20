spec: project
name: "T29 independent consumer host fixture"
satisfies: [REQ-TTVIDEO]
---
## 意图
执行原SurfaceTexture/TextureView两TU真实方法，建立可对照CC派生源的行为证据。
## 约束
- 原两TU和CC目录只读。fake仅JNI/OH外部seam；不重写业务方法、不实现logger、不生产构建/HDC/部署/push。
- 原行为为对照，不将released attach或alias引用顺序等既有行为改成预期修复。新版缺件只能pending。
