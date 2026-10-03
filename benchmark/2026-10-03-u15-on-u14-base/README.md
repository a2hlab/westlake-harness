# Disabled U15 transactions on per-board U14

## Evidence first

Earlier U15 compared reviewed U14 content but had no selected transaction BASE. VM replay also needs more than PATH: its `dexdump` wrapper forwards to the Mac SDK, which cannot read VM-local `/tmp` DEX files. Zero/zero classes must never become a class-diff PASS.

This packet selects matching U14 candidate BASEs, preserves all U15 artifact bytes/native bindings and runs fresh Mac diagnostics. It does **not** attest U14 promotion or authorize a window.

| Variant | U14 BASE | Disabled U15 copy |
|---|---|---|
| common (5ea/5cd) | `12d30eb099e683aa0f909b01db787a6aa00279be1fdf21447d157ccf3bc7d806` | `29c8a62cc78f5ba1eddea75fceb46e96baacba7e9b4d6fd046c9d8951ebe904f` |
| 61b | `b0f741320586a9fd10a538c9b22a34926a7167d98b74272669da62403295a652` | `8a260cec9b4ab3505cf72fe445e34643f0f1441abe9367658f3240d2e45a6a8b` |

Native manifest remains `4d3b6568a341e147754ccde384ed40ab58554eff0167cb248bb09c0b99fcf1b0`; inputs remain `4e25b830cad69914c5104628b5aff1e57d33b2f59c036a0f60ac3488efe3a4f2`. Persistent package and BASE paths are in each `composition.json`.

## Immutable composition

- Relative to each U14 BASE: **5 native paths / 4 objects, 3 JARs, 20 changed images**. Complete image group: **27 files**, 7 unchanged. `increments.csv`: 56 rows, 28 per variant.
- Native: runtime `94c31177`, host `9e3ad72e`, ANL `b96a8991` at both aliases, Flutter-private `libandroid` `9b824502`. Host/ANL remain atomic.
- JARs: framework `9e55e286`, stubs `94a94905`, runtime `20e748e5`; existing paired run1 receipt retained. No build or rebake.
- Only two `baseline_bundle_sha256` fields and explicit disabled `transaction_binding` change. `metadata-delta.json` and `artifact-stability.json` prove this boundary.
- Installers stay board-local: common `2c9a5294`, 61b `51e1b525`, both paths, no transaction action.

## Fresh refusals

Both executor attempts return **2**, stopping at static exact-add review: **NSD8 + trampoline5**. Framework comparison is nonempty **29341/29341**, with zero dropped/reshaped/added/frozen violations. All five ELF static comparisons pass with no open-site/namespace delta.

Independent native candidates return **1**: **99 N1 + 105 N2 = 204** rows await outer registry rebinding, zero tool errors. Both U14 baselines return **0**. Registry and exact-add policy were not edited or applied.

Independent image checks return **1**: **G1 true / G2 false**, because executable oatdump is unavailable here. RB/T4b/frozen return **0** for both variants. The executor did not reach those gates after its earlier static refusal.

Supplementary fresh open/readelf/strings/ABI/calls/219-consumer evidence is in `native-delta-gates.json`; raw strings rejection remains visible despite prior exact 20-row approval. `gate-exits.md` lists every exit; no historical PASS is substituted.

## Parameterized finalization

After outer confirms actual armed U14 bundles, change only explicit BASE path/SHA arguments:

```bash
python3 "$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-on-u14-base/run.py" \
  --common-base "$U14_COMMON_ARMED" --common-base-sha256 "$U14_COMMON_ARMED_SHA256" \
  --61b-base "$U14_61B_ARMED" --61b-base-sha256 "$U14_61B_ARMED_SHA256"
```

`rebind.py` validates the reviewed variant or an explicit arming-only equivalent (only `rollout_ready`/`rollout_blocker`), full planned fingerprints and effective hashes. Wrong variant, modified payload, existing output and installer actions refuse. Correspondence never grants promotion.

External replay uses `../2026-10-03-u15-final-assembly/replay-production.sh` with `U15_PRODUCTION_REPLAY=outer-approved`, arguments `mac|vm BASE BASE_SHA256 DISABLED_PACKAGE TRUSTED_OATDUMP`. Default **78 before probes**. VM prepends master `.vm-tools`, exports shared `$HERE/.artifacts/vm-tmp` as TMPDIR, and preserves MAC_HOME or discovers it through `mac sh` (empty discovery refuses). Mac environment remains unchanged. The same fix is included in the existing U14-on-U13 entry. U15 previously had no replay entry; this packet adds one.

Local tests model wrapper precedence, inherited/discovered Mac HOME and temporary DEX location; **not actual VM verification**. Actual production replay and 204-row/NSD8/trampoline5 processing remain outer-owned after U14 windows.

## Handoff

`landing-paths.txt` includes reports/specs/tests and both replay entries, excluding persistent `.artifacts`. `documentation.json` supplies isolated root README/runbook deltas without copying unrelated root changes. All execution/promotion/window flags stay false. No board, lock, VM, SSH or active-table write occurred.
