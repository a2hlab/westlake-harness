spec: task
name: "N2 合并 N1 实测剩余 native 簇"
inherits: project
tags: [native, n2, cx-t0]
---

## 意图

以已采认 N1 aa57845c 为底，合并 Flutter 域可见性与 property、JNA errno、SPD GLImpl、Camera JNI、VLC abort-message 修复。先找 Westlake 验证实现再移植，记录未实现与设备未验项；收到 cc-wiki 的 Skia 真头文件产物后核输入再并入。

## 已定决策

- 不修改 N1 包；N2 新目录、完整 SHA 清单、可回滚。
- 保持 FZ-001/002 与 FZ-003 源字节一致；新增功能另源文件。
- ELF 文件闭包不足以证明 namespace 可见，测试必须覆盖真实 search/permitted/load 路径与直接 owner 继承。
- JNI 签名从现役 DEX 与同源源码核对；无硬件能力不假报成功。
- 合成一版后交外环排板；不自行占正在 U1 的板。

## 边界

### 允许修改
- benchmark/2026-09-30-n2-native/**
- specs/native-n2/**
- tools/spec-checks/**
- README.md 与 .octos/KNOWLEDGE-DIGEST.md

### 禁止
- 修改已冻结源、installer、provider、JAR、APK、ART、boot image
- 修改已签 N1 包，或以静态测试代替设备点亮
- 无板锁写板、加入未说明的全系统 namespace 共享

## 验收标准

场景: 六簇源码与边界逐项记录
  测试: n2_sources_and_predictions
  假设 N1 的六类首墙已有日志
  当 按 Mac、VM、远端顺序查源并编写处理表
  那么 六类均有原始证据、来源哈希、预测与未实现边界
  并且 Skia 条目明确交付状态，不伪报已合入

场景: 域选择与符号负控
  测试: n2_namespace_and_abi
  假设 包身份可能仅出现在 permitted path 或加载路径
  当 测试实际回调、JNI 表与 ELF 导入版本
  那么 已授权包选择正确且非目标包行为保持
  并且 旧实现或删掉必要导出的负控被拒

场景: 冻结与可回滚部署包
  测试: n2_package_and_frozen
  假设 N2 构建完成
  当 校验 frozen、SHA、依赖闭包与部署 dry-run
  那么 原冻结行为保留且候选包可核验回滚
  并且 构建源码、命令与工具链身份有持久记录

场景: 设备证据诚实交接
  测试: n2_handoff
  审核: human
  假设 外环统一排板
  当 提交 N2 部署与验收命令
  那么 明确 HW/ZZ、保护组、目标组、时限与回滚条件
  并且 未执行设备实验标 unverified，有实验时附 facts 原文和 t20
