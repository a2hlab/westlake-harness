spec: project
name: "Offline admission evidence for accepted N11h"
---

## 约束

- Preserve accepted host65ac5089 and audit manifest37c48e2b/inputs a825ba23; do not rebuild, deploy, take a device lock or modify U10.1/T8.
- Use actual accepted source and hash-bound raw artifact/gate evidence, not a proxy library or an invented approval.
- Unavailable optional compat is diagnostic, neither smoke failure by itself nor proof of success; fingerprints, required owners, controls and screenshot decisions remain independent.
- Produce proposed registry deltas only; never edit the live exception registry or approve the new N1 observation.
- All cited evidence paths must exist in this worktree or already-landed master; no user-home paths in landing files.
