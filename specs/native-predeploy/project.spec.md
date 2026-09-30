spec: project
name: "Native build and predeploy static gates"
---

## 约束

- Work offline in this lane; do not edit deploy_generation or invoke device operations.
- Package SHA and input identity must be checked before static findings can authorize a pass.
- Findings and unknown coverage block by default; only exact, documented, approved exceptions may waive findings. Invalid inputs cannot be waived.
- Keep historical scanner evidence and selectors unchanged; no runtime-success claim follows from a static pass.
