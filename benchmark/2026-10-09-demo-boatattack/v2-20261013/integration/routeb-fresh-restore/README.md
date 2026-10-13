# Current-prestate RouteB 487 recovery core

The old 43bc absent-directory recipe is not authority to replay the existing 362f state. This release binds the actual postarchive 497 capture, original R5 evidence and all 29 existing directory metadata/inodes. It performs all 487 placements with atomic sibling inode replacement and exact preimage CAS, preserving mapped old inodes and user data. Original executor/43bc proof/seal remain unchanged. Every before hash equals the corresponding restored hash; successful byte equality alone is not a placement receipt.

Independent T0 review accepted executor `3f176393a9388b85130084a3b2eabcb3221bdbf3cf72852aa2471d87a2ee35db` and prepare `38176fcc5e8bb66e86b7feae3bcddf080d4b68000fcf09df270065a22ee29019`, with 6/6 tests. Local 6/6 actual-plan recording tests also passed. These are offline tests, not board execution.

## Main-bound preparation (zero device calls)

Run from main after landing this exact list. Set WORKSPACES to the existing workspace parent. Do not execute the lane's historical generated example.

```sh
CORE=benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/routeb-fresh-restore
OUT=benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/routeb-fresh-restore-main
python3 "$CORE/prepare.py" --request "$CORE/request.5cd.disabled.json" --out "$OUT"
RECIPE_SHA=$(shasum -a 256 "$OUT/recipe.json" | cut -d ' ' -f1)
python3 "$CORE/executor.py" --recipe "$OUT/recipe.json" --recipe-sha256 "$RECIPE_SHA" --out "$OUT/transaction"
```

Expected preview: `DISABLED_CURRENT487_PREVIEW`, 487 members, 29 directories, zero device calls. The output directory must be fresh. Keep `plan.disabled.json` and recipe disabled and unsigned. Inputs already bind actual boot `362f2212-1a42-4c1a-8487-0dddb091c74b`. Any boot, source, directory inode or target drift rejects; do not patch around the gate.

## Independently approved execution

Use the existing outer board_run/lock window. This package does not acquire a lock. Fill the separate authorization and admission exactly as described in AUTHORIZATION.md; there are no signed examples in this release. Use the complete `board_note held` output line as holder, not its first token. Root retains responsibility for invoking rollback before the expiry.

```sh
AUTH=/path/to/current-apply-authorization.json
ADMISSION=/path/to/current-apply-admission.json
AUTH_SHA=$(shasum -a 256 "$AUTH" | cut -d ' ' -f1)
ADMISSION_SHA=$(shasum -a 256 "$ADMISSION" | cut -d ' ' -f1)
python3 "$CORE/executor.py" --recipe "$OUT/recipe.json" --recipe-sha256 "$RECIPE_SHA" \
  --authorization "$AUTH" --authorization-sha256 "$AUTH_SHA" \
  --admission "$ADMISSION" --admission-sha256 "$ADMISSION_SHA" \
  --out "$OUT/transaction" --action apply --execute
```

Apply succeeds only with rc0, `recipe-receipt.json` complete true, executor_rc0, placed_count487, the exact transaction and 487 placed receipt pins, final 487 probes, and `directory-complete.json` checking all 29 inodes/metadata. No Boat placement or reboot belongs in this window. Release this lock before the separate Boat window.

On failure preserve the entire transaction. Create separately approved action=rollback documents for the SAME recipe, plan, boot and transaction. Invoke the same command with their independently computed SHA values and `--action rollback --out "$OUT/transaction"`. Do not re-run apply into an existing transaction. Before==after makes the original verified rollback short path legitimate; known interrupted staging is retained with exact recorded observations. Unknown or changed staging returns nonzero and is not deleted. The core never treats retained stage files as restored runtime proof.

## Budget and evidence

Recorded real CLI shape: apply4566 HDC operations, rollback1035. At the prior 3539 calls/1183 seconds, apply estimates 25.44 minutes; +25% contingency +10-minute rollback reserve estimates 41.8 minutes. This is not a timing guarantee: transport/bandwidth and local backup hashing may vary. Both approval documents must set apply_deadline_epoch at least600 seconds before their expiry; maximum authority lifetime2700 seconds. Every per-member identity and atomic CAS enforces that deadline. Plan for immediate rollback on nonzero; do not use an external timeout that destroys transaction evidence. Existing transport records timeouts as rc124.

`results.json` pins the two larger synthetic command recordings kept locally for outer archive; they are excluded from this small landing. `evidence/tests-final.txt` contains the preserved completed 6-test output. The Rust selectors compile successfully; the full Python matrix was not repeated for packaging.

The separate downstream entry will admit THIS completed recipe/receipt before original R5 and Boat. It is not included in this core freeze. Postboot uses the already frozen f28 selfcheck entry, its parameter-observation pin, and the existing 62-target snapshot; no new collector is required.
