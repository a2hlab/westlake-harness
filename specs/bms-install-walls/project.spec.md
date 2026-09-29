spec: project
name: "BMS installation-wall offline preparation"
---

## 约束

- #77 is explicitly offline: no hdc, board writes, installs, process starts or lock operations.
- Original APKs and 00.Workspace/real-work/Westlake source trees are read-only.
- Findings distinguish verified byte/log evidence from predicted post-fix behavior.
- Candidate patches are reviewed and deployed by the outer lane; this lane cannot commit git metadata.
