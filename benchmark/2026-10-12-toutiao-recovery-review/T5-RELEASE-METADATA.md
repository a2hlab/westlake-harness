# Metadata-only release check: 9436ed64 closure

The bounded observation ran from 2026-10-12T20:26:07+08:00 through
2026-10-12T20:31:07+08:00, polling the t0 package Git history every ten seconds.
No package commit after `b093d8599aeffac5e4830bd2dc7f6c15806b8a28` appeared.
Editing files and untracked lifecycle outputs were not used as approval objects.
No logic-family test or candidate execution was repeated.

`check_t5_release_metadata.py` is ready. It reads only immutable Git blobs,
requires a full descendant commit, and compares executor, prepare.py, every
payload member, modes, code additions, complete declared manifest hashes/sizes,
and plan-member SHA bindings. Other new/changed code is explicitly listed and
blocks silent inheritance. The plan must retain its reviewed semantics and
remain disabled. A known-stale b093 run correctly exits 2: eleven manifest
mismatches and two omitted code files. This is a checker known answer, not a
new release rejection or rerun of executor behavior.

```sh
python3 benchmark/2026-10-12-toutiao-recovery-review/check_t5_release_metadata.py \
  --commit FULL_NEW_RELEASE_COMMIT \
  --out benchmark/2026-10-12-toutiao-recovery-review/.artifacts/NEW_UNIQUE_METADATA_RECEIPT.json
```

No offline deployment-admission recommendation is issued without that commit.
If the metadata check passes, the recommendation is limited to inheritance of
the already reviewed b093 logic and outer-controlled admission checks, not an
authorization, successful board installation, autonomous reboot/UI, or sealing.
The outer's real b093 preimage PASS is not reused for changed bytes. Plan-2 is
still 61b's 20 keys plus the existing 5cd 128-key cross-check.

The known-stale receipt and original output are retained under
`.artifacts/metadata-known-stale-b093*`. Zero board, VM, remote, deployment,
permission, stop, user-data, signature, build, or push operations occurred.

## Final immutable release: offline inheritance PASS

The supplied release is `9436ed64b694d222ed4fa952dd0a5126df3ec4ce`.
The metadata checker executes no candidate code. Its fresh final output is:

```text
{"commit": "9436ed64b694d222ed4fa952dd0a5126df3ec4ce", "protected": 25, "manifest": 78, "plan_members": 23, "final_manifest": 79, "code_changes": 0, "failures": [], "exit": 0}
```

- Executor, prepare.py and every payload file: **25/25 byte and Git-mode
  identical** to reviewed b093; no new or removed payload member.
- Checkpoint manifest: **78/78** actual Git bytes/sizes match. The previously
  omitted bounded helper and CFG tests are now included. Manifest SHA:
  `740182144fed46dc45110eddb0c8addfe0c08bd6e884735bd64a42a2cb59eae1`.
- Final manifest: **79/79** actual Git bytes/sizes match, including the new
  checkpoint manifest; `program_commit` is exactly b093. Final manifest SHA:
  `9bb6374c3df12130500e4d5ca7c54ba161d3548135deee0fc742e78b5ac490f7`.
- All **23/23 placement-member** digests match frozen payload bytes. Plan
  semantics are identical to b093 and execution remains false. Plan SHA:
  `f7dfdd5daf91df1e4afb34fc3357e0386404a05b0564b1a873d01e402c5c88e0`.
- Executor SHA remains
  `430fbf4a6348dc12ef107c4786a16de83c06a99330cd527c5dbbbc6aca44f30a`.

## Separate static review: Rust wrapper, not hidden code inheritance

The only external code change is
`tools/spec-checks/tests/recovery_executor.rs`, SHA
`9ad762e1af30d0031abe6e1116fb35a73dd2946521bc7b159e51f505b4be260e`.
Line-by-line review confirms:

1. The shared `run` function, repository-root calculation, Python invocation,
   exit assertion and all four Rust test-selector names are unchanged.
2. `recovery_executor_plan` additionally invokes the existing `CFGTests`.
3. `recovery_executor_reject` additionally invokes existing `FailureTests`
   and `StopTests`.
4. `recovery_executor_format` and `recovery_executor_autoboot` are unchanged.

Those Python test bodies already exist unchanged in b093. This is wider test
coverage/contract wiring, not executor or deployment behavior. The exact Rust
blob is independently accepted for static wiring only and pinned explicitly
in the checker; any different external code remains rejected. No logic test
was rerun, and no new test-PASS claim is made here.

The initial strict run exited 2 because it flagged this unreviewed external
wrapper and incorrectly treated the permitted external manifest path as unsafe.
That original refusal is retained at `.artifacts/metadata-release-9436ed64*`.
After the explicit Rust review and correction of that checker path assumption,
the fresh final receipt is
`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-12-toutiao-recovery-review/.artifacts/metadata-release-9436ed64-final.json`;
original stdout/stderr are adjacent `.stdout.txt`/`.stderr.txt` files.

**Recommendation:** the metadata blocker is closed. Release 9436 may inherit
the b093 independent offline logic review and proceed to the outer-controlled
admission/deployment window using this exact new release and manifest. This
is not a board authorization, automatic deployment, fresh-boot/UI/interaction
acceptance, or seal signature. The outer retains fresh preboot/boot/expiry,
permissions, actual placement and guardian control, one-reboot acceptance,
and Plan-2 (61b 20 keys + existing 5cd 128 reference). No old manifest is used.
