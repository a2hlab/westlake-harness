spec: task
name: "T29 actual dual artifact data freeze"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-data]
---
## 意图
将实际联合生产的bridge和shim及新owner偏移绑定到既有六件交易，减少上线准备等待。
## 已定决策
- 保留pending原件；executor逐字693448，四件固定参数不变，未知runtime winner仍unknown。
- 仅以实际两ELF、原始22条命令回执、公开构建引用、owner/JNI/ABI与独审回执回填数据；fresh身份与授权保持null。
## 边界
### 允许修改
- benchmark/2026-10-20-t29-deployment/**
- specs/toutiao-t29-deployment/**
- tools/spec-checks/tests/toutiao_t29_deployment.rs
### 禁止
- benchmark/2026-10-20-t28-shim-deployment/**
- knowledge/frozen/**
## 完成条件
场景: 双产物真实对应
  测试: ttvideo_t29_deployment_final
  假设 真实联合生产两ELF及公开回执存在
  当 校验SHA与bytes以及新owner和shim导出偏移
  那么 数据与公开引用逐项一致，四件固定参数及executor原字节不变
场景: 未签模板保持拒绝
  测试: ttvideo_t29_deployment_final
  层级: integration
  替身: 仅本地公开回执视图；原executor真实入口，Board不可用
  假设 final候选参数完整但实际身份与授权为空
  当 执行三mode preview和三mode execute sentinel
  那么 preview零device且execute在Board导入前拒绝，不伪造实际slot结果
场景: 关键数据漂移拒绝
  测试: ttvideo_t29_deployment_final
  假设 任一ELF SHA或导出偏移或owner绑定或fresh授权被漂移
  当 调用真实final校验函数
  那么 每项反例拒绝且pending原件仍可原样核对
## 排除范围
不构建、不上板、不改原交易、不补签身份、不改旧生产回执语义。
