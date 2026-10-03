spec: project
name: "61b reconnect recovery preparation"
---

## 约束

- Prepare and test offline in the lane worktree; do not contact a board, VM or SSH.
- Actual recovery belongs to outer or cx-t0, using the existing window2 journal and production executor.
- Keep the cx-t0 lock on any failure. No fresh apply, reboot, mount workaround or unrelated board operation.
