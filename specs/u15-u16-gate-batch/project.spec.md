spec: project
name: "Signed U15/U16 gate batch preparation"
---

## 约束

- Prepare only in this worktree; never modify master gates, signed packets or authorized bundles.
- Actual application belongs to the outer after all three boards are unlocked.
- Gate tables and bundle-local static policies remain separate; no new gate schema or bypass.
