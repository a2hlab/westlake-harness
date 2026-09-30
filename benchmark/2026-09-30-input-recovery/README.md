# Three offline input repairs

The host rejected four payloads already approved in #77, and its Subway pin referred to an older input. All **3/3 current local inputs now pass host preflight**, totaling **167 sidecars: 163 AArch64 ELF files and 4 exact approved data payloads**. No board was contacted; install, process survival and first-screen outcomes are **unknown**.

| Key | J3 rejection | Repair | Verified sidecars / exceptions |
|---|---|---|---|
| fd-seal | `libaria2c.zip.so` is ZIP data | Reuse three exact #77 packaged-data approvals | 9 / 3 |
| toutiao | `libcvt.so` is ARM32 | Preserve the single exact approved artifact as data | 138 / 1 |
| subwaysurfers | Pinned APK SHA mismatch | Explicit current arm64 input revision in `batch/apps.json` | 20 / 0 |

J3 evidence is `master benchmark/2026-09-30-j3-u3-sweep/runs/j3-5ea/5ea34a4500000000000000001123012c/{key}/record.json:17` (absolute paths and SHA in [J3 evidence](../2026-09-30-round1-plan/j3-feedback/evidence.json)). The exact approvals are [native-data-exceptions.json](../2026-09-29-install-walls/native-data-exceptions.json), lines 3–48. The original #77 README's “draft” label predates those recorded approvals.

The production gate requires approved status, package, ABI, filename, payload SHA/size, and APK SHA to match. Exception bytes must also match the member in the original APK. All other ELF, symlink, inventory, metadata, staging and installed-file hash checks remain. ARM32 data preservation does **not** enable ARM64 loading. Whether the active BMS extractor contains #77's corresponding exception patch is untested; this delivery removes the **host gate only**.

Subway changes from `5904cda2…` to `ffd32287…`; split `68920637…`. Both current APKs verify under signer `a0328a96…`, package `com.kiloo.subwaysurf`, actual versionCode `95769`, versionName `3.69.1`. The input metadata records the vendor-variant substitution at `~/a2hlab/app-inputs/subwaysurfers/app-input.json:10`; its versionCode `0` at line 37 is stale. We read the actual manifests with `aapt2`. The split has no DEX/resources requiring a merge (only `stamp-cert-sha256` beyond native libraries/manifest/signatures). The absent old APK's signature was not checked. Historical predictions keep the old SHA; new bytes require a new cohort identity, never retrospective scoring as the same APK. No external APK or metadata was edited.

[results.json](results.json) includes full SHA values, verified signatures/package lines, original metadata hashes and each sidecar. Reproduce from the repository root with the readonly Mac inputs and Android SDK build-tools 37.0.0 available:

```sh
python3 benchmark/2026-09-30-input-recovery/verify_inputs.py
python3 benchmark/2026-09-30-round1-plan/j3-feedback/extract.py
python3 benchmark/2026-09-30-round1-plan/j3-feedback/build.py
python3 benchmark/2026-09-30-input-recovery/test_receipt.py -v
agent-spec lifecycle specs/bms-input-recovery/t1-offline.spec.md --code tools/spec-checks --layers lint,test
```

Validation: **7 new FakeBoard tests**, **13 sidecar regression tests**, **56 batch regression tests**, **2 receipt tests**, and **3/3 Rust contract selectors** pass; lint score 100%. Logs are `tests.txt`, `sidecar-regression.txt`, `batch-regression.txt`, `receipt-tests.txt`, and `lifecycle.txt`. The contract covers offline behavior; it does not certify a board installation. `SHA256SUMS` pins this receipt, while `code-input-sha256.json` pins changed production/test/contract sources. R2: host reproduction verified, device outcome unknown.
