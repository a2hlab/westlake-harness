# Contract Review: N5 Flutter dependency visibility and native predeploy wiring

## Intent

Build one N4-order-based offline candidate for the Flutter private-domain
runtime dependency, and integrate the delivered N1/N2 gates before device access.

## Decisions

- Read OH musl source before selecting the bounded six-package repair.
- Preserve native non-target paths, frozen sources and the current U5 artifacts.
- Reject unresolved native checks; no bypass or fabricated build/source binding.
- Rollback gates inspect the restored target, not the failed candidate.

## Boundaries

**Allowed:**
- benchmark/2026-10-01-n5-native/**
- benchmark/2026-09-29-static-wall-prediction/**
- scripts/lab/deploy_generation.py
- scripts/lab/deployment_native_gate.py
- scripts/lab/native*.py
- scripts/lab/test_deploy_frozen.py
- benchmark/2026-10-01-native-predeploy-gates/**
- knowledge/gates/native-predeploy-exceptions.json
- specs/native-n5/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

**Forbidden:**
- N5 device deployment, edits to published packages or gate exceptions without approval
- ART, provider, boot image, JAR, installer, APK or frozen-source edits
- Treating static namespace checks as proof of rendered apps or one runtime instance

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 4 | 0 | 0 | 4 | 0 | 0.0% |

- ⏭️ Bounded Flutter path and loader semantics
- ⏭️ Native gate precedes all device access
- ⏭️ Candidate assembly and honest rejection
- ⏭️ Offline review handoff

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | Bounded Flutter path and loader semantics | n5_flutter_paths | found | skip | — |
| — | Native gate precedes all device access | n5_predeploy_hook | found | skip | — |
| — | Candidate assembly and honest rejection | n5_package | found | skip | — |
| — | Offline review handoff | n5_handoff | found | skip | — |
