# T51 preparation — waiting for accepted T50 sources

**PREPARATION ONLY. No T50 candidate was read or copied, and no candidate package was generated.** The external acceptance and final source hashes remain pending. This is not T51 completion, deployment admission or a signed maintenance plan.

The local builder/checker derive from the accepted T47 implementation. `inputs/reuse.json` records donor hashes, source main commit and the T51 contract hash. Old cards were not edited. The source lock is located under this T51 CARD and requires its own schema plus accepted-source state; a T47-shaped lock cannot pass, even with a different --sources directory.

## Inputs already prepared

- Nine public historical controls copied byte-for-byte from T47 baseline; original mode/UID/GID/dev/inode/mtime references remain in `inputs/preimage-inputs.json`.
- T46-P2 complete13-member records and outer read-only acceptance copied under `inputs/`. Their SHA/mode entries must match the original member table. This binds historical records, not a new device read or fresh runtime state.
- The nine non-control member byte files are not duplicated here. Their13-member historical record coverage is separate from the nine public control preimages. No extra replacement targets are introduced.
- Fixed root, six output names, unchanged boot-entry/config/init, disabled startup and exact rollback generation remain the T47 behavior. The final source/entry/member/startup/expected chain will be generated only after acceptance.

## Fields still required

`inputs/source-lock.json` intentionally has `status=PENDING_OUTER_ACCEPTANCE`, null T50 commit/acceptance, and empty sources/provenance. Await the outer's explicit acceptance before filling:

1. Final40-hex T50 source commit and exact watchdog/owner bytes, sizes, SHA256 and Git blob IDs. An unchanged owner must still be explicitly pinned.
2. Source/patch provenance and exact assembly/validation recipe evidence.
3. Persistent original execution-log index, its SHA and source paths.
4. Actual outer acceptance receipt path/hash, with no reinterpretation as device approval.

The final lock requires provenance roles `source_git`, `recipe`, `raw_execution_index`, and `outer_acceptance`, each referencing a file under this card's sources directory with SHA. These are pending binding slots, not fabricated receipts. Adapt the slots to actual accepted artifacts if required, while preserving pin checks. Nothing enables startup or reuses a historical signature.

## Checks performed and remaining

The actual preparation check returned rc0: all9 controls rehashed;13 historical member records matched; original startup/member/expected chain matched; Python files parsed. Actual builder invocations rejected pending acceptance (rc2) and a T47-shaped lock (rc2), with no output package. Logs were written before/during execution under `.private/preparation-driver-01/` and `.private/preparation-01/`.

The full checker is prepared to invoke two real builds, compare candidate/rollback bytes, verify the exact chain, and reject wrong source, wrong preimage, mixed lock, existing output, executable startup grammar and optimized Python. **It and the new Rust selector have not been run**, because accepted T50 sources are absent. No full scenario PASS is claimed. The full checker deliberately refuses while this lock is pending.

Preparation-only reproduction:

```sh
CARD=benchmark/2026-10-22-toutiao-owned-exit-fix-package
python3 "$CARD/prepare_check.py" --out "$CARD/.private/preparation-next"
```

After explicit outer source acceptance and exact local binding, the local command forms will be:

```sh
python3 "$CARD/build.py" --inputs "$CARD/inputs/preimage-inputs.json" --bytes "$CARD/baseline" --sources "$CARD/sources" --out "$CARD/package-01"
python3 "$CARD/check.py" --out "$CARD/.private/check-01"
```

These are not deployment commands. Every output must be new. `check.logged` retains actual argv/start/stdout/stderr/rc/end. No device, remote, VM, startup enablement, process-control, commit or push occurred; `author_commit=null`. Next window still needs fresh admission. No T50 acceptance or68-execution validation is claimed by this preparation.
