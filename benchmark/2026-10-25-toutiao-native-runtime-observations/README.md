# Native candidate: partial usable UI, then an exited-child white screen

The earlier interpretation was too broad: a white screenshot after a successful
mapping check does not establish a live-child rendering failure. In run
`aa4d97`, child **6879** existed at s30 but was absent at both s60 and s90.
The host **4948** and appspawn parent **5076** remained. The exit cause is unknown;
this record does not attribute it to the native candidate or anti-virtualization.

Candidate `3291f76d…` has real device evidence, but **is not sealed**:

| Run | Actual observation | Limit |
|---|---|---|
| `43e2a3` | First-open feed and same-host return responded to scrolling. New host 10685 retained child 7013 and showed the feed. | Recreated-host content interaction missed its review deadline; a retained frame alone does not pass. A narrow text column is visible. |
| `aa4d97` | Candidate mapped in child 6879; s5/30/60/90 images were white. Child disappeared between s30 and s60. | No confirmed feed; later white images show the surviving host after child exit. |

The `aa4d97` window restored the exact `b0e5602a…` baseline, verified its actual
mapping during recovery, restored power settings and released its lock in
**370.499 seconds**. Final `mapping_now=not_running` is preserved separately from
the earlier successful recovery binding. Neither is an application-health claim.

The ordinary child log was **457,852 bytes**, below the 4 MiB capture limit;
its complete persisted contents were retrieved after rollback. SHA-256:
`bd9b24a2980cbcc7fe53362e051649f9621c81e594723e006644e18524773e54`.
It contains successful window/foreground/focus request returns, which do not
prove display composition. Its injected parent ID 32 matches the same-round
host layout; that specific stale-ID mismatch hypothesis is unsupported.
No `HOST-SESSION` line does not prove the recovery observer was inactive:
the implementation intentionally suppresses Idle and Throttled outcomes.

Selected original images and identity receipts are pinned in [results.json](results.json).
Complete closed-run receipts, layouts, logs and images are preserved outside the
worktree at `$HOME/.local/share/westlake/t136-runtime-evidence-20261025/`, with a
per-run SHA-256 inventory. Runtime source and build records remain in
`../2026-10-24-native-host-window-recovery/`. Two-boot retention tooling is in its
`demo-seal/reentry/` directory; offline tests are not a device acceptance result.

Rule: classify each white observation using the contemporaneous child identity.
The next ordinary check is desktop reopening after child exit; random-exit
remediation remains outside the requested demo task.
