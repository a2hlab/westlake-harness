spec: task
name: "核验部署身份并本机编译"
inherits: project
---

## 意图

核验 libapp_native_loader 的部署 SHA、源码、工具链和 sysroot。在本机容器原样编译，并核对命名空间公开库表的真实实现位置。

## 已定决策

- 使用 U13 指纹的 exact SHA 选择原件；源码和构建命令来自已有 n3-native 配方。
- 若命名空间表不属于 loader，报告前提错误并编译真实所有者的最小表修改，不伪造 loader 修复。

## 边界

### 允许修改
- benchmark/2026-10-09-local-build-check/**
- specs/local-build-check/**
- tools/spec-checks/tests/local_build_check.rs

## 验收标准

场景: 原样构建证据绑定部署件
  测试: local_build_identity
  假设 U13 指纹包含 loader 的 exact SHA
  当 本机容器执行原配方且保存原始日志
  那么 results 记录输入输出 SHA 日志 SHA 退出码和逐节比较结论

场景: 修改位置错误时报告真实所有者
  测试: local_build_owner
  假设 loader 通过回调委托命名空间创建
  当 静态核验回调绑定和 dlns_inherit 实现
  那么 报告指出宿主所有权且最小修改只追加公开库表并记录 ABI 比较

## 排除范围

- 板上行为验证和生产部署；修改 loader 回调 ABI。
