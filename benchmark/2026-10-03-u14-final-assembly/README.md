# U14 single-batch offline assembly — disabled, review required

Previously, an unpromoted content comparison bundle was mistaken for a transaction
baseline. This assembly keeps those roles separate: comparisons use accepted U13
`91272eaf`; transaction identity is an explicit parameter. The current diagnostic
binding is real U10.1T8 `190afedd`, **not an assertion that U13 has been promoted**.
After promotion, re-finalize metadata against the signed per-board effective U13
base, including 61b's local installer references. No native output was rebuilt.

## Exact composed identity

| Item | SHA-256 |
| --- | --- |
| Disabled bundle | `93bb674a64e0ca5290b9dfe17eb6761107a5d7a85c21a7a2a5d44cd91c53da53` |
| Native manifest | `5b6fb28917f61b97d52bec976c446f034123c4a0e53f140d4cfaaaa0d4e70c25` |
| Native gate inputs | `0292444910e5be80926d8f86393bfbdad17408c72fd67c8f4f87ec238de9f4f2` |

Persistent output:
`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u14-final-assembly/.artifacts/bundle`.
`final-composition.json` binds the actual paired receipt and board fingerprint
tables. Native manifest, inputs and source profiles are snapshotted in `manifests/`.
Large ELF/JAR/image files and untouched native sidecar system providers remain
persistent outside the public listing, with exact hashes in the package.

| Component | Selected bytes | Scope |
| --- | --- | --- |
| Bridge | `7daa5435` | R1/R2/R3 + M5/M6, replacing `84695d62` |
| Stock host | `341c1260` | Replaces `2a87118e`; source is donor patched host + its two headers |
| Flutter libandroid | `fff9be31` | Only `westlake_flutter/libandroid.so`; root and other private alias retained |
| Gecko native ABI | `7605812c` | Only `westlake_native/libwestlake_native_abi.so`; root/Flutter `d205` retained |
| ICU | `9b36b989` + `4886bc5c` | Existing libicuuc `.so`/`.z.so` move together; one new shim |
| Runtime JAR | `0349eb83` | Native underlay and framework overlay, non-BCP |
| Stubs | `87cf65cc` | Native underlay and effective BCP overlay |
| Boot group | Actual hw248 run1 | All 27 copied atomically; 19 SHA changes versus U13, eight unchanged |

The earlier partial native/JAR staging has no `bundle.json`, boot-group descriptor
or old paired receipt. Its historical native image underlay was inventory-only.
It is never a deployable new-stubs/old-images package. The final assembly replaces
both native image underlays and boot overlays with the actual U14 image group.

## Actual build and paired receipt

`receipt.py` verified **131/131 incoming release inventory hashes**, both actual
nine-JAR maps, exact same compiler argv and host dependency inventory, frozen
compiler `ae865ddd` and driver `14b1f709`, and the authorized wrapper delta:
`36a0fff0` → `cd1393fc` (real host guard plus explicit lab HOME only).

Both runs: compiler/tee/session-tee/script **0/0/0/0**; frozen driver **6/6**.
Driver 6 is the old-reference mismatch, not a PASS. `receipts/paired-run{1,2}.json`
bind actual argv, tools, live compiler/session log SHA and exit codes. Full
unredacted argv/logs persist in `.artifacts/receipts/` and the incoming release;
public copies use portable lab paths and retain original raw SHA separately.

**Verified build execution is not exact-byte reproduction approval.** Two bakes
match 26/27. `boot.art` differs at `0x3e3b9` and `0x3e3ba`, within historical
`[0x3e3b8,0x3e3c0)`. Fresh frozen oatdump **now verifies both new object chains**:
`PendingFuture.CANCELLED → CancellationException.backtrace → Object[2] → long[2]`.
Full 156,090,590-byte log hashes and exit 0 are checked in `object-proof.json`;
line-numbered small excerpts are listed, large logs remain persistent. Method
words are `0x4066ba28` and `0x40df4a28`, with second element (dex PC) 2 in both.
This establishes ownership, **not runtime harmlessness**.
`image-exception-draft.json` binds the exact new input/output pairs and remains
proposed/unapproved. Old T7d/U12 provenance exceptions are not applied. See
`reproduction-review.json`, not a masked-image equality claim.

## Fresh Mac gates against U13

| Gate | Actual result |
| --- | --- |
| Native baseline | PASS, N1 55 + N2 104 excepted |
| Native candidate | REJECT, N1 99 + N2 105, no invalid-input errors |
| Auto-identical preview | 159 old findings, unapplied |
| New review | **N1 44, N2 one** |
| Production static comparison | REJECT: two JARs, one new native admission, four open/namespace pairs |
| ABI/calls, 219 consumer set for each replaced distinct ELF | All removed/drift/consumer-break counts zero |
| RB | exit 0 |
| T4b | exit 0 with actual U14 boot.oat-bound BUILD receipt |
| Frozen package | exit 0; only two artifact entries checked, not FZ-005 replacement approval |
| G1/G2, production replay, VM | Not run locally; deferred to outer after U13 window |

N1 adds 39 previously covered bridge/M6 uncertainties and five Flutter NOLOAD
uncertainties. N2's new issue is Flutter `libandroid.so → libc++.so`: factory bytes
exist outside the private search/permitted domain; this gate deliberately does
not traverse inherit. It remains a rejection, not a claim of a new second owner.
`needs-outer-review.json` includes the raw finding and search paths.

All newly introduced **strong** imports have a byte exporter in a direct NEEDED
provider. Unmatched weak imports are separately labelled: Gecko's optional
`__loader_android_dlopen_ext` and the new ICU shim's weak compiler-runtime hooks.
This export intersection does not prove live namespace visibility. The bridge's
35 ordered NEEDED entries are unchanged; `SetSubWindowZLevel` is exported by the
pinned `libwindow_scene_common.z.so` direct provider. See `imports.json`.

| ELF pair | Open sites old → new | Namespace edges old → new | Raw strings dropped / added |
| --- | ---: | ---: | ---: |
| Bridge | 3 → 3 | 0 → 0 | 9 / 33 |
| Host | 8 → 8 | 17 → 17 | 2 / 4 |
| Flutter libandroid | 0 → 7 | 0 → 0 | 1 / 22 |
| Gecko native ABI | 0 → 2 | 0 → 0 | 0 / 7 |
| ICU pair | 1 → 1 | 0 → 0 | 0 / 0 |
| New ICU shim | none → 0 | none → 0 | No fabricated old ELF comparison |

Original `DEFAULT-NS`, `UNRESOLVED`, `MULTI-NS` and may-path diagnostics remain in
the raw open evidence. Host keeps 17 edges, zero INHERIT-REPEAT and four old
INHERIT-AFTER-OPEN may-paths. The production bridge delta is
`87ed7281bbc4375ec5fa65ec42767a38205680aade4538ff84800fa5c915fbea`;
the previously archived ADR literal proof is in
`benchmark/2026-10-03-u14-native-assembly/adr-proof.json` and is not an approval.

ABI call-set changes: three bridge functions (display width, createSession,
ScheduleAbilityTransaction), one Gecko `__emutls_unregister_key`; host/ICU and
existing Flutter functions have zero call-set changes. Added exports are
bridge +4, Flutter +4, Gecko +10. Calls of new functions are not an old-body parity
claim. The consumer set is an import intersection, not 219 working apps.

JAR raw `--frozen`: runtime **0 drop / 0 reshape / 3 add**; stubs **0/0/2**.
Neither addition set is silently allowed. All raw statuses and production
schema deltas appear in `report-summary.json` and `evidence/static-vs-u13.json`.
`static-allowance-draft.json`, `new-native-admissions-draft.json` and
`registry-delta.json` are previews only; active registries were not changed.

The first T4b attempt incorrectly retained the old U12 OAT identity and rejected
that mismatch; a second attempt also refused an existing output path. Both raw
failures remain as evidence. The final fresh unique-output run uses `inputs/U14-BUILD.md`:
the immutable compiler build environment is unchanged, only actual OAT identity
is rebound. No libart build or switch was invented to make the gate pass.

## Replay and landing

`compose.py` stages verified native/JAR bytes; `receipt.py` consumes actual bake
evidence; `object_proof.py` validates the incoming fresh dump and makes the exact
paired-byte exception proposal; `finalize.py` requires `--transaction-base`, its full SHA and signed
`--board-baseline`, with optional `--reference-board` for a per-board metadata
variant. Each output directory must be new. Rebinding changes metadata only,
never native bytes. `reports.py` compares with U13 independently of that parameter.

`replay-production.sh` exits **78** by default, before any VM/device action. Only
outer may invoke it after the window, on the selected OS, with
`U14_PRODUCTION_REPLAY=outer-approved-after-window` and positional
`mac|vm BASE BASE_SHA PACKAGE`. It checks the effective baseline binding first
and calls only `u7_executor --dry-run`. The present packet is expected to reject
unapproved rows; no historical production PASS is borrowed.

Tests are cold-safe: 12 Python checks and two Rust selectors require only listed
source/JSON evidence, not `.artifacts`, foreign worktrees or donor binaries.
Both task lifecycles pass three scenarios each. The landing listing and
preflight output are supplied separately; outer owns approval/commit/deployment.
