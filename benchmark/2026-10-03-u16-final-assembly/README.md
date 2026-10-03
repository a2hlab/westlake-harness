# U16 actual bake receipts and disabled content assembly

## Correction / evidence first

`verify-return rc0` proves transport completeness, not reproducibility, image
compatibility or a promoted BASE. The new pair is **26/27 byte-identical**;
boot.art differs at three bytes. A matching byte interval does not authorize
reuse of U14's exception. Actual object-chain evidence and an exact new
input/output approval are still pending. No board, lock, VM, SSH, build or
gate-table write was performed by this lane.

## Incoming pair

Persistent source:
`$WORKSPACES/westlake-inputs/generations/u16-bt-bake-8593-f6f5-v3-20261003T162410-42707/`.
All86 `SHA256SUMS` entries independently verified; inventory SHA is
`2a0964267e6aa46b23cc872d883bc961c8daa7a5d08fa842dfa40dc4f35a1d31`.
All14 original handoff members match; nine JARs and frozen host-library hashes
match the reviewed input snapshots. Both live compiler logs contain exactly
the recorded argv, also equal to the expanded planned argv for this attempt.
Two runs share the same work path; each has independent session/log hashes.

`receipts/paired-run{1,2}.json` bind nine inputs,27 outputs, actual command,
frozen dex2oat ae865ddd/driver14b1, toolchain identity, complete compiler and
session logs, log SHA and statuses. Compiler/tee/session/script are all0 in
both runs. Frozen driver rc6 is its comparison against old U15 image hashes,
not compiler failure or paired-reproduction acceptance. Full unchanged raw
stdout+stderr remains in the persistent incoming `logs/`; portable copies
are `evidence/build/`. Run1 is selected for disabled review only.

### New boot.art exception, not historical transfer

|Run|boot.art SHA256|64-bit word at0x3e3b8|next word|
|---|---|---|---|
|1|`af0a1b17b455c1fa7736f8b90073c4b17192541abb44b014ffd73b25ffb44e43`|`0x60bcea28`|2|
|2|`46a2e9a17188593cb6807ee353232435eb06f43488abf23918c0192b105f7bd6`|`0x4025fa28`|2|

Both4644864 bytes; delta at0x3e3b9/ba/bb, within[0x3e3b8,0x3e3c0).
U14's signed field is PendingFuture.CANCELLED → CancellationException →
backtrace Object[2] → long[2] element0. This new pair has not yet proved that
chain. `image-exception-draft.json` pins the full nine-input map, both full
output hashes, exact offsets and U14 precedent SHA, with `not_transferred=true`.
Do not infer the object's type or approve nondeterminism from the offset alone.

## Single disabled U16 content version

|Profile|Bundle SHA256|Content comparison|
|---|---|---|
|common|`ed9447a958a8afe5d54348e29df6e4cf2d2f3ae16ce2f611ff326bf900c02b31`|U15 common29c8a62c|
|61b|`ffe5dd537ccac49dd9ab92c7df2159b70589bc32a7f4fddcefe0737a56c4375c`|U15 61b8a260cec|

Persistent review candidates are `.artifacts/{common,61b}` in this lane.
Components: runtime1d42dbfb, Fluttereb90a640 (not withdrawn15e988), stubs85938130,
runtime JARf6f5face, all27 run1 images. Exactly23 effective paths change:
two native + two JAR +19 images; all27 boot overlays and native underlays
are rebound together. All other U15 artifacts, host/ANL and the private
westlake_native/libandroid stay unchanged. common2c9a/61b51e1 installers remain
board-local. Both profiles have the same native manifest/inputs identity.

All execution/rollout flags false. Transaction BASE is null until U15 promotion;
U15 candidates are content comparisons, not actual resident baselines. Fresh
reference/image-gate-reference metadata describes U15 content, not inherited
U14. Neither U15 policy allowlists nor image exception approval are copied into
this candidate. Verified compiler receipt does not prove accepted26/27 pair.

## Fresh Mac gates (both profiles)

|Check|Raw exit|Result|
|---|---:|---|
|RB|0|Read barrier image/header consistency|
|T4B original BUILD binding|2|Original BUILD's old boot.oat SHA differs; original report retained|
|T4B new derived frozen-output binding|0|Same libart/frozen compiler environment, actual U16 boot.oat SHA|
|N1/N2 active table|1|103/105 rejected,0 excepted, errors[];208 new final-binding rows unsigned preview|
|Static full|2|stubs eight exact additions require allow_add; Flutter new delta requires exact binding|
|G1/G2 aggregate|1|G1 true; G2 required but no oatdump, false—not PASS|

`receipts/U16-BUILD-snapshot.md` explicitly derives the new output binding
from original BUILD's unchanged compiler environment; it does not claim a new
compiler build. Original T4B SHA mismatch is archived, not hidden. Fresh output
in `validation/gates-mac.txt`, `evidence/{common,61b}/darwin-*`,
`fresh-gates-summary.json`; raw logs remain privately with hashes.

Static details: runtime1d42 raw PASS deltaa79aabf8, runtime JAR224/224 raw PASS;
Flutter REVIEW_REQUIRED delta190c0607. Stubs276→284,0 dropped/0 reshaped/8 added,
frozen0. Exact descriptors are in the original stubs row in `static-report.json`.
Native208-row `registry-preview.json` is **unsigned and unapplied**. The signed
U16 seventeen-row source/open/callset scope is not itself a final-manifest grant;
outer must review/transfer each binding. No registry or static-policy widening here.

## Outer execution commands (never run by this lane)

First collect the **new pair**'s object chain using frozen oatdump's full SHA,
two sequential runs and complete stdout+stderr tee. Script validates the sealed
incoming inventory on hw248, creates a fresh timestamped evidence directory,
keeps full large logs there and emits hashes/statuses/small excerpts.

```sh
ssh hw248 "LAB_HOME=/home/alvin U16_OUTER_REPLAY=outer-approved bash -s" < "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u16-final-assembly/dump-object-chain-hw248.sh"
```

Return the emitted directory's excerpt/status/argv/SHA256SUMS and persistent
full-log location. Then prove the entire object chain and request an exact
U16 exception; absence/another object/out-of-field delta stops acceptance.

G1/G2 with the real remote wrapper, current two disabled packages, exact U15
content reference (not a production transaction authorization):

```sh
U16_OUTER_REPLAY=outer-approved LAB_HOME=/home/alvin bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u16-final-assembly/replay-outer.sh" g2-mac
U16_OUTER_REPLAY=outer-approved LAB_HOME=/home/alvin bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u16-final-assembly/replay-outer.sh" g2-vm
```

The second command runs in the outer's Linux VM only when rollback/window work
allows. VM branch adds `.vm-tools` to PATH and uses shared TMPDIR plus MAC_HOME.
Each invocation has a new immutable output directory and records gate/tee RCs.
No executor apply, lock or device command occurs. Default shell entries exit78.
Actual future production dry-run requires promotion BASE rebind and the pending
native/JAR/pair admissions; do not use this image-only check as production PASS.

## Offline reproduction

```sh
python3 benchmark/2026-10-03-u16-final-assembly/prepare.py
python3 benchmark/2026-10-03-u16-final-assembly/test_receipt.py
```

`prepare.py --compose` creates immutable fresh content candidates once; do not
overwrite existing review outputs. Tests use committed receipts/metadata only,
not binary `.artifacts`. Source recipe/snapshots/build tee provenance remain in
the previously landed U16 draft, bake handoff and persistent incoming inventory.
