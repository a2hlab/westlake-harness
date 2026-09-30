spec: project
name: "PID-scoped first-frame suspicion replay"
---

## 约束

- Offline only in this worktree; do not touch devices, raw runs, frozen predictions or input packages.
- Use U6 full runs and T7d 5cd logs; retain every attempt and bind record/log/capture hashes.
- Suspicion is not root-cause proof or a lit judgment; t20 remains outer-reviewed original capture, never a later nudge.
- Count only app-PID execution events inside the launch-to-t20 interval; global compositor counts cannot establish app present behavior.
