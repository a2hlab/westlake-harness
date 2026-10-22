# T51 — accepted owned-exit fix, disabled package

The T47 source lock could not authorize a different watchdog by changing --sources. This package uses its own **T51 lock**, the nine exact public historical control preimages,13 T46-P2 member records, and the outer-accepted T50 source at commit **53749c0ded3c320fc3b66c7d9a2efc140ceefe64**. Two actual fresh builds returned rc0; all six candidate and six rollback files are byte-identical across builds. The public package is an exact copy of those outputs. **STARTUP_ENABLED=0; rollout_ready=false.**

## Bound inputs and changes

- Accepted watchdog SHA `d45a8d36794d3927c0c03f19d71fa632a0b9cec18944d9d9f92a3406b49f64f0`.
- Accepted owner SHA `fc63dae9a24c4a41d1e8db92612cc256734c650e94451513b97f05226f82fe58` (unchanged relative to T50's T47 diagnostic baseline).
- Outer receipt SHA `0e7321f5fd61990f91373126cf53a007d548fd6579a8be77645c85984e5a2985` and upstream raw-index SHA `452d5dc473881f4d5c9affb7fb3ae1f7a43c709d2baac395b7bd58230e7b323d` match the explicit handoff.
- `bind_inputs.py` read17 files through `git show` from that exact commit, verified Git blobs and the four handed-off SHA pins, and preserved the pending lock. `inputs/accepted-source-index.json` records every original path, blob, size and SHA. The complete committed T50 source/patch/recipe/fixture/provenance snapshot is under `sources/t50/`; no T50 replay or runtime build was executed here.
- `inputs/source-lock.json` binds both source bytes and provenance roles, and checks the accepted receipt's candidate hashes. Source roots are local to this card. The baseline and `inputs/preimage-inputs.json` remain exact T47 historical controls. Member records/outer review are separately pinned historical T46-P2 evidence.

`build.py` changes exactly watchdog, owner, entry's two SHA literals, the three corresponding member hashes, startup's member hash and disabled flag, then the expected-file content. The ten other member lines and all modes remain unchanged. Rollback contains the original six bytes with original stat references. The unchanged boot-entry/config/init inputs are hashed in the receipt, not replaced. Root remains `/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012`; no boot directory, application data, stop, permission or lifecycle policy is changed by this local assembly.

All13 manifest members have historical T46-P2 SHA/mode records. Four are also among the public control preimages; the nine other member byte files are not duplicated. This distinction is recorded in the package receipt. All members still need next-window fresh admission. Historical approval text in baseline/candidate is not a new authorization; the candidate's startup remains disabled.

## Local reproduction

From the repository root, no private HOME input or network is needed:

```sh
CARD=benchmark/2026-10-22-toutiao-owned-exit-fix-package
python3 "$CARD/build.py" --inputs "$CARD/inputs/preimage-inputs.json" --bytes "$CARD/baseline" --sources "$CARD/sources" --out "$CARD/rebuild-01"
python3 "$CARD/check.py" --out "$CARD/.private/recheck-01"
CARGO_TARGET_DIR="$CARD/.private/cargo-target" cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test toutiao_owned_exit_fix_package -- --nocapture
```

Use a fresh output each time. `bind_inputs.py` is the original one-time source-intake recipe, not a required rebuild step; it refuses an already bound lock/populated source directory. `check.logged` writes argv/start before each command and streams stdout/stderr directly to durable files, then records rc/end. Optimized Python is refused; the checker invokes -O only as a negative rejection test, never a bypass. Input shell/config bytes are never sourced or executed.

## Actual validation

Seven bounded check groups passed: two real builds and exact chain; old output refusal with unchanged historical tree; wrong preimage SHA; wrong source SHA; the real T47 lock copied into a disposable card; actual startup parser rejection of executable syntax; optimized execution rejection. Rejected builds produced no package. The dedicated Rust target passed1/1,0 skipped and ran this T51 checker, not T47's checker. Original successful/rejected command streams are retained. No unrelated tests or T38 work were run. No full agent-spec lifecycle PASS is claimed.

Primary raw: `.private/bind-01/`, `.private/check-driver-01/`, `.private/check-01/{positive,repeat,existing-output,wrong-pin,wrong-source,mixed-lock,optimization-refusal}/`, `.private/rust-01/`, `.private/publish-01/`. Rust's additional two-build checker directory is retained as well. `raw-index.json` binds raw files excluding disposable Cargo/Python caches. Earlier pending-state checks remain in `.private/preparation-*`; preparation README/results/listing and pending lock remain explicitly historical. An initial patch-context failure is retained in `.private/edit-context-failure.txt`; it did not change source or produce a failed build.

`package-01/receipt.json` holds all six output/rollback SHAs and stat references. `landing-paths.txt` is the exact public listing; `SHA256SUMS` covers every listed file except itself. Device/remote/runtime-build/deployment actions0; no enabled bytes, new signature or maintenance runner. `author_commit=null`; no commit/push. Offline packaging is complete; device behavior and any white-screen improvement are not claimed.
