spec: project
name: "61b board-local effective baseline metadata"
---

## 约束

- Offline only; no board access, service upgrade, installer change, rebuild or VM use during the window.
- Original authorized U13 91272eaf stays immutable; outputs, native manifest and native input bytes do not change.
- Board-local service identity is pinned to local source artifact51e1 and signed61b evidence.
- Fresh production replay and renewed metadata authorization remain outer-owned.
