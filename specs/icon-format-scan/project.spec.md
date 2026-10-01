spec: project
name: "Exact installer-selected icon audit"
---

## 约束

- Offline, read-only APK/runtime/run evidence; no device operation or frozen-prediction changes.
- Use the exact 166-key v1 plus cv2 cohort and SHA-pinned inputs.
- Resource selection follows the installer resolver, not Android density preference or directory-name inventory.
- Signed screenshot outcomes and observed desktop tiles are separate axes; absent evidence remains unknown.
