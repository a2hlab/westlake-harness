spec: task
name: "N3 资源与 native 簇离线候选"
inherits: project
tags: [native, n3, cx-t0]
---

## 意图

读取 U2 原始首个致命点，核 VLC 资源属性链、SPD EGL、Noice 音频与 Termux 白屏。按 Mac、VM、hw248 顺序查验证实现，与 cx-bms N3 表合并后只出一个候选。日志不支持的归因不强行补 native，逐项记边界。

## 已定决策

- U2 51a78bde 不动，FZ-001/002/003 不动，JAR/APK/boot/ART 不动。
- 优先照抄 Westlake 已验证实现；无现成件先复现最小可证伪条件。
- 资源缺属性先核 APK 原始表与实际主题链，不能凭异常直接认定 OH 解析器错误。
- 无运行期证据不把静态闭包称为点亮。

## 边界

### 允许修改
- benchmark/2026-09-30-n3-native/**
- specs/native-n3/**
- tools/spec-checks/**
- README.md 与 .octos/KNOWLEDGE-DIGEST.md

### 禁止
- 修改冻结源、统一态包、JAR、APK、ART、安装器、provider
- 任何板写操作、以伪数据冒充 API 能力

## 验收标准

场景: 当前墙逐项分层与来源
  测试: n3_cluster_sources
  假设 U2 首墙和 cx-bms 簇表可读取
  当 核对四项派单与新增 native 簇
  那么 每项有原始证据位置、源码来源、处理或未实现理由
  并且 VLC 属性能追到实际 APK 与主题父链

场景: JNI 与加载域检查
  测试: n3_jni_and_domains
  假设 现成 EGL 配方和私有域按原样移植
  当 核注册表与现役 DEX 并运行域负控
  那么 签名匹配且非目标域不扩大
  并且 旧缺失表或移除必要库的负控被拒

场景: 包身份与冻结门
  测试: n3_package_frozen
  假设 编译产物齐全
  当 核 SHA、导出和依赖并执行 dry-run
  那么 新包不改变未声明件且冻结零违例
  并且 损坏 SHA 的负控拒绝

场景: 离线交接诚实分级
  测试: n3_handoff
  审核: human
  假设 本轮没有独占板授权
  当 提交候选与验证命令
  那么 明确未验证设备效果与控制回退条件
  并且 附恢复 U2 指纹与释放板锁的步骤
