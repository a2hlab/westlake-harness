spec: task
name: Audit JAR freeze candidates and freeze U4 per-key expectations
inherits: project
---
## 意图
Give the outer loop a registration-ready or missing-evidence table for two JAR freeze candidates and a 66-key forecast pinned to actual J4/J5/N3b artifacts.
## 已定决策
- Verify distinct app evidence, captured t20 images, PID-attributed failure disappearance, split source blobs and emitted build provenance.
- Mixed alarm/vibrator files cannot freeze unverified behavior; existing FZ identifiers cannot be reused. Emit proposals only, never edit frozen.json.
- Separate existing lights, new first-screen forecasts, named checkpoint passage and secondary-functional repairs. Missing provider inputs and exact Java/native contract gaps remain explicit blockers.
- Keep old predictions immutable and pin APK revisions, candidate SHA, baseline evidence and freeze timestamp for later scoring.
## 边界
### 允许修改
- benchmark/2026-09-30-freeze-audit-u4/**
- specs/freeze-audit-u4/**
- tools/spec-checks/src/lib.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### 禁止
- No changes to runtime sources, input APKs, board state, frozen registry or prior reports.
## 验收标准
场景: 冻结证据与登记草案
  测试: freeze_u4_eligibility
  假设 Two JAR candidates, source blobs and archived app observations are available
  当 Offline audit validates their evidence and source scope
  那么 Each candidate has an explicit admission verdict and remaining actions
  并且 No mixed-behavior or duplicate-ID proposal is admitted
场景: 实物契约缺口与不可用输入
  测试: freeze_u4_contract_gap
  假设 J5 and N3b require matching Java classes and real provider inputs
  当 DEX definitions and native requirements are compared
  那么 A missing required class or provider blocks an unconditional WebView success prediction
场景: 六十六项前瞻冻结
  测试: freeze_u4_predictions
  假设 The current 66-key identity and actual candidate hashes are pinned
  当 Forecast files are generated
  那么 Every key occurs once and already-lit functional repairs are not new lights
  并且 Missing or altered source hashes are rejected during validation
## 排除范围
- Registering frozen APIs, implementing fixes, installing WebView, device scoring, or changing external screenshot signatures.
