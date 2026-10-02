spec: task
name: "Fail-closed new-native exception table"
inherits: project
---

## 意图

Permit an otherwise rejected new ELF only when its target, full artifact SHA and native package manifest SHA exactly match an outer-registered row with existing repository evidence.

## 已定决策

- Add an empty production table, never the draft mediandk row.
- Missing, malformed or invalid table/evidence remains REJECT.
- Bind the registry to executor policy identity so admission changes invalidate preflight.
- JAR additions and existing comparison criteria retain their previous behavior.

## 边界

### 允许修改
- scripts/lab/generation_static_checks.py
- scripts/lab/u7_executor.py
- knowledge/gates/new-native-admissions.json
- benchmark/2026-10-02-new-native-admissions/**
- specs/new-native-admissions/**
- tools/spec-checks/tests/new_native_admissions.rs

### 禁止做
- Register a mediandk approval, relax other criteria, use board transport or deploy.

## 验收标准

场景: Exact triple admits only the reviewed native member
  测试: new_native_admissions_exact
  假设 A fixture row for reviewed mediandk with existing evidence
  当 Exact identity and sha/manifest/target variants are tested
  那么 Only exact target artifact and manifest pass; variants reject

场景: Invalid registry and evidence fail closed
  测试: new_native_admissions_closed
  假设 Missing malformed or evidence-invalid tables
  当 A new native member reaches the static gate
  那么 All invalid states reject and the production table remains empty

场景: Other criteria and registry identity are preserved
  测试: new_native_admissions_preserved
  假设 Existing native and JAR comparisons and executor preflight
  当 The exception reader and policy binding are checked
  那么 JAR additions remain rejected and registry changes alter policy identity

## 排除范围

- Final U12 manifest approval, exception registration, window execution or runtime changes.
