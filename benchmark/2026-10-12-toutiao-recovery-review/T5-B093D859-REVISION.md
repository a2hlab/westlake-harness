# Targeted immutable revision review

## Evidence first

The bounded ten-second poll found
`b093d8599aeffac5e4830bd2dc7f6c15806b8a28` at 20:19:32, within five minutes.
Only this Git object was exported and executed. Executor SHA:
`430fbf4a6348dc12ef107c4786a16de83c06a99330cd527c5dbbbc6aca44f30a`.
Archive SHA: `06c064b68a3349b383952c06fafae279dcdc172657ec73333f905b45cb94919e`.
The old 70b rejection and its original records remain unchanged.

## Targeted outcomes

| Existing fault family | Actual CLI outcome | Verdict |
| --- | --- | --- |
| Positive real-file authorization | apply 0, four sends | fixture baseline reachable |
| Partial second watchdog transfer | apply 2, rollback 0, both original aliases restored | old blocker removed |
| After-label null | reject 2, zero transport calls and sends | rejected before first write |
| First directory creation fails; ROOT absent | apply 2, rollback 0, zero sends, no stop; receipt `NO_MEMBER_CHANGES_NO_DONOR_RESTART` | verified no-op, not fake stop success |
| CFG inert write then failure | rollback 2 without completion; retry 0 | retry remains safe in fixture |

The same independent directory-aware recorder ran these five cases, not the
editing worktree and not the R1 suite. Four original members remain in original
order; new signed directory metadata is retained. Prerequisites remain excluded
explicitly. Synthetic tickets bind actual complete fixture files, not a hand-set
`_sha`. The model additionally supports only the new directory operations; it
never invokes recorded board commands.

The frozen author's existing CFG shell cases and late-tap case ran unchanged:
four tests in 5.280 seconds, exit 0. The three CFG cases execute the real atomic
shell on local files with recorded mount/chown/chcon substitutes: ro restoration
on success/failure and preservation of an initially rw mount. The late-tap case
compiles a host-only decoder fixture, executes the relocated entry, reaches the
guardian guard, and does not assert READY or start a real parent/namespace.

**Late-tap limitation:** its sleep substitute writes `601` into a fixture file
after one loop. This is not an actual 601-second wait. The inspected revision
does remove the old finite loop budget, and records
`until-human-or-stop-or-boot-change`; the passing case proves delayed readiness
can reach the guard, not wall-clock endurance or actual foreground interaction.

## Remaining release blocker

The export's normal manifest check failed. `checkpoint-manifest.json` is still
the 70b manifest: 11 declared hashes disagree with this immutable Git object,
and new files are not represented there. This is not silently waived. The
second attempt uses the explicit `--review-stale-manifest` flag solely to test
logic, records all mismatches and exact archive SHA, and retains the initial
rejection. Refresh the final release manifest/member/plan bindings before
admission; this checkpoint is **not approved for deployment**.

No additional executor logic blocker was observed in these requested families.
Full preboot prerequisites, real permissions/mount behavior, kernel boot,
actual foreground capture/UID/WID/parent, refresh/article, Plan-2 regression,
and sealing remain external pending acceptance. Default PENDING/disabled
startup is retained. There was no board, VM, remote, deployment, permission,
user-data, stop clearing, real authorization, or push. Only the existing local
host-decoder test fixture was compiled; no deployment artifact was built.

## Recorded entry points

```sh
python3 benchmark/2026-10-12-toutiao-recovery-review/review_t5_70b6.py \
  --commit b093d8599aeffac5e4830bd2dc7f6c15806b8a28 \
  --attempt NEW_UNIQUE_NAME --review-stale-manifest \
  --case positive_cli --case partial_send --case null_after_label \
  --case mkdir_first_failure --case inert_retry
```

The flag does not change candidate bytes or confer approval. A fresh finalized
manifest should use the normal strict mode instead. Raw stdout/stderr,
transaction receipts and source hashes are indexed by
`evidence/t5-b093d859-artifact-index.json`; targeted results are
`t5-b093d859-results.json`. Future commits require new attempts and only changed
fault-family reruns.
