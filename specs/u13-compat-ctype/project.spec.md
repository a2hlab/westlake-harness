spec: project
name: "U13 legacy ctype compatibility"
---

## 约束

- Offline only; no device, deployment, VM build or active registry mutation.
- Reproduce b2be657c before modifying it; add only the _ctype_ public symbol.
- Use verified AOSP14 original table bytes and pointer ABI, not host locale classification.
- Keep root and route aliases atomic and the U13 draft disabled; retain U12 host.
- Preserve persistent source, object, toolchain and tee build provenance.
