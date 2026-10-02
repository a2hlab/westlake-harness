# U15 preparation — disabled, not a production package

## Evidence and correction

Content is not promotion. The accepted U14 common bundle is
`9b42ddc6324c63e13d494a8e1144b3c196e70dabeb5ca7a8ec4fc36b58961cd1`;
the 61b metadata variant is
`f589844793299c3884a6738b2a4168dffe45680e89379cd53774bbde5c42835e`.
Both are checked against every declared native payload, effective BCP input,
runtime JAR and boot-group member locally. Neither is claimed promoted.
They carry identical native/JAR/image bytes but different board-local installer
references: common `2c9a5294`, 61b `51e1b525`, at both libinstalls paths.
Their files are unchanged by this preparation.

The M3 **native runtime** `94c31177` is not the Java runtime JAR `0349eb83`.
Only **framework.jar** `3e106350 → 9e55e286` changes the effective nine-member
BCP; stubs `87cf65cc` and non-BCP runtime JAR `0349eb83` are preserved.
Therefore all **27** FZ-005 images must be regenerated as one group. The donor's
earlier host verifier experiment is not the U15 two-run image build and its
output hashes are deliberately not selected here.

`plan.json`, `input-inventory.json` and `source-snapshots.json` bind full hashes,
persistent sources and portable snapshots. Large inputs remain under
`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u15-plan/.artifacts/inputs/`.
No native build, image bake, a2hlab/VM probe, device operation or registry write
is performed. There is **no final bundle/native manifest/inputs SHA** yet.

## Native input slots

| Slot | State | Evidence / scope |
| --- | --- | --- |
| M3 runtime | Staged, not deployed | `94c31177709dbea0b1615a63c0d41a358f7db6843cbbd11f77979576a1a86a47`; two persistent builds match; `a9cd4ed73b` |
| Mindustry host | Final slot pending | Intermediate `08175d186546fe8f95c2ecef0bc4158162afc4952c48fe9965dc5b2e3ee11320` arrived during preparation; stored as an **unselected reference** |
| Compat v3 | Stopped before build | Outer ACK(90) **06:55:21** accepts predicted movement **0**; no new ELF is invented |

That latest ACK replaces the compat direction with `org.jitsi.meet` in both
ANL and host native-domain lists, host based on the intermediate `08175d18`.
These two final route artifacts remain unknown. Keep one eventual U15 native
version, not an intermediate host package followed by a second compat package.
The current compat aliases remain U14 bytes until a separately accepted donor
exists. `native-slots.json` records the stopped item and replacement waitlist.
Do not count a plain compat export as relocation-scope proof.

Donor-only first-wall targets: M3 **3** (Flowit, fd-app, SPD), Bitmap **2**
(privacybrowser, fd-musicplayer), original compat v3 **0**; subsequent Meet route
**1** conditional target. **Observed movement here is 0**. None is a screenshot
or promotion result. Bitmap retains the ALPHA_8 null behavior.

## Full image rebake plan

`expected-images.{json,csv}` names all 27 `.art/.oat/.vdex` members and their U14
baseline hashes; every candidate hash is null. Forecast: **3 expected-change**
(framework segment), **16 may-change** (aggregate ART/OAT layout/references),
**8 expected-same** (unchanged DEX VDEX). These are not measured change counts.

Selected machine: SSH alias **hw248**, actual hostname **ecs-9f6c**, Linux x86_64.
Use the explicit approved FZ-005 lab home, not the SSH account's inherited HOME.
For public-path hygiene `plan.json` calls it `$HW248_HOME`; its exact string is
bound by SHA256 `4e5277d9907dc562d2135c48e53fa1ed5764ab628dae1e8e397499e708a1c102`
and sourced from master `knowledge/frozen/frozen.json`, FZ-005 artifact paths.
The historical U14 actual wrapper used this home and hostname; its portable
snapshot and raw source hash are in `inputs/source/u14-actual-recipe/`.

Frozen tools, unchanged:

- dex2oat64: `$HW248_HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64`,
  SHA256 `ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b`.
- driver: `$HW248_HOME/cc-wiki-t5/tool/t5_gen_image.sh`,
  SHA256 `14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46`.
- The repository t5 driver is **not** this frozen driver. Do not substitute it.
- `inputs/hostlibs.expected.sha256` binds the complete historical host `.so`
  inventory. Require a fresh exact inventory and dependency check before **each**
  compiler run. Remote availability/tool hashes have not been probed this round.

Future staging, owned by the authorized bake lane:

1. Copy this plan (without `.artifacts`) to
   `$HW248_HOME/u15-bitmap-9e55-v1/plan/`, and its nine private JAR snapshots to
   `$HW248_HOME/u15-bitmap-9e55-v1/jars9/`; verify `inputs/jars9.sha256`.
2. After a separate outer execution approval, explicitly set `HW248_HOME` from
   FZ-005, then run the following **on hw248 only**, once per run. Do not run it
   as part of preparing or reviewing this packet:

   ```bash
   U15_PLAN_EXECUTE=outer-approved-hw248-only \
     bash "$HW248_HOME/u15-bitmap-9e55-v1/plan/planned-bake.sh" 1
   U15_PLAN_EXECUTE=outer-approved-hw248-only \
     bash "$HW248_HOME/u15-bitmap-9e55-v1/plan/planned-bake.sh" 2
   ```

3. Both invocations use the **same** `work/incoming` and `work/products/arm64`
   paths. Save each complete nonempty group as `run1/` and `run2/`; do not reuse
   a log or output directory. The runtime JAR is not passed as `--dex-file`.
4. Live `tee` records compiler output and the full session. Persist actual argv
   JSON, frozen-tool and hostlib inventories, compiler/tee/session/script return
   codes, all 27 output hashes and timestamps under the same persistent root.
   Driver rc6 against the old U14 image reference is a **reported mismatch**,
   not G1/G2 or production PASS. Compiler and both tee statuses must still be 0.
5. Return both complete outputs and logs to
   `$WORKSPACES/westlake-inputs/generations/u15-bitmap-9e55-v1/`, with source and
   toolchain receipts. Partial products or concatenated interrupted logs are
   rejected. `planned-argv.json` is a template, never an executed-argv receipt.

`planned-bake.sh` exits **78 before any probe** unless separately enabled. This
packet and its publication do not supply that execution approval.

## Pairing and subsequent admission

`paired-receipt.template.json` has two NOT_RUN entries. For each actual run,
`validation.check_receipt` requires the exact nine input and 27 output maps,
actual argv, frozen compiler/driver identities, hash-bound logs/toolchain/hostlibs
and zero compiler/logging/script statuses. Also compare actual argv against
`planned-argv.json` after expanding only the approved HOME token; both runs must
use the same paths. Inspect every log and physical file against its receipt;
the structural validator alone is not provenance or execution evidence.

Compare all 27 files byte-for-byte. **Neither T7d nor the U14 boot.art exception
transfers to these new framework inputs.** If nondeterminism recurs, retain both
raw files, offsets and fresh frozen-oatdump object-chain evidence; submit a new
exact input/output-pair draft. The default is strict refusal, not a mask copied
from U14. Select a run only after that review.

Final composition must update both framework.jar inventory/live identity and its
effective `/system/android/framework` target, then pair the entire new image
group. Replace the native runtime/source profiles with the actual M3 donor,
preserve all other U14 owners unless an accepted final slot says otherwise, and
generate fresh N1/N2, ABI/calls/consumer, full open/string/class deltas, RB/T4b,
frozen/G1/G2 and Mac/VM production reports. Old registry rows are preview only
until exact new bindings are signed and active. No approval is fabricated here.

## Transaction baseline is a parameter

`transaction-base.template.json` keeps **common and 61b transaction bindings null**.
Each future binding must provide the actual base path/full SHA, signed full
per-board identity file and expected path map. `validation.check_transaction`
rejects missing evidence or either changed installer identity. This is a
structural check; future composition must also verify the evidence signature,
file hash, bundle contents and actual board state before replay.

Do not copy U14 `reference/runtime.txt` as an expected U14-live identity: those
comparison references describe the older U13 baseline. When U14 is promoted,
use the signed U14 **candidate** full identity. Until then no promotion is
inferred; neither 9b42/f589 nor a historical successful dry-run authorizes apply.

## Fresh Mac input checks and validation

- Runtime `open_site_scan`: **197 → 197**, namespace edges **0 → 0**. Existing
  DEFAULT-NS/MULTI-NS findings are retained verbatim in the evidence files.
  This is input comparison, not a final native gate or owner-uniqueness proof.
- Runtime `deployed_strings_diff`: raw **exit1**, unapproved additions/deletions
  retained. No allow list applied and no production delta signature invented.
- Framework `deployed_class_diff --frozen`: raw **exit1, UnicodeDecodeError**.
  The donor's verifier/shape report is preserved separately, not substituted for
  a fresh PASS. Final composition needs a successful fresh class/frozen check.
- Public outputs normalize only workspace/home paths; raw outputs, command
  argv, raw/evidence hashes are bound in `static-input-checks.json`.
- Python tests and two Rust selectors run without private artifacts; exact
  outputs are in `evidence/tests-*.txt` and lifecycle receipts.

Landing uses `landing-paths.txt` and `documentation.json` snippets. No binaries,
private logs, accumulated root documents, git commits, pushes or active-registry
changes are included. The outer reviewer owns landing and later authorization.
