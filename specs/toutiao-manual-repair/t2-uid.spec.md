spec: task
name: "Explicit installed-host UID JIT51 successor"
depends: [t1-owner]
---
## 意图
在冻结5cd候选之外交付显式UID参数入口，避免61b误用20011300。只有显式期望UID与installed host及私有data根owner一致时继续原目录修复。
## 已定决策
- 原5cd冻结件不改，参数入口无默认UID，不动态接受任意当前owner。
- 沿用原JIT51目录行为，发布仍需原compiler更新脚本及调用wrapper独立SHA。
## 边界
### 允许修改
- benchmark/2026-10-14-toutiao-manual-repair/jit51-parameterized/**
- specs/toutiao-manual-repair/t2-uid.spec.md
- tools/spec-checks/tests/toutiao_jit_uid.rs
### 禁止
- 不执行HDC，不改已冻结5cd候选或旧启动配置。
## 完成条件
场景: 实际owner与显式期望一致
  测试: toutiao_jit_uid
  Given 61b或5cd显式UID和相同的installed host私有data owner
  When 执行本地参数守卫
  Then 守卫通过且源差异仅参数和owner一致性校验
场景: 错UID零写
  测试: toutiao_jit_uid
  Given 显式UID与任一owner不一致
  When 执行本地参数守卫
  Then 返回非零并且零目录变更
场景: 缺参数或非法UID
  测试: toutiao_jit_uid
  Given 没有期望UID或非法数字
  When 执行本地参数守卫
  Then 返回非零且不以当前owner作为默认值
