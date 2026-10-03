spec: task
name: "U16 t4 runtime native offline slot"
inherits: project
depends: t1-inputs
---

## 意图

Stage the accepted M1 split runtime1d42 on exact U15 runtime94c3 and report fresh offline native gates while Flutter interposer and all rebaked images remain pending.

## 已定决策

- Only one runtime payload changes; every other U15 native file alias and namespace domain is preserved.
- Bind actual split shim and M1 translation-unit sources into the candidate scanner input sidecar; do not claim the old inlined source describes the new artifact.
- Run open-site, NEEDED, strings, ABI calls and the exact219-member consumer set against U15; raw rejection stays rejection.
- N1/N2 read the current active exception table; no application, automatic signature or active-registry write occurs.
- Accept the corrected t1 receipt only when artifact and classes.dex hashes both match; preserve the historical mismatch evidence.

## 边界

### 允许修改
- benchmark/2026-10-03-u16-assembly-draft/**
- specs/u16-assembly-draft/**
- tools/spec-checks/tests/u16_assembly_draft.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Runtime-only staging has exact source and consumer bindings
  测试: u16_draft_native
  假设 Runtime1d42 donor and U15 content package are independently hashed
  当 Native-only staging and fresh static reports are checked
  那么 Exactly one runtime payload changes with a source-bound sidecar and219 consumers while execution rollout and final bundle remain disabled

场景: Rejection incomplete provenance or fake readiness does not pass
  测试: u16_draft_native
  假设 Candidate findings may have new manifest and source evidence bindings
  当 A gate rejects or a source identity or preserved payload changes
  那么 The report retains each raw exit and explicit pending review without writing the active exception table or claiming native production approval

## 排除范围

- Compile native artifacts, rebake images, contact devices or VMs, or approve findings.

