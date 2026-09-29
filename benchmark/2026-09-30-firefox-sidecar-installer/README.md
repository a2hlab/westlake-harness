# Firefox native sidecars (offline handoff)

The old batch installed only the original base APK. Firefox's base contains **zero `lib/` members**; all **18 AArch64 shared libraries, 198,637,232 bytes**, are extracted beside the input APK. Every file matches both `app-input.json` and the original arm64 split member (see [input verification](evidence/input-verification.json)). Base APK SHA-256 is `eba96cc660d0a49116db37c97535d01d809b21e217d4f24909eb33bf912882fc`; split SHA-256 is `6bbda34bfa4c5310b255e369b66e566324d0279cddb337efd8311b1b7ba209e7`.

The new rule is to assemble and verify native sidecars **after BMS readback and cold stop, before desktop click**, retaining the exact original APK. The destination is:

```text
/data/app/el1/bundle/public/org.mozilla.firefox/android/lib/arm64-v8a
```

This choice is backed by the actual r17a JAR, not just a source comment: [B7BindFixes.smali:341](evidence/B7BindFixes.smali) checks the old directory, then selects APK-parent `lib/arm64-v8a` at lines 402–426. The [bind callsite](evidence/bind-callsite.txt) proves it is invoked. [Runtime identity](evidence/runtime-lookup.json) pins that JAR. In the prior r16 run, Firefox fell back to the APK directory and failed to load `libjnidispatch.so` ([numbered log excerpt](evidence/r16-before.txt)). The new path addresses that missing-file condition; subsequent linker/runtime behavior remains untested.

`resolve_native_sidecars` in [bms_batch.py](../2026-09-28-bms-route-deploy/batch/bms_batch.py) validates inventory, input hashes/sizes and ELF64 little-endian AArch64 ET_DYN headers before any board operation. Firefox's manifest entry requires exactly 18 files. `assemble_native_sidecars` verifies the installed base APK, stages and hashes every library, copies into the destination, checks final hashes, and writes `native-assembly.json` plus `record.json.native_assembly`. Missing inputs, conflicting existing libraries, changed bytes or transfer failures prevent the click. Identical existing libraries are reusable, including with `--launch-only`; unrelated files are retained. A failure can leave a partial set, recorded as failed; it is never reported as verified. A conflicting partial/corrupt file requires a clean reinstall, not silent replacement.

No APK rewriting/signing or split dex/resource installation occurs. The xhdpi resource split is still not installed by this step. Directory existence, sidecar receipts and FakeBoard success do not establish a rendered first screen.

## Run offline

From the repository root:

```sh
python3 benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py --keys firefox --resolve-inputs
python3 -m unittest discover -s benchmark/2026-09-28-bms-route-deploy/batch -p test_bms_batch.py
python3 -m unittest discover -s benchmark/2026-09-28-bms-route-deploy/batch -p test_native_sidecars.py
python3 benchmark/2026-09-30-firefox-sidecar-installer/verify_receipt.py
```

The default input root is `~/a2hlab/app-inputs`. [firefox-plan.json](firefox-plan.json) is the resolved read-only plan. The two test suites pass **56 + 13 = 69 tests**; [lifecycle](evidence/lifecycle.json) passes. Native tests cover install/reinstall ordering, `--launch-only`, metadata/ELF/hash failures, embedded/existing-library conflicts, input symlinks, offline planning, and the real shell status-marker convention. The historical #59 whole-directory test rejects its already-obsolete runner hash; [baseline comparison](evidence/historical-plan-drift.json) proves this predates the change. Its frozen plan was intentionally not repinned. The first broad test log is retained in `evidence/unittest.txt`; focused final results are `batch-tests.txt` and `native-tests.txt`.

## Outer-loop board handoff

Per the updated assignment, this lane performs **no board writes**. After r17a releases 61b, the outer executor performs its normal read-only checks and acquires the 61b lock. With Firefox already installed and the executor holding the lock as `claude`, run from the repository root:

```sh
python3 benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py \
  --execute --serial 61b0657200000000000000000324012c --lane claude \
  --hdc-cmd /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc \
  --keys firefox --launch-only --shots 5,20 --hilog 20 --wait 20 --focus-check \
  --run-id "firefox-sidecars-$(date +%Y%m%dT%H%M%S)" \
  --out benchmark/2026-09-30-firefox-sidecar-installer/runs
```

Use the actual lock holder for `--lane`. For a fresh install, replace `--launch-only` with `--reinstall`. Do not use both. The batch checks installed-APK identity before library copying. Collect `native-assembly.json` (18 verified files), `hilog.txt` (actual B7 destination and next failure, if any), scheduled process tables and screenshots. Quote `facts.txt` and visually review the screenshots. This handoff's captured count, live counts and lighting verdict are **unknown**, not zero or pass.

## Integration and scope

[batch-sidecars.patch](batch-sidecars.patch) is the **three-file incremental patch** against master `3ab4817356f4e2b421b286d4db7e0a4cdbcffe13`: batch runner, `apps.json`, and the new native-sidecar test. Existing master batch improvements and `run_facts.py` were synchronized into this older worktree for regression tests; the patch does not replace them. The outer loop can `git apply --check` this patch before applying it, then include this benchmark, the new spec, two Rust selectors and the small README/DIGEST additions. No local commit was possible because this sandbox's git metadata is read-only; the commit field is null in [results.json](results.json).

Installer rebuilding was reassigned to **cx-t0** by the user; no installer binary was built or deployed here. R2: input bytes and r17a lookup verified; orchestration verified with FakeBoard; device effect unknown. The original source/input directories remain read-only.
