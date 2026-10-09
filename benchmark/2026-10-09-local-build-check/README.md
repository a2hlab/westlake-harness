# Local native fallback build check — cx-build, #91

**Status: partially.** The local container faithfully rebuilds the deployed loader, and compiles the actual
namespace-table owner's minimal change. BoatAttack's existing CLASSNAME_FIX needs no compilation for
`libandroid.so`; applying that same file to the current runtime is **unverified and invalid as a direct replacement**.
All five questions in `TASK.md` are answered below. No board command, lock, install, restart, deployment or push ran.

## What was wrong / rule established

1. The task points the public-library fix at `libapp_native_loader.so`. Its deployed source only **calls**
   `namespace_host_ops.create_configured_namespaces`; `StockCreateConfiguredNamespaces` and the app-to-bridge
   `dlns_inherit` table belong to **`appspawn-x`**. The earlier correction already exists in
   `benchmark/2026-10-03-u14-appns-build/README.md`; this check confirms it from the actual loader source and archived
   deployed host source (`evidence/namespace-owner.txt`). A loader-only table patch would misrepresent the owner.
2. BoatAttack's archived bundle aliases the same `adc125f4` blob into two shared paths. Today's U13 has **different
   objects** at those paths: `libandroid.so` is `9ccf64f8`, but `liboh_android_runtime.so` is `18763dd4`.
   Compare the exact destination object before reusing a file. The runtime is **3,194,328 bytes / 787 exports**;
   the boat blob is **744,856 bytes / 268 exports**. Direct replacement removes **520 exports** and adds one.
   Only **2/49** original patch bytes match the runtime at the recorded offsets.
3. Local frozen Linux clang plus the original source path and working directory reproduces loader `eebd62f2`
   **byte for byte**, without hw248. A build-host dependency must be checked by running its pinned compiler.

## 1. Deployed identity and exact inputs

The existing read-only **2026-10-09 three-board fingerprints**, not a candidate plan alone, identify:

| destination | SHA-256 |
|---|---|
| `/system/android/lib64/libapp_native_loader.so` | `eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c` |
| `/system/lib64/westlake/route-a/74d1d6d48210ec5bf66ae43598655c3486b8873513821f13c2ffe15f0de552ac/libapp_native_loader.so` | same `eebd62f2…` |
| secondary route `74e6f759…/libapp_native_loader.so` | `a3d4b80d943dd78972e5689a29810406f97056e0ce8f040d2ec24ac3618d9929` — a different archived loader, not the build baseline |

Evidence: `benchmark/2026-10-09-demo-baseline/evidence/readonly-20261009/{5ea,5cd,61b}/runtime-fingerprint.txt`;
U13 `benchmark/2026-10-03-u13-gate-review/manifests/native-manifest.json`. The actual reference file is
`$WORKSPACES/westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle/native/payload/route/libapp_native_loader.so`.
ABI consumer is that bundle's `payload/runtime/appspawn-x`, **`2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e`**.

Exact source: `$WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-09-30-n3-native/flutter/`.
`app_native_loader.c` SHA `aa1cd7c09164f1e6eefb928e8bc856ecb4df3ce22f81842d6595911c5c1f1d06`,
`flutter_domain.inc` SHA `0117797953a738f248d13f9f8be04e76d6052f1e0f70cf0f0e5c88f16472c15b`.
Source commit **`9b6d6df021757c07840c8ff06a89ea1c4cef79bc`**, working tree source unchanged.
Build recipe: the **two ANL compile/link commands** from that benchmark's `build-flutter.sh`
(`1052fca583251cd7e4f55f17bdcc7d00a2fb512cef24f3ca3978bf218d023d51`). The rest of that script builds unrelated
libraries and was not executed. `evidence/build-commands.txt` records the exact invocation.

`FROZEN=$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b68-generation/.work/product-tls-generation/frozen`:

| input | identity |
|---|---|
| `$FROZEN/toolchain/bin/clang-15` | OH clang 15.0.4 `feef13a36e78b7a2ff3e9e3f180a958f2782be1e`; SHA `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913` |
| `$FROZEN/toolchain/bin/ld.lld` | SHA `8583bdc812436711a586fc4eae23cbf744606a31377fa3b28b04b639e1f403b4` |
| `$FROZEN/sysroot/lib/aarch64-linux-ohos/libc.so` | SHA `ab5ad48a82295e6ec144aaac730bfa053e744e4903c01d51707ce0935385d905` |
| full toolchain tree | 1,694 entries; manifest SHA `dde053bfd4cc188d8d4f0af90d249ded58f0a97db571cc284128cf7603feccea` |
| full sysroot tree | 2,368 entries; manifest SHA `b5440ab39dd05c9ec6b40bde12fc820400f6291947e356c2f69edc473e53e629` |

Source lookup succeeded on the Mac, before VM/remote search. OrbStack `a2hlab` was checked read-only and available;
builds used local Docker image `a2hlab-build:24.04`, Linux amd64. hw248 was not contacted. The source workspace was
mounted **read-only**; only this task's independent output directory was writable. Original source paths and cwd were
preserved, and `clang-15` was called directly with `LD_LIBRARY_PATH=$FROZEN/toolchain/runtime`.

## 2. Unmodified local rebuild

**Two builds = exact deployed `eebd62f2…`.** All **40/40 ELF sections**, file size and full file SHA agree. There is
no source/toolchain/path/timestamp discrepancy to explain (`evidence/loader-sections.json`, `loader-readelf.txt`).
`abi_diff.py --old <deployed> --new <local> --consumer <U13 appspawn-x>`: **8/8 exports, 0 removed, 0 added,
0 signature drift, 0 consumer breaks**. See `loader-abi.json` and `loader-abi.txt`.

## 3. Minimal public-library-table build — corrected owner

The literal request to modify a loader-owned table cannot be executed faithfully: no such implementation exists in
the deployed loader source. Instead the actual owner was built, with **only the app-to-bridge public-library list
expanded by `libicui18n.so:libGLESv2.so:libGLESv3.so:libjnigraphics.so`**. The existing sonames are preserved;
overflow returns `ENAMETOOLONG`. No ABI/header change or native-package enrollment was made.

Source: this repo's `benchmark/2026-10-03-u15-jitsi-native-domain/inputs/candidate-stock-host.c`
(landed commit **`6e8f2ce2554da7c3d912e93d47cf9172d34b330f`**), the archived U13 host source before Wall-1.
Implementation pattern reused from `benchmark/2026-10-03-u15-host-mindustry/recipe/build_u15_host.py`, with exactly
the four requested libraries rather than its six. The U10 host receipt supplies headers, link command and
**16 SHA-checked reused objects**. No other worktree was edited.

| build | SHA-256 |
|---|---|
| local container host baseline | `27fff5ec8bd1608a058f9db9b804f190f7cacdc5795cc600c79b3f40054d58a4` |
| local container host + four public libraries | `4cb25e404c3a28caa505ee1615e9faf424d22d443c70eb5955d4fc23d7e51e28` |

Compile/link **rc=0**. Same source filename/cwd for the paired comparison. Host `abi_diff.py`: **15/15 exports,
0 removed/added/drift/breaks**. `.rodata` string-set delta is **one added table string, zero removed strings**.
See `host-public.diff`, `host-abi.json`, `host-strings-diff.json`, `host-sections.json` and `host-readelf.txt`.

**Limit:** this host comparison proves local compilation and unchanged exported ABI. The deployed host was built
with **Mac DevEco clang**, while this container uses **Linux frozen clang**. The container host is not claimed to
faithfully reproduce deployed host `2a87118e`; production publication must use its original-toolchain reproduction
gate. No namespace visibility or app behavior is claimed from compilation.

## 4. BoatAttack route ②

**No compile required for the existing `libandroid.so` fix.** Use this read-only source:

`$HOME/orca/00.Workspace-games-ad1ab0a7/.bridge-payload/zigzag-candidates/strict-boat-assembled-20260924T074522Z-25403/files/libandroid.so`

SHA **`adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130`**, 744,856 bytes.
Source tree anchor: `games/boatattack-repro` **`43ec24af9`**; binary is an assembled/board-pulled file without a
tracked introducing commit. Its later candidate-file destination is **`/system/android/lib64/libandroid.so`**, whose
current baseline is `9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db`.
Diff: **49 bytes**, **268/268 exports**, 0 export/signature changes (`boat-byte-diff.json`, `boat-abi.json`).

Do **not** reuse that blob at `/system/android/lib64/liboh_android_runtime.so`: today's destination SHA is
**`18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae`**, not the boat bundle's aliased baseline.
The **520 removed exports** and **2/49 offset matches** disprove a same-object patch mapping
(`boat-runtime-abi.json`). That checker returns rc=0 when there is no signature drift/known consumer break;
the removed-export list must still be inspected. Whether the actual runtime also needs CLASSNAME_FIX, and the
source/instruction mapping for such a port, remain **unverified**. No modified runtime was produced.

## 5. Conclusion and missing inputs

| fallback / component | conclusion | missing input and time to close |
|---|---|---|
| deployed `libapp_native_loader.so` rebuild | **本机能编**, exact deployed SHA twice | none; input gap **0 min** |
| Wall-1 actual owner (`appspawn-x`) four-lib amendment | **本机能编**; ABI equal to paired local baseline | loader-only fix premise corrected; deployment-host fidelity under Linux is not claimed because its original compiler is Mac. Production gate is a later task |
| BoatAttack `libandroid.so` CLASSNAME_FIX | **现件齐备、无需编译** | none; input gap **0 min** |
| BoatAttack current runtime CLASSNAME_FIX | **适用性未验证**, cannot replace with the existing blob | exact-object patch/necessity mapping missing; **unknown** until that question is resolved. This is not evidence that its compiler is missing |

Final measured container run (two loader builds + two host builds): **5.535 s**, all compile/link commands rc=0.
An earlier successful exploratory run took 6.253 s; final comparison re-ran with the same host source filename to
remove path differences. Environment preparation failed once before any compiler ran (missing archived input
directory); the builder then used the already-landed source copy. No source/link failure occurred.

## Persistence, checks and delivery

Final original merged stdout/stderr was **tee'd during execution** to
`$WORKSPACES/westlake-inputs/generations/local-build-check-20261009T131530Z/build.log`,
SHA **`2fe184ffc471fcfcee16f88dd92d426c6a3ff2ff4251d37da6427c7c71c49d8d`**.
Paired receipt `receipt.json` SHA **`aa7bb5b1fa7e0a73a63795ff2bc60d5a72e4cc09c41fa6ad6078fdef9558997f`**;
executed `build.sh` SHA **`5a13601ec5bccc0029e1e7c9da1b82023f451c4537f511fdd4fe1c4043680b33`**.
That independent temporary build directory also retains exact outputs, source snapshot, host baseline/patch sources,
toolchain/sysroot file manifests and raw ABI receipts. Large binaries and full raw logs are not committed.
The earlier exploratory run is retained at the sibling `local-build-check-20261009T131451Z` directory.

Small evidence, `results.json`, contracts and `landing-paths.txt` are committed locally. `documentation.json`
contains root Layout/DIGEST/RUNBOOK additions for outer landing. Frozen/user-path gate outputs and spec checks are
in `evidence/`; frozen reports **8 entries, 0 checked, 0 violations** (no registered frozen source in this worktree
was checked), not a claim of validating all external frozen artifacts.

Re-run from this worktree:

```sh
python3 benchmark/2026-10-09-local-build-check/evidence/build_local.py
python3 benchmark/2026-10-09-local-build-check/evidence/audit_local.py <printed-run-dir>
cargo test --manifest-path tools/spec-checks/Cargo.toml --test local_build_check
python3 scripts/lab/check_user_paths.py
```

**Verified:** exact local loader reproduction, actual-owner minimal compilation/ABI, existing boat `libandroid`
identity and negative runtime-replacement check. **Partially:** corrected owner differs from TASK's loader-only
premise; BoatAttack's runtime port remains undecided. **Unverified:** production deployment and app behavior.
