# Pre-land complete runtime input prerequisite

The second landing invoked the original eight-test file directly. It did not run
the clean-landing reproducer, so the first missing runtime object was appspawn-x.
This independent addendum changes no prior freeze, provider or test. It supplies
only a local input hydrator; it never invokes Git, a device or a production lock.

## Required landing sequence

The receiving main tree successfully landed the 60-file supplement at commit
`34e9018091`; outer reported the original eight tests PASS. Before that landing,
outer checked every runtime row against exact manifest
`0c5da8dadaec9e6fc4969d06f884b6204ce5601297f18f76b25fc0407f0d8ab5` and hydrated
**all 463 runtime inputs, 769937330 bytes**, from the verified producer package.
Those files are local untracked test inputs; no runtime binaries were committed.
This acceptance report is supplied by outer, independently of our clean replay.

For each future sparse landing that runs the original test entry:

1. Obtain the exact pinned package locally, or reproduce it with
   `landing-repair/replay_clean_landing.py` into a new temporary directory.
2. Verify the source manifest SHA and **every** declared `runtime/` file's SHA and
   byte count. Hydrate all 463 rows and their parent directories locally into the
   receiving `package-r3-disabled/runtime/`, skipping only equal verified files.
   Do not overwrite mismatches or use directory existence as completeness proof.
3. Recheck the destination against all 463 manifest rows, then run the original
   landing/test command. Copy only the explicit small-file landing list into Git.

The local source can be the clean replay's `rebuilt-from-pinned-inputs` directory.
Its manifest must still match the exact frozen v5 SHA above. The clean replay
remains separate evidence: it creates its own empty tree, reconstructs inputs,
and runs the unchanged tests; it does not hydrate the receiving checkout for an
outer land command. These two entry points have different input preparation.

## Optional single-object repair only

`hydrate_appspawn.py` remains available for an individually missing appspawn-x.
It is **not** the complete land prerequisite. Run it from a checkout holding this
addendum and the frozen adjacent v5 metadata:

```sh
python3 benchmark/2026-10-12-v1-seal-assembly/restore-v5/landing-hydration/hydrate_appspawn.py \
  --workspaces "$WORKSPACES" \
  --target-package "$WORKSPACES/westlake-harness/benchmark/2026-10-12-v1-seal-assembly/restore-v5/package-r3-disabled"
```

Exact source: `$WORKSPACES/westlake-inputs/seal-artifacts-20261012/sha256/a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c`.
Bytes: **257792**. SHA256:
`a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c`.
This is independently present in the frozen v5 manifest (SHA `0c5da8da…`)
and its typed extra-runtime source in the binding (SHA `a1739d72…`), from the
captured closure index (SHA `d7fcc146e0eb9b3e3cbcaa8154a5c453ac787a09f956b267deb655cb78ec7579`).
The tool verifies the complete manifest/binding pins and CAS bytes before copying.
An equal existing input is skipped; a drifted input is refused without overwrite.

The copied runtime object is a local test input only. It is deliberately absent
from every supplement landing list. Do not git-add or package the runtime tree.

**Scope limitation:** the frozen hash-chain test iterates all 463 runtime files,
and appspawn-x is the first runtime row. A single first error does not establish
that the other 462 files exist. The tool reports `runtime_missing_after` and the
first missing names; its success means only the requested appspawn object is
present and exact. It does not claim eight-test success or validate other objects.
If the receiver still lacks runtime files, the auto-test prerequisite remains
incomplete: use the previous `landing-repair/replay_clean_landing.py` entry, which
rebuilds all runtime in a temporary directory, or have the outer wrapper hydrate
its local inputs from that exact-manifest rebuild before calling the original
suite. No large runtime belongs in the Git landing.

Validation here uses a fresh temporary target and the actual CAS: first copy and
idempotent equal-input skip, with source/destination SHA/size verified. It runs no
provider or transaction matrix and performs no writes in the receiving main tree.
