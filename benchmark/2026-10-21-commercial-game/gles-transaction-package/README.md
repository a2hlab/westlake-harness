# G20 current-baseline transaction inputs

The old U13 package is not the current baseline: four Boat r4 overlays change its runtime JAR, libandroid, bridge and Android runtime. The actual 5ea receipts cover 285 package targets and 34 additional reference targets, **319/319 full SHA values**, with boot `a1d869b4-69a2-40a4-937e-4860f5b54239` held across the reads. Three separately observed Boat private libraries are preservation evidence only. No device calls or compilation occurred in this lane.

`assembly-01` and `assembly-02` are persistent under `.private/`; **assembly-01 remains unchanged**. Both reuse G18 ELF `878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23`. Baseline loader is `b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7`. Original U7 `prepare` proves two logical alias changes, no additions, and **32 actual planned writes, including 30 same-SHA boot/JAR members**. This is an unsigned input package, not deployment or game success.

## Inputs and immutable attempts

- Original bundle: `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-03-u13-effective-rebind/.artifacts/bundle-v4`, bundle `91272eaf4cdda30b0c079575cd269959c6f6dab9f23a09a0fed567c20478bd28`, native `85aef68eafbde98e6ac885264fe36f2f1e357618abf1d455de6ca15c0996cee6`.
- Assembly follows the existing U13 `prepare.py` clone/rebind method and calls unchanged `effective_files`, `validate`, `prepare`; it never executes historical `main` or staging. Exact tool hashes are in `tool-source-pins.json`.
- Boat r4 sources come from the existing `minimal-r4/package/plan.disabled.json`; all four local artifacts match actual current SHA. The three private app libraries remain outside the candidate replacement set.
- G19 admission: `benchmark/2026-10-21-commercial-game/loader-deployment-admission/README.md`, accepted in `d4723c8505` and `0343e4a61b`. U7 creates a new journal after live baseline/hash/mount checks; no historical owned state is required or fabricated.
- Current raw evidence roots are indexed in `input-pins.json` and `evidence-index.json`. Public copies are explicitly sanitized; raw files are unmodified. `$G20` means this card, `$WORKSPACES` the workspace parent, and `$LAB_HOME` the prefix recovered from the actual AOSP `SOURCE.txt` provenance.

## Actual gate results

First attempt (`evidence/gates-01`) is retained: U7 rc2, G1 PASS, G2 missing oatdump; native rc3 with historical N1 profile binding error and 104 rejected N2 findings. Static rc0 and both frozen checks rc0. The original static scanner reports empty open-site/literal sets for the loader pair; its PASS does not replace G18's explicit 7-to-8 shared-array proof.

Outer reran the unchanged U7 with the original `oatdump_remote.sh` and provenance-derived `LAB_HOME`: rc2 reached native gate. Separate original generation-bundle evidence in `evidence/outer-g20-images-01/report.json` proves G1 nine segments match and G2 candidate/reference String.hashCode each 36 instructions match. The identical images/BCP in both assemblies reuse this evidence. Full package preflight is still not accepted.

`assembly-02` changes only N1 sidecar source/binding metadata. It verifies the Boat fresh-build ELF and original rc0 logs, actual dependency source files and updated compat shim, plus G18 baseline/candidate source and build records. Its 30 profile bindings are listed in `n1-current-source-attestation.json`. The initial rebind check failure is preserved: `preparation.json` records recipe before the original build driver replaces one compat-shim path; exact reverse replacement reproduces that preparation hash. No historical build was rerun.

Actual native rerun (`evidence/gates-02`) returns rc1 with no INVALID/errors: **55 N1 + 104 N2 findings per package**. N1 has two changed finding texts at the compat-shim source locations; they remain explicit review items. `exception-comparison.json` compares full finding content and relevant consumer/provider/directory-member SHA against the old approved 85aef68e/c40faa79 group. N2 divides into **100 exact-object rebind review items and four changed-object review items**: two domains' runtime dependency provider candidates and the Android/route uncovered directories. Identical text is not identical object bytes.

`exceptions.unsigned.json` contains 318 proposed rows (159 per package). All `approved_by`/`approved_at` fields are null. Old signatures are references only, never transferred. Both package manifests and new inputs identities require real outer approval. The main registry and all gates remain unchanged.

## Reproduce and review

Run `inspect_inputs.py --main <main> --base <bundle-v4> --evidence <readonly-root> --out <card>`, then `assemble.py --workspaces <workspace-parent> --evidence <readonly-root> --out <fresh-assembly>`. The assembly output must be new. `rebind_n1.py --from-assembly <assembly-01> --out <fresh-assembly-02>` creates the current-source sidecars without modifying its input. `run_gates.py` persists argv, stdout, stderr and rc during execution; `--oatdump` is explicit and `--lab-home-from-provenance` uses the original U13 regex. `next-commands.json` gives the final original U7 argv for outer after native review. Do not repeat isolated G2 or execute a device action from this package.

`rollback-binding.json` binds all 319 baseline hashes and both original alias sources (`seq16`, `seq51`). A future real apply journal owns rollback; the current package has none. Original mounts and Boat overlays remain baseline layers. Fresh live identity checks and the original gates remain mandatory at any future outer window.

Run `python3 check_receipt.py` for public evidence and five refusal cases; add `--private` to rehash all private package files. The Rust selector is `commercial_game_gles_transaction_package`. `landing-paths.txt` is the path-only handoff; `.private`, binaries, raw personal-path logs and Python bytecode are excluded. No shared Git or board write was attempted.
