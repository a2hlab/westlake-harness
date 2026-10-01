spec: project
name: "Invalid selected raster fallback for U9 native"
---

## 约束

- Offline patch proposal only; no board operations, APK edits, or runtime replacements.
- Preserve healthy PNG/WebP/JPEG and existing iconless, XML, ZIP and manifest behavior.
- Reuse only the template's own placeholder, never another app's icon.
- Header validation is bounded and is not a full WebP/JPEG decoder.
