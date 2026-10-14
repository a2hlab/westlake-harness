# Locked archive merge revision

The second real hw248 attempt restored 80477 generation members, then rejected
an overlapping external library. That was not a compiler failure. The previous
285-file checkpoint and both failed attempts remain unchanged.

The new **actual full local scan** checked both locked archives and all canonical
targets: generation 80478 tar members / 80477 targets; external 2648 targets.
All 2647 regular-file overlaps have identical SHA and identical recorded type,
mode, uid, gid, mtime, size and linkname. The single directory overlap differs
only in mtime. Existing directory metadata is retained without modification.
There are **0 conflicting files** and **0 new external targets**. This audit does
not assert equality of unapplied transport-specific PAX extensions.

`restore_provider_inputs_r2.py` first repeats the complete audit against the
two locked archives. It rejects changed bytes or recorded metadata, new targets
and unsupported restored objects. It invokes the original frozen restorer for
the generation only, then checks every external duplicate against the actual
fresh staged file SHA, size and mode. No external file is overwritten. The
unchanged provider entry is invoked only after this succeeds. This is a narrow
dependency-restoration revision, not a source, API or compiler-flag change.

Six new known-answer tests PASS, including seven metadata subcases, changed
bytes, unexpected targets, actual staged-file tampering and symlinks. Actual
stdout/stderr/rc are in `evidence/`; the real scan's output/rc are preserved there
as well. The complete 25 MiB inventory is private persistent worktree evidence:

`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-14-verified-source-closeout/native/.artifacts/archive-merge-audit-r2/`

- `audit.json`: SHA `a4eb83542a48c94f9438973caa24a65564b8313d4fb7d9e90764ad134d0b1ffe`.
- `generation.jsonl`: SHA `bf4c7a4ed70a3df899b90ac351e7fecc0be53fb178331dd5d898e024b2dd0148`.
- `external.jsonl`: SHA `7460057d3acc99b4cbe4324bc7898029ab53f5ad3a52254db623d172941afece`.

The configured hw248 invocation is:

```sh
LAB_HOME="$PERSISTENT_HOME" bash sources/api-implementations/shared-native-production/revisions/archive-merge-r2/execute-hw248-r2.sh "$PERSISTENT_HOME/native-merge-r2-$(date -u +%Y%m%dT%H%M%SZ)-$$"
```

The new attempt must keep stdout/stderr/rc and resulting SHA separately. Pending
remote compilation is not called PASS. The original source freeze503f3acc and
its API amendment5bd5a438 are not overwritten; this revision adds a new entry.

## Checkpoint validation addendum

The original checkpoint's targeted Rust test also actually passed (1 Rust /
9 Python known answers); raw is retained in the parent's `.artifacts/rust.*`.
The old `land.py` prefix allowlist does not include `sources/`, so its preflight
rejected those paths; the explicit task contract does allow this source prefix.
Do not silently bypass or report that preflight as PASS. The outer loop must
use the task's exact source whitelist for review/commit.

An explicit all-285-file user-path scan found four historical recipe references:
three fixed dependency paths in the raw original FZ003 shell and one historical
comment in the related bridge shell. Those raw originals are **not portable
admitted execution recipes**. They remain preserved history at this checkpoint;
FZ003 cannot be labelled a complete portable production build. The new active
FZ002 entries have no author-specific path dependency. No new exemption or
historical SHA/freeze change is requested by this report.
