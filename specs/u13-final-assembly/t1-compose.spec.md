spec: task
name: "Final JAR composition and fail-closed approval transfer"
inherits: project
---

## 意图

Bind the final JAR and all native findings to one disabled U13 package without borrowing previous gate results.

## 已定决策

- Update the native inventory and effective framework target together.
- Compare complete findings without only issue binding fields; do not discard source evidence.
- Preserve old to new issue mappings and require exact production delta approval.

## 边界

### 允许修改
- benchmark/2026-10-03-u13-final-assembly/**
- specs/u13-final-assembly/**
- tools/spec-checks/tests/u13_final_assembly.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Final composition keeps native and boot owners
  测试: u13_final_assembly
  假设 The old bundle and final donor JAR hashes are pinned
  当 Both runtime JAR copies and native inventory are updated
  那么 The only payload difference is that JAR and the host and boot group remain unchanged

场景: Approval fails closed on semantic or production delta drift
  测试: u13_final_assembly
  假设 The old two N1 findings have signed review identities
  当 A source field or production delta differs from authorized conditions
  那么 No approval is transferred and the difference remains explicit

## 排除范围

- Device operations, deployment and screenshot claims.
