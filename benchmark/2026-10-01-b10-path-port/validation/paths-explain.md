# Contract Review: Port unpinned live B10 paths

## Intent

Audit the ten temporary B10 path-exception files, migrate unpinned live paths and remove only their approved temporary exception memberships.

## Decisions

- Use the existing lab_paths WORKSPACES resolver or script-relative paths.
- Retain source bytes when historical freezes pin the live script; record that evidence separately from frozen copies.
- Preserve all unrelated exceptions and all three permanent frozen-copy exceptions.

## Boundaries

**Allowed:**
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

**Out of Scope:**
- Rewriting freezes, new exception approvals, and runtime deployment.

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 2 | 2 | 0 | 0 | 0 | 100.0% |

- ✅ Relocated workspace paths override former host paths
  - test: `b10_port_relocation`
- ✅ Frozen evidence and unrelated exceptions remain intact
  - test: `b10_port_preservation`

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | Relocated workspace paths override former host paths | b10_port_relocation | found | pass | computational |
| — | Frozen evidence and unrelated exceptions remain intact | b10_port_preservation | found | pass | computational |
