spec: task
name: "Predict launcher Activity trampolines from exact APK bytecode"
inherits: project
depends: [t1-signed-shards]
---

## 意图

Scan all 66 pinned APKs for launcher lifecycle startActivity and finish calls and intersect predictions with white black and first-screen observations.

## 已定决策

- Use manifest MAIN plus LAUNCHER including aliases and inherited lifecycle methods; report runner override separately.
- Evidence identifies APK and DEX hashes plus method and instruction offsets; unresolved code is unknown rather than a negative.
- Direct lifecycle calls and bounded synchronous helper calls are distinct from callbacks or unrelated methods. Conditional calls are possible not guaranteed immediate jumps.
- Explicit destination classes and finish evidence are recorded when available; class-name strings alone do not constitute a call.
- ActivityResultLauncher.launch is a separate modern routing candidate, never mislabeled as a literal startActivity call; superclass lifecycle delegation does not consume the three-helper budget.
- Modern launch operand context must separate a permission-string input from an Intent object; permission requests are recorded but not counted as app-to-app trampolines.
- Negative controls require two lit apps with one declared Activity and no lifecycle trampoline evidence; controls are chosen from manifest and code, not assumed.
- Outer explicitly accepted the observed control boundary: ooniprobe is a bounded Java negative; fd-stk has four native helper gaps and remains unknown/non-alert, never counted as a complete negative. Add a multi-Activity lit bounded Java negative separately.

## 边界

### 允许修改
- benchmark/2026-10-01-trampoline-scan/**
- specs/u7-followup/**
- tools/spec-checks/tests/u7_followup.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Manifest lifecycle and opcode rules distinguish positive negative and unknown
  测试: trampoline_rules
  假设 Aliases inherited callbacks helpers conditional calls unrelated strings and missing methods
  当 Offline bytecode rules are applied
  那么 Only reachable lifecycle start calls are candidates while callback-only references stay separate and missing code is unknown

场景: Sixty-six rows and two negative controls remain reproducible
  测试: trampoline_replay
  假设 Pinned manifest and instruction extracts for sixty-six apps
  当 The machine-readable report and symptom intersections are replayed
  那么 Every key appears once the two proven single-Activity lit controls are not reported and evidence tampering is rejected

## 排除范围

- Device execution and claiming static evidence proves the second-window attachment defect.
