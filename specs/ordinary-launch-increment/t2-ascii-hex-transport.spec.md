spec: task
name: "ASCII hex transport for ordinary increments"
inherits: project
depends: [t1-readonly-observer]
---
## 意图
已实证HDC丢弃cmdline的NUL，独立修订传输而不覆盖已采认v1证据。cmdline和日志增量先转ASCII hex，本地严格还原。
## 已定决策
- 仅新增incremental-observer-hex，v1源码/manifest/validation保持原样并固定SHA引用。
- 唯一新增远端工具为实测/bin/od；-An -v -tx1配精确-j偏移/-N长度，不使用awk/tr/wc，不把原始二进制放入shell变量。
- 本地验证ASCII帧、版本、十六进制token、声明原字节数和实际解码长度；拒绝星号压缩、坏token、短读取和旧二进制帧。
- 保持90秒/1MiB双流总量/单命令10秒、出生partial不推进偏移和原身份文件停止条件；本轮无设备调用。
## 边界
### 允许修改
- benchmark/2026-10-24-ordinary-host-timeline/incremental-observer-hex/**
- specs/ordinary-launch-increment/t2-ascii-hex-transport.spec.md
- tools/spec-checks/tests/ordinary_launch_hex.rs
### 禁止
- 已采认v1原件、设备动作、控制脚本/env、信号和保护分析、REA、运行时修改、推送。
## 验收标准
场景: HDC丢NUL模拟传输
  测试: ordinary_launch_hex_fixtures
  假设cmdline及普通日志含NUL和非ASCII字节
  当真实本地shell的od编码输出经过删除NUL的模拟通道
  那么wire全ASCII无NUL且本地还原与原字节相同，v1旧帧反例拒绝
场景: 错误编码和短读取
  测试: ordinary_launch_hex_fixtures
  假设错误长度或坏hex或星号压缩或不完整帧
  当解析候选传输
  那么拒绝且不推进已确认偏移，原始回执保留
场景: 继承预算与出生边界
  测试: ordinary_launch_hex_fixtures
  假设超过13KiB完整ps且受限PATH没有awk/tr等工具
  当真实shell连续90样本并重放原身份轮转超时出生用例
  那么目标筛选不被无关行耗尽预算且原15用例保持通过
## 排除范围
本轮真机smoke、日志缓冲根因、UI自动点击、控制实现修改。
