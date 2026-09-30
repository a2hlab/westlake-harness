spec: project
name: "BMS native sidecar assembly"
---

## 约束

- Original APKs and external input/source trees are read-only; no git metadata writes.
- This lane is offline only per the updated assignment; outer loop owns Firefox board validation.
- Screenshots establish lighting; FakeBoard tests establish only orchestration behavior.
- Installer deployment is owned by the outer loop; report unavailable build tools honestly.
