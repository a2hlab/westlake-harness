# T128-B access source review 01 — final (2026-10-25)

Conditional pre-evidence for t3: the production record reader's admission conditions, evaluated offline against three verified input sets — the reader source (`.private/t128-access-input/`, 4/4 SHA), sanitized observed 61b metadata (`.private/t128-observed-snapshot-01/`, 12/12 SHA), and the root-captured 518-byte window record (`.private/t128-observed-record-01/`, 2/2 SHA; private analysis only, body not republished). Not a child read, not a deployment, not t3 execution; no white-screen claim; no device/build/candidate changes this round.

## Three final conditions

**C1 — DAC admission.** Satisfied at metadata level: regular file `window-state.json`, mode 0660 (no S_IWOTH), uid/gid 20011206 matching the child's four-field identity (CapEff 0), size 518 ≤ 8192, and every parent directory traversable for uid 20011206. Runtime-unknown: the child's own `open()` at a future poll. SELinux fact: `enforce=0` was observed at capture time — no SELinux denial was being enforced then (read-only observation, no permission changed, no child read claimed); any future enforce transition is listed only as a limitation, not mixed into this capture's conclusion.

**C2 — Namespace path identity.** Satisfied at metadata level: direct path and `/proc/22035/root/...` resolve to identical dev 66352 / inode 438987 / owner / mode / size; child is in its own mount namespace; no final-component symlink divergence. Runtime-unknown: whether the producer's replacement cadence passes the reader's in-child before/after/lstat StableRead triple at a future poll.

**C3 — Record body vs parser and recovery gates.** **Parse-admissible, not foreground.** The captured bytes pass every byte-level reader gate offline — no NUL, depth 5 (≤16), no duplicate keys, `event="stage-event"` (allowed), details + window objects present, `window.id=62` in 1..INT32_MAX — so `ReadWindowRecord` on these exact bytes deterministically returns `Status::Candidate` with `stage_event=4`. But the T126 recovery admission gate (window-ready OR stage ∈ {1,2}) **rejects stage 4**: this record would leave the coordinator at `Outcome::Idle` by design — no recovery attempt. This is a deterministic offline conclusion about the current bytes; which record version exists at the child's next poll remains runtime-unknown.

## Cross-lane status

Codex is separately running a production-reader byte replay on these bytes; outer will merge verdicts. Pending: child-side read success at future poll; a foreground-qualifying record (none observed — stage 4 only). Machine-readable detail: `results.json`.
