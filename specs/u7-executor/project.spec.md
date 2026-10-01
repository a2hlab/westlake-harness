spec: project
name: "U7 production transaction"
---
## Intent
Compose native, 27 images, stubs and runtime JAR in one reversible transaction.
## Constraints
- This task performs no device I/O and no push.
- Reuse trusted deployment primitives and required gates; do not chain full deploy commands.
