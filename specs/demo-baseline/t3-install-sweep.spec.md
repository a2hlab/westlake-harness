spec: task
name: "Install the manifest and sign first screens on the demo board"
inherits: project
depends: [t1-inventory]
---

## 意图

把 demo-manifest 里的全部 APK 装到演示板,逐个启动并在约 20 秒截图,外环逐张签认,得到首屏有内容的包数(目标 ≥100)。

## 已定决策

- 用现有 `bms_batch.py` / `board_run --detach` 流程,按清单顺序分批,每批 ≤45 分钟,批间释放锁。
- `needs_first_tap` 的应用按清单写的位置点一次,再截图;点击动作写进运行记录。
- 签认三分:亮(应用自己的内容)、半亮(空列表/加载中/带错误框)、不亮;只有亮计入目标数。
- 不亮或回退的 key 只记首个致命点,不在本任务修;从演示清单移到附表。

## 边界

### 允许修改
- benchmark/2026-10-09-demo-baseline/**
- specs/demo-baseline/**
- tools/spec-checks/tests/demo_baseline.rs

## 验收标准

场景: Every manifest app has a recorded launch and screenshot
  测试: demo_baseline_sweep
  假设 The manifest apps are installed on the demo board
  当 The sweep finishes
  那么 facts.txt lists one capture per manifest key and missing captures are reported as unknown not omitted

场景: At least 100 packages are signed lit
  审核: human
  测试: demo_baseline_sweep
  假设 The outer loop reviewed every t20 screenshot
  当 The signoff is tallied by run_facts
  那么 At least 100 distinct packages are signed lit and every non-lit key has a status and first fatal or unknown

场景: Install failure is recorded not skipped
  测试: demo_baseline_sweep
  假设 One APK fails to install
  当 The sweep continues
  那么 The key appears in facts.txt with the installer error code and the batch lock is still released

## 排除范围

- 修墙、换运行时版本、改别的板。
