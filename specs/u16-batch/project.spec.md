spec: project
name: "U16 batch contracts — per-cluster fixes, one JAR version + one native version"
---

## 约束

- 按簇批量:U16 出一版 JAR 与一版 native;每个改动件在落地前必须通过 `scripts/lab/check_fix_observers.py`(token / SHA 前缀 / 冒烟标记 / 派生件四通道)证明自己有至少一个观察点——无观察点的改动件不得进批。
- 冻结规则:改动命中冻结表(FZ-00x)的文件,只有『同一产物加新功能且原行为保留』路径可行,须外环事先批准并在单板重验原证据 app 后登记新版本;其余改动走新文件。
- 新修新文件:U16 的修复一律新增源文件(不动既有修复的文件),除非目标本身是既有文件的一行修正且外环批。
- 每个任务先出契约(`specs/u16-batch/t*.spec.md`,agent-spec lint --min-score 0.7 过)再实现;本目录当前只有契约,不含实现。
- 测试选择器一律指向 `tools/spec-checks/` 的 Rust 测试,由它转调真正检查器;需要人读截图的验收标 `审核: human`。
- 上板窗口、锁、回滚、指纹核验按 AGENTS/RUNBOOK 执行;契约内不写部署参数。

## 交付物

- `specs/u16-batch/`:本 project 约束 + t1–t5 任务契约(依赖用 `depends:` 串)。
- 每个 t*.spec.md 至少包含:意图、已定决策(含来源表引用)、边界(允许修改/禁止)、验收标准(场景+可 grep 断言+测试选择器)、排除范围。
