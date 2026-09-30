spec: task
name: "Detect native namespace and JNI initialization order walls"
inherits: project
---

## 意图

Add source-based detectors for the two missed native initialization walls, with reproducible N3b/N2 and N4/N4-order replays. Report bounded static risks and unknown coverage separately, never substitute source ordering for successful runtime initialization.

## 已定决策

- Analyze actual C/C++ call sites and namespace identity; inheritance is not a prior load. Comments and unrelated namespace loads cannot satisfy a NOLOAD prerequisite.
- Walk native initialization calls in source order and join JNI ID lookups with pinned DEX class-initialization dependencies and native registration calls.
- Retain source and DEX hashes, original line/offset witnesses, and generation identity in offline replay inputs. Unknown indirect calls or missing dependencies remain unknown.
- N3b and N4 are positive retrospective examples; N2 and N4-order are negative examples for the respective rule, not claims that all runtime walls are absent.

## 边界

### 允许修改
- benchmark/2026-09-29-static-wall-prediction/rules_native_initialization.py
- benchmark/2026-09-29-static-wall-prediction/scan_native_initialization.py
- benchmark/2026-09-29-static-wall-prediction/test_native_initialization.py
- benchmark/2026-09-29-static-wall-prediction/native-initialization/**
- benchmark/2026-09-29-static-wall-prediction/README.md
- tools/spec-checks/tests/native_initialization.rs
- specs/bms-static-v3/t9-native-initialization.spec.md
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No runtime source repairs, devices, frozen prediction edits, historical score changes or pushes.

## 验收标准

场景: Namespace prerequisite replay
  测试: native_initialization_namespace
  假设 Pinned N3b and N2 host sources are available
  当 The detector checks NOLOAD targets against earlier mapping in the same fresh namespace
  那么 N3b reports the resident runtime library and N2 has no corresponding risk
  并且 Comments inheritance wrong namespaces and later loads cannot suppress a risk

场景: JNI initialization ordering replay
  测试: native_initialization_jni_order
  假设 Pinned N4 and N4-order sources share the same DEX initialization dependencies
  当 The detector orders cache-triggered initialization and native registrations
  那么 N4 reports GLImpl initialization before registration and N4-order does not
  并且 Unreachable cache helpers do not become startup risks and missing dependencies remain unknown

场景: Provenance and incomplete inputs
  测试: native_initialization_provenance
  假设 Replay inputs have frozen source hashes and original evidence coordinates
  当 A source hash changes or an input is missing
  那么 The CLI rejects the replay instead of reporting a clean scan
  并且 Untampered replays reproduce stored results without external worktrees or devices

## 排除范围

- General C++ compilation, whole-program proof, successful RegisterNatives or class initialization at runtime, new light counts.
