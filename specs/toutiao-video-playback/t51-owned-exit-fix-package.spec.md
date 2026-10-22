spec: task
name: "T51 package the accepted owned exit fix with exact rollback"
inherits: project
depends: [t50-owned-exit-race-fix]
satisfies: [REQ-TTVIDEO]
---
## 意图
将外环独立复验采认后的T50源码转为可重复构建的禁用候选包，消除手工修改入口与成员哈希链的风险。复用T47真实builder与已保存前像，不部署、不沿用历史签认作为新窗口授权。
## 已定决策
- 外环交付精确T50 watchdog SHA及owner SHA后才生成最终包；来源文件、git对象、配方及原始执行日志全部绑定。暂未获采认的候选不能以最终包交付。
- 从T47 public baseline九控制文件及T46-P2完整成员记录重建输入；T48恢复仅证明历史前像，下一窗口仍需fresh准入。以本卡source-lock为准，不让--sources参数暗中沿用T47 CARD锁。
- 真实build派生watchdog/owner→entry内嵌SHA→13成员表→禁用startup.env→startup.expected.sha256；六候选+六精确rollback，保留mode元数据，boot-entry/config/init保持不变。不执行任何输入配置或脚本。
- 已经纳入仓库的旧源与日志不覆盖；新目录保留源码、机器清单、README复现命令、rc=0原始stdout/stderr/argv/start/end。fresh输出、显式拒绝错源/错前像/旧输出/混用锁。大原始文件持久私有，仓库记录哈希和路径。
## 边界
### 允许修改
- benchmark/2026-10-22-toutiao-owned-exit-fix-package/**
- tools/spec-checks/tests/toutiao_owned_exit_fix_package.rs
### 禁止
- 设备与远程操作、部署、启用startup、执行输入内容、历史签名复用、历史源覆盖、权限修改、commit/push。
## 验收标准
场景: 精确源组包并可重现
  测试: toutiao_owned_exit_fix_package
  假设外环已采认的T50源SHA及完整前像记录
  当实际builder在两个fresh输出目录执行
  那么六候选文件逐字一致且完整哈希链自洽，六rollback与原前像一致，startup保持禁用，原始stdout stderr rc与输入清单持久保留
场景: 错源和混合旧锁被拒绝
  测试: toutiao_owned_exit_fix_package
  假设源漂移、前像漂移或误用T47锁
  当执行实际组包入口
  那么非零拒绝且不生成可用候选包，不以旧T47测试PASS代替本包测试
场景: 旧输出与输入代码不执行
  测试: toutiao_owned_exit_fix_package
  假设输出已存在或输入配置含不允许的语法
  当实际builder解析并组包
  那么非零拒绝且旧输出字节不变，没有执行输入中的命令
## 排除范围
fresh设备准入、启用配置、维护计划签认、上板、手动关闭重开验收与封板。
