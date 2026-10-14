spec: task
name: "RouteB package directory owner repair"
depends: []
---
## 意图
5cd已实证RouteB包根root:root0755阻止UID20011300创建app_webview，随后WebView异常退出。提供仅该目录owner的受控实验，以及另版本JIT准备脚本修复首次创建和已有root-owned目录；61b存活无窗口另案。

## 已定决策
- 外环独占5cd锁执行不超过30分钟，内环零设备调用；原件、用户数据和旧attempt保留。
- 实验仅chown一个固定包根，保inode/mode/label；首写前核boot/parent birth/namespace同inode/精确metadata且无子消费者，回滚同样CAS。
- 持久候选不自动安装；仅显式包根/code_cache/art-volatile逐项校验，拒symlink和foreign owner，不递归chown。

## 边界
### 允许修改
- specs/toutiao-manual-repair/**
- benchmark/2026-10-14-toutiao-manual-repair/**
- tools/spec-checks/tests/toutiao_owner.rs
### 禁止
- 不改冻结源/运行时/表格，不清数据，不预建app_webview，不杀parent，不向61b发设备命令。

## 完成条件
场景: 单目录精确变更与回滚
  测试: toutiao_owner
  Given 固定5cd目标和boot/parent/metadata前像
  When 生成并离线验证preflight apply rollback脚本
  Then 仅包根owner变化且回滚绑定原inode和原metadata

场景: 错误身份零写拒绝
  测试: toutiao_owner
  Given 错boot或错inode或foreign owner或symlink
  When 校验实验输入或持久JIT候选
  Then 返回非零且拒绝未授权owner变更

场景: 首次与既有目录
  测试: toutiao_owner
  Given 缺包目录或root-owned包目录或已正确owner目录
  When 执行离线JIT目录测试
  Then 包根和code_cache先回填owner并保已有mode且art-volatile保持0700

场景: 真实WebView复验
  审核: human
  测试: toutiao_owner
  Given 外环授权的独立5cd窗口
  When 外环手点并复验WebView数据创建和真实截图
  Then 仅真实日志与截图证明本次修复且未执行时保留pending
