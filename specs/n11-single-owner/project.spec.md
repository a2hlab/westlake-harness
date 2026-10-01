spec: project
name: "N11 single JNI owner on signed U8"
---
## Intent
Share the existing route-a bridge and runtime owners across class-loader domains. Preserve frozen APIs, production gates, U8 Java/images and rollback.
## Decisions
- Use OH6.1 musl namespace-host callbacks with exact two-library sharing and resident-only owner opens.
- Combine N10b fixes in one native candidate; source and binary identity precede load-site conclusions.
- A 61b short window lasts at most 30 minutes and always restores U8 before unlock.
## Boundaries
### Allowed
- benchmark/2026-10-01-n11-single-owner/**
- specs/n11-single-owner/**
- tools/spec-checks/tests/n11_owner.rs
### Forbidden
- No bridge, ART, frozen provider, Java or boot-image edits; no new default-namespace owner loads or gate relaxation.
