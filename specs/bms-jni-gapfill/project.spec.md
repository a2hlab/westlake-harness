spec: project
name: "Framework JNI gap inventory"
---

## 约束

- Offline only; all external JARs, APKs, libraries, source trees and logs are read-only.
- Evidence absence is not proof of no implementation; distinguish observed attempts, compiled coverage, confirmed ULE and unknown.
- Bounded reachability is conditional; no static path is not proof of first-screen unreachability.
- No runtime repair, board writes, git metadata writes or invented source implementation.
