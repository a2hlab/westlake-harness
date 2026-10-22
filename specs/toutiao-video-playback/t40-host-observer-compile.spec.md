spec: task
name: "T40 compile passive host observation candidate"
inherits: project
depends: [t39-host-launch-observation]
satisfies: [REQ-TTVIDEO]
---
## 意图
将 T39 已复核源码编译成可追溯 ABC，排除 Node 模拟通过而实际工具链不接受的缺口。此次只验证可编译性，不改变设备或重入行为。
## 已定决策
- 输入固定为主线 T39 的 candidate fc0e5ec024d34b27e56ac9841eb2cae9a5dd95de84d4da72c71418e1cfae0e56、baseline 9dc302d9aa72eb1be8635d7bc4bc4306da76f0e45d2414d67bd96d024e2a24c6；原件只读。复用 T32 compile_abc.py 的原始工具参数与日志方式，另目录实现。
- 工具链固定 Linux es2abc SHA d20db2d40cef6ae897eeb736e6023625f507f89ba67b0d6cdcb602ca0a21fb0c，target API20，输入文件名 EntryAbility.js。先复现 baseline ABC bb1eccd3338dde573393b24d81e26e67450d5461ba51f73e578d9e42a78cbde9，再编译候选两次比较字节。
- 只用既有允许的编译通道；权限拒绝时保留原文并停止该操作，不变更权限、不另找通道绕过。不运行任何设备命令、签名、打包、安装或 T38 编排。
- 输出新目录不可复用；真实命令执行时保留 argv、cwd、开始结束时间、stdout、stderr、rc 与 SHA，写入持久目录。无原始执行证据不得标记编译完成。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-host-observer-compile/**
- tools/spec-checks/tests/toutiao_host_observer_compile.rs
### 禁止
- 不修改 T39、T32、sources、冻结项、其他车道文件、权限配置或 Git 共享引用，不推送。
## 验收标准
场景: 精确工具链复现并编译候选
  测试: toutiao_host_observer_compile
  假设源和工具链 SHA 与锁文件相符
  当真实编译基线及两次候选
  那么基线 ABC 与历史 SHA 一致、两次候选逐字一致且命令 rc 均为0，原始日志可按 SHA 校验
场景: 输入或历史基线不符
  测试: toutiao_host_observer_compile
  假设源码或编译器 SHA 错误或基线 ABC 不符
  当运行构建检查
  那么非零退出且不得记录候选已通过
场景: 编译不可用或日志缺失
  测试: toutiao_host_observer_compile
  假设编译被拒绝、失败或原始日志缺失
  当生成结果与校验报告
  那么状态明确为未完成并保留已发生失败，不以模拟结果代替真实编译
## 排除范围
HAP 打包签名、设备部署、手点来源认定、自动恢复、白屏修复验收、原神调试。
