# U13 effective-baseline correction (offline, unarmed)

## What was wrong

The previous U13 `bd83d846` compared against unpromoted U12 `bf6c0fb6`.
Its Mac/VM PASS receipts were comparison receipts, not admission for a transaction
from the three boards' actual U10.1T8 state. The executor correctly refused before
LOCK. This correction preserves those old receipts and does not reinterpret them.

**Rule:** the effective baseline must match both the sealed bundle and the signed
full board identities/fingerprints. Native package underlays are not effective JARs
or boot images. A baseline change requires fresh transaction, open/string/class
comparisons, approval bindings and production replay; it is not a one-field bypass.

## Exact bindings

| Object | SHA256 |
|---|---|
| Actual U10.1T8 bundle | `190afedd3ddb250752e67b83d19669b6a952eb04cd69db5edf0b06eafe119736` |
| Actual native baseline | `4db327033870b597248a7188ab7f007e1979dafbb330edc58a4f052b6a086e00` |
| Old U13 comparison bundle | `bd83d846bc6c3a47a1a8e6431051d874d0cdd30db0687b3338ddd0f3fc61141d` |
| Corrected disabled bundle | `91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28` |
| Unchanged U13 native manifest | `85aef68eafbde98e6ac885264fe36f2f1e357618abf1d455de6ca15c0996cee6` |
| Unchanged U13 native inputs | `c40faa79d197f023dbe47a62ae186d5eb5671f9b8f4a448924098fdd5f02f185` |

Persistent disabled package:
`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4`.
Actual baseline: `$WORKSPACES/westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle`.

No native, JAR or boot output was rebuilt or changed. Host stays `2a87118e`, bridge
`84695d62`; McDonald's host `c2883376` remains excluded. Native manifest/inputs and
all 159 approved N1/N2 issue IDs are unchanged. Only bundle policy/reference
metadata and the readonly comparison copies change; old bundles remain intact.

## Real transaction and identities

- All three signed recovery snapshots match 316 unique paths / 318 assertions.
  Runtime: 5ea/5cd `f3b604c94df4`, 61b `d6848fa2c989`; boot `e3806b65a079`.
  The two libinstalls identities on 61b stay board-specific, not unified here.
- Runtime references now bind 123 actual resident paths (old generic reference
  covered 119); boot references bind 36. All 36 image-gate comparison members
  come from effective U10.1T8, not U9 or native payload underlays.
- The fresh transaction baseline matches all 316 signed 5ea paths, expected
  candidate matches all 319 previously composed paths; **3 additions, 40 staged
  changes**. The three additions are root mediandk and private libz/provider.
- There are 23 actual effective SHA differences: 11 image bytes differ, 2 JARs,
  9 shared libraries and the host. The stopped-parent transaction deliberately
  stages all 27 paired images, not just the 11 different images. No frozen image
  was rebuilt. Paired receipt is verified against the final nine BCP JARs and
  all 27 output hashes. Rollback must restore real U10.1T8 and remove the 3 additions.

## Fresh static evidence and exact transfers

`evidence/static-unapproved.json` preserves the initial REJECT. No new unmatched
open/namespace finding appeared. Host pair `65cc3535→2a87118e` retains reviewed
delta `f4254914`; both compat aliases retain `015aa3a6→b8a87f6f` / `ab8d10e3`.
ICU, policy aliases and runtime have no open/namespace delta. The full schema,
including namespace fields, is compared rather than a sites-only hash.

Real deployed JAR comparisons report **0 dropped / 0 reshaped**, stubs **1 added**,
runtime **19 added**. The 19 are the reviewed U12 additions plus U13 additions,
minus the defective anonymous Cipher absent from this true baseline. No U12-pair
`allow_drop` is copied to the different U10.1T8 pair.

Raw string checks remain exit 1: `strings-binding-review.json` lists all **31**
rows with paired SHA, reason and raw receipt. ICU's 5 drops / 4 adds and host's
source-path changes are not hidden; the exact approved objects are transferred,
not declared byte-equivalent to their older deployed objects.

Outer's 02:42:53 same-object rule authorizes these transfers.
`binding-transfer.json` maps each static member old→new bundle/manifest/baseline;
`image-binding-transfer.json` maps 27 same-SHA FZ-005 images. Native active gate
fresh **PASS: N1 55 excepted / 0 rejected; N2 104 excepted / 0 rejected**.

The three exact admission rows still need outer to append
`new-native-admissions-delta.json` to active `knowledge/gates/new-native-admissions.json`
(old manifest `2a3fac81`→unchanged U13 `85aef68e`). A private combined-registry
preview is **PASS**, but is explicitly not the active production registry.
There was no `--apply`, master write, device access, lock or a2hlab command.

## Required outer replay, not yet claimed

After landing the three exact new-native admission rows, outer runs:

```bash
bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/replay-production.sh" mac
bash "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/replay-production.sh" vm
```

`common.py` pins BASE to U10.1T8, and replay verifies its full SHA before passing
`--baseline-native` to the production executor. Fresh G1/G2 may not be borrowed
from the old comparison. Raw results go to `.artifacts/raw/` and portable originals
to `evidence/`, with OS and exact bundle/baseline identity in `gates/`.
**Production pending; no renewed window authorization and no promotion claim.**
The U14 assembly remains paused. Seven portable tests cover identities, exact
transfers, rejected drift, additions and the pending-production boundary.
