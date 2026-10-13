# Exact authorization fields

No document here grants execution. Prepare on main first; compute pins from that exact output. JSON numbers below must be actual epoch seconds, not strings.

Both independent documents contain:

- `recipe_sha256`: SHA256 of new recipe.json.
- `plan_sha256`: new recipe.plan.sha256.
- `executor_sha256`: new recipe.executor.sha256 (3f176393... in this release).
- `serial`, `boot_id`: exact new recipe values.
- `action`: `apply` or `rollback`, matching the invocation.
- `holder`: exact complete stdout.strip() of the current held command (owner PID timestamp).
- `lock_tool`: `{ "path": "$WORKSPACES/westlake-harness/scripts/lab/board_note.sh", "sha256": "ACTUAL_FILE_SHA256" }`.
- `expires_epoch`: actual future time, no more than2700 seconds from invocation.
- `synthetic`: false.
- `actions`: exactly `["place-only", "one-reboot", "rollback-safe"]` (unchanged original validator vocabulary; this core executes zero reboot).
- For apply only: `apply_deadline_epoch`, identical in both documents and <= both expires_epoch minus600.

Authorization additionally has `approved_by: "outer(codex)"`.

Admission independently has `signed_by: "outer(claude)"`, `admitted: true`, `authorization_sha256` equal to the exact finalized authorization bytes, and `target_sha256` equal to the COMPLETE recipe.targets dictionary (487 entries). Do not calculate authorization SHA before finalizing it. Admission and authorization have independent CLI pins. These required literal roles match the prior approved contract and are to be filled only by the authorized outer reviewers.

Rollback needs a fresh pair with action=rollback, the same original transaction and recipe, and current valid holder/expiry. It does not accept a changed boot. Before starting, reserve the full600 seconds for this independent rollback action. Retained unknown audit files are a nonzero unresolved result, not permission to delete them.
