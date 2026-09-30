spec: task
name: "Port unpinned live B10 paths"
inherits: project
---

## 意图

Audit the ten temporary B10 path-exception files, migrate unpinned live paths and remove only their approved temporary exception memberships.

## 已定决策

- Use the existing lab_paths WORKSPACES resolver or script-relative paths.
- Retain source bytes when historical freezes pin the live script; record that evidence separately from frozen copies.
- Preserve all unrelated exceptions and all three permanent frozen-copy exceptions.

## 边界

### 允许修改
- benchmark/2026-09-29-static-wall-prediction/*.py
- benchmark/2026-09-29-static-wall-prediction/.gitignore
- benchmark/2026-09-30-r16-prospective/collect_results.py
- benchmark/2026-09-30-r17op-prospective/prepare.py
- benchmark/2026-09-30-v2-scanner-feedback/profile.py
- benchmark/2026-10-01-b10-path-port/**
- knowledge/gates/user-path-exceptions.json
- specs/b10-port-u5-score/**
- tools/spec-checks/tests/b10_port_u5.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Relocated workspace paths override former host paths
  测试: b10_port_relocation
  假设 A temporary directory is selected by WORKSPACES
  当 Each migrated live module is imported without running its generators
  那么 Its configured input paths resolve beneath that directory or its documented parent

场景: Frozen evidence and unrelated exceptions remain intact
  测试: b10_port_preservation
  假设 Ten temporary entries and three frozen-copy entries are audited
  当 Ported files are removed from the temporary registry
  那么 Only ported memberships disappear and retained files have their original SHA256

## 排除范围

- Rewriting freezes, new exception approvals, and runtime deployment.
