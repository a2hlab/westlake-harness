spec: project
name: "Deployed source reconciliation"
---

## 约束

- Read-only deployed ELF and existing source/object archives; no compiler, linker, board or package operations.
- A matching symbol or string alone is not proof of exact source provenance.
- Select authenticated build snapshots and retain unsupported or historical files without landing them.
- Reconcile U10.1T8, not later U12/U13 candidates; do not overwrite unrelated master hardening.
