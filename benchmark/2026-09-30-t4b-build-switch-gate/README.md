# T4b: native / OAT / build-receipt consistency

The earlier assumption was that matching layouts, image/OAT versions, or ART's
own loader would stop an incompatible image. Outer-reviewed T6 instead observed
SIGILL with the RB-on T5 image and recovery with v3c. This check independently
compares the read-barrier state before any board command. **Known disagreement
is a hard failure; missing build history stays unknown.** It does not replace
the original T4 layout check or T6 visual acceptance.

## Actual controls

| Input | Primary OAT SHA256 | Known consistency | Strict verdict / exit |
|---|---|---|---|
| v3c | `25d92cf7df9c86ca4bbc81c1e2f44a5c6c64798506247239e07a30f651b9e78c` | pass: RB=false matches R155 | pending_review / 3: historical BUILD.md absent |
| T5 | `08837079ac97bbec25a804fc1916e5973911b8dd58733a57f8e5f52d5c9da6c9` | fail: RB=true versus R155 false | fail / 2, even with missing receipt fields |
| T5b | `90f827190482b849f71bceb9ab3d2482c8b42adf70b8b084af887728cb43f248` | pass: 7 comparisons, RB=false and five BUILD settings match | pending_review / 3: four receipt gaps |

All three use actual R155 libart
`59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f`,
read from the local v3c payload. Eight instruction ranges plus the decoded
`VMRuntime_vmLibrary` string substantiate RB=false, CMS, generational CC=false,
heap poisoning=false and native release. `ART_TEST_DEBUG_GC=false` is derived
from the observed CMS default and r1's SS override rule. The extractor applies
only to this full library SHA; another library becomes unknown, never R155 by
filename or available collector symbols.

The native predicates and source interpretation are retained in
`../2026-09-30-t5-oat-attribution/{libart-evidence.json,build-flags.json,source-evidence.json}`.
This task rechecks the binary bytes; it does not merely trust that JSON's values.

v3c is the positive **known-consistency** control. It cannot honestly be a
complete three-way historical-build proof: its SHA-bound build receipt was not retained.
An explicit synthetic complete receipt exercises exit 0 in tests, is labelled
`synthetic_fixture`, and has `deploy_allowed=false`. It is not a reconstruction
of v3c's original BUILD.md. Actual v3c and T5 each have nine missing-receipt
exceptions, listed separately from the known mismatch. No automatic waiver is
provided. The outer reviewer owns any baseline exception.

## CLI and receipt

From the repository root, with `WORKSPACES` pointing to the shared workspace:

```sh
python3 knowledge/toolchains/art-r155/t4b_build_switch_gate.py \
  --libart "$WORKSPACES/westlake-generation-v3c-candidate/payload/android/lib64/libart.so" \
  --oat "$WORKSPACES/_hw248-t5/arm64/boot.oat" \
  --build benchmark/2026-09-30-t4b-build-switch-gate/evidence/T3-BUILD.md \
  --out /tmp/t4b-t5-new-report.json
```

The last argument must be a new path. JSON on stdout and in the output file is
identical. Exit 0 means this consistency gate passed, 2 means a known conflict or
invalid input, and 3 means unknown requiring outer review. Consumers must check
`verdict`, `deploy_allowed`, and its scope, **not just `consistency`**. Even a
complete T4b pass still needs the separate layout and board gates.

`BUILD.template.md` specifies one `t4b-build-json` block, full runtime-library
and candidate-OAT hashes, and explicit build settings. The library hash binds
the **runtime to deploy against**, not an unrelated newly built target library.
Keep actual host dex2oat/dependency hashes, compiler evidence, logs and complete
environment (including ALLOW_MISSING_DEPENDENCIES) alongside it. The record must
be made by the builder, not retrospectively filled from the desired answer.
The gate checks declarations for consistency; a matching declaration alone is
not proof that the compiler consumed those options.

For old unstructured documents only assignments inside shell code fences are
considered. Inline prose such as “ART_USE_READ_BARRIER=1 occurs zero times in
ninja” is not an environment assignment. Conflicting code-block declarations
are refused. Mixing multiple generations in one unstructured document cannot
produce a hash-bound pass. A receipt is never executed as shell code.

KV reading reuses cc-wiki's `check_boot_oat_rb.read_kv` from `785fdaf1b`, copied
without changes. Its first-400KB key search is cross-checked with the existing
T5 `compare_oat.parse` bounded ELF64/AArch64 OAT230 validator; duplicate keys,
malformed offsets or a key-like string outside the real KV store are refused.
No second new KV decoder was written. Only `concurrent-copying` measures image RB state.
The primary OAT's GC/default-generational/heap-poisoning/native-build-mode fields
are **not encoded**, rather than silently assumed equal. `debuggable` and
`native-debuggable` remain AOT properties, not evidence of native NDEBUG.
No invented `bootclasspath-checksums` or `compilation-reason` is required.

## Provenance and replay

`evidence/T3-BUILD.md` is the original T3 file from commit `8f7fc4f85`, SHA256
`22b44304117f69b693492c269acb41753fb8757fe479279b982e891443f43a21`.
It has neither the five switch declarations nor full artifact hashes. The
separately retained `T3b-BUILD-worktree-snapshot.md` was captured while the outer
worktree already contained an uncommitted T3b update; it must not be attributed
to T5. The mutable shared document changed during this task, so the T5 replay
uses the commit-pinned original, not whichever BUILD.md happens to exist later.

At 22:31 the outer loop located an author recipe (host Soong RB-off/CMS and a
separate device cross-compile script); cc-wiki is archiving it. A recovered
source recipe is useful independent evidence, but is not a SHA-bound receipt
of the historical v3c build. This gate does not automatically waive that gap.

```sh
python3 benchmark/2026-09-30-t4b-build-switch-gate/replay.py \
  --workspaces "$WORKSPACES" --include-t5b --out /tmp/t4b-replay-new
python3 benchmark/2026-09-30-t4b-build-switch-gate/test_gate.py -v
agent-spec lint specs/dex2oat-once/t4-layout-gate.spec.md --min-score 0.7
agent-spec lifecycle specs/dex2oat-once/t4-layout-gate.spec.md \
  --code tools/spec-checks --format json
```

23 tests cover actual artifacts, each required mismatch/missing field, native
debug versus OAT debug, malformed/duplicate receipts, artifact identity,
unknown libraries, missing OAT keys, JSON output and input protection. Five
new Rust selectors pass. The existing `d4_mirror_layouts_match_board` selector
still matches zero tests: full T4 lifecycle therefore remains **5 pass / 1
skip**, not green. That original obligation is preserved.

T5b was reported ready at 22:28 CST; SSH was denied and no Mac copy was present
at 22:30. At 22:36 the local `_hw248-t5b` copy arrived and all 27 files matched
the delivered manifest (run from `arm64`, as manifest names have no directory
prefix). The final BUILD snapshot SHA is
`0ac3e43c1a876410a7a141a765299196643d2e7237b26f7d107228c82a8bff92`.
It is byte-identical to `a9ca66df9:knowledge/toolchains/art-r155/BUILD.md`.
Seven comparisons pass. Four gaps remain: no structured artifact-bound receipt,
no explicit runtime libart SHA, no explicit candidate OAT SHA, and no explicit
native release declaration. Artifact transfer hashes are verified independently;
they do not invent a builder's receipt. See `observed-final/` for all three
controls and their exception table; `observed/` retains the earlier two-control
run. No board commands, runtime changes or image rewriting were performed.
TLAB/interpreter/sanitizer/optimization recovery and all-nine-image semantic
coherence remain outside this four-switch gate.
