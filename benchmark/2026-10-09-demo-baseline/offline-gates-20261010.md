# 演示基线离线门禁快照(2026-10-10,oc-t4 只读跑批)

宿主树:`/Users/zhaoyue/orca/workspaces/westlake-harness`(master checkout,含 specs/demo-baseline + benchmark/2026-10-09-demo-baseline 全部 t3/t4/t5/selfcheck)。五项全部**通过,零失败**;只报不修,未改任何代码。

## ① python3 scripts/lab/check_user_paths.py

```
user-paths: 28470 files, 25 exceptions, 0 violation(s)
```
退出码 **0**。

## ② python3 scripts/lab/check_frozen.py

```
frozen: 8 entries, 0 checked, 0 violation(s)
```
退出码 **0**。

## ③ agent-spec lint --min-score 0.7(specs/demo-baseline/t*.spec.md ×7)

| spec | 结果 |
|---|---|
| t1-inventory / t2-toutiao / t2b-boatattack / t2c-adapter-buildchain / t3-install-sweep / t4-stability / t5-seal | 全部 rc=0,无 gate 级发现;每份仅一条 `[INFO][bdd-rule-grouping]`(建议加 `Rule:` 分组,明确标注"not a gate") |

退出码全部 **0**。

## ④ python3 -m unittest discover(benchmark/2026-10-09-demo-baseline 各子目录)

| 目录 | 结果 | 退出码 |
|---|---|---|
| t3 | `Ran 15 tests in 0.112s / OK` | **0** |
| t4 | `Ran 28 tests in 1.055s / OK`(含 KNOWN_ANSWER 驱动自证:128 keys/8 disabled windows/no device calls) | **0** |
| t5 | `Ran 34 tests in 1.288s / OK` | **0** |
| selfcheck | `Ran 13 tests in 2.000s / OK` | **0** |

## ⑤ cargo test --manifest-path tools/spec-checks/Cargo.toml demo_baseline

```
Running tests/demo_baseline.rs (tools/spec-checks/target/debug/deps/demo_baseline-b6d6a590f6567f7f)
test demo_baseline_manifest ... ok
test demo_baseline_selfcheck ... ok
test demo_baseline_seal ... ok
test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 3.38s
```
(另 3 个测试二进制因过滤器命中 0 个测试输出 `0 passed ... N filtered out`,均为 ok。)退出码 **0**。

## 结论

五门禁 rc 全 0:**spec 层(lint+cargo)与实现层(unittest)一致通过,冻结面零违规,用户路径零违规**。本文件为快照证据,后续任何回归以同命令重跑对照。
