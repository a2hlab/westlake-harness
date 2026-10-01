# J8 + T7e reproducible package (cc-t3, 2026-10-01)

Self-contained, offline-reproducible record of the two U8 candidates the outer loop accepted:
- **J8 runtime JAR** `oh-adapter-runtime.jar` `6895b9e4…` (accepted ACK 09:48)
- **T7e boot images** (adapter-mainline-stubs.jar `f3bcc9d7…` + 27-file arm64 boot image) (accepted ACK 10:10)

Everything needed to rebuild from the pinned baselines is here: the three source artifacts, the build
scripts, and every input/output hash. Large binaries (jars, boot images) are not committed per repo policy —
only their sha256 (see `inputs.json` / `outputs.json`), so the package stays reproducible without shipping MB.

## Source artifacts (`src/`)
Authoritative copies from `feat/bms-walls` (commits `af75379f3`, `2fd59764c`):
- `WebViewProviderFix.java` — **new** class (cluster webview-provider / fd-tutanota). Seeds
  `WebViewFactory.sProviderInstance` with a type-zero `WebViewFactoryProvider` so `getProvider()` short-circuits
  on its cache instead of throwing `UnsupportedOperationException` (AOSP 14 r1 `WebViewFactory.getProvider`).
- `WestlakeSSLContextSpi.java` — **modified** (cluster nextcloud-accountmanager-null / fd-client). Both
  `engineCreateSSLEngine` overloads now `return null` instead of throwing, so `MainApp.onCreate` completes and
  the Dagger graph (incl. `accountManager`) is built.
- `ColorMatrix.java` — **replaced** empty stub with full AOSP 14 r1 `android.graphics.ColorMatrix` (cluster
  osmand-map-info-null / fd-plus). Adds `set(ColorMatrix)` + the backing 20-float array + the standard methods.

## Which baseline (run first — `evidence/artifact_identity.out`)
`scripts/lab/artifact_identity.py` on both stubs baselines, verbatim:
```
NOT DEPLOYED 366acc276a39  _u6-stage/adapter-mainline-stubs.jar  (deployed adapter-mainline-stubs.jar is d8b2406eb89d)
DEPLOYED     d8b2406eb89d  _hw248-t7d/adapter-mainline-stubs.jar  ->  /system/android/framework/adapter-mainline-stubs.jar
```
T7e must build on **d8b2406e (T7d, full tagsoup / FZ-007)**, not 366acc27 (T7c). The first T7e attempt used
366acc27 and was rejected; this package is the corrected d8b2406e build.

## Reproduce

**J8 runtime JAR** (`build/build_runtime_jar.py`, via `scripts/lab/dockbuild.sh` image `a2hlab-b5-java:24.04`):
baksmali the pinned J7b baseline (`381110a6`), add `WebViewProviderFix` (compiled→smali), surgically rewrite
the two `WestlakeSSLContextSpi.engineCreateSSLEngine` bodies to `return null` in smali, inject one
`invoke-static … WebViewProviderFix->install()V` into `B7BindFixes.apply`, reassemble, and prove via baksmali
diff that only those three classes changed. → `oh-adapter-runtime.jar` `6895b9e4…`.

**T7e stubs jar** (`build/build_stubs.py`, same image): baksmali the pinned T7d baseline (`d8b2406e`), replace
`android/graphics/ColorMatrix.smali` with the compiled full ColorMatrix, reassemble, prove only ColorMatrix
changed. → `adapter-mainline-stubs.jar` `f3bcc9d7…`.

**T7e 27 boot images** (`build/gen_t7e_images.sh`, on hw248): the FZ-005 `t5_gen_image.sh` + host `dex2oat64`
over the 9 BCP jars (8 T7d-identical + the new stubs). Acceptance:
- **G1 (determinism)**: 8/9 vdex byte-identical to the T7d reference (only the changed stubs input moves output).
- **G2 (change landed)**: `boot-adapter-mainline-stubs.vdex` `465e0dd4…` (T7d) → `1c115d56…` (new ColorMatrix).
- L2: `boot.oat` oat version 230, `boot.art` image version 108; dex2oat clean (6.84 s).
- `t5_gen_image` exits 6 by design (it wants 9/9 for a *pure* reproduction); for T7e the stubs vdex is intended
  to differ, so 8/9 + the single expected segment + valid headers is the pass. The outer loop re-checked all 27
  files per-file on hw248 and accepted by the vdex criterion (ACK 10:10).

## Layout
- `src/` — the three source artifacts.
- `build/` — `build_runtime_jar.py`, `build_stubs.py`, `gen_t7e_images.sh` (paths default to `$HOME`/`LAB_HOME`; override with `J8_INPUTS`, `DEX2OAT`, `T5_GEN`, `T7D_JARS`). `evidence/artifact_identity.out` — verbatim baseline identity check.
- `inputs.json` — every pinned input hash (baselines, 8 BCP jars, toolchain, references).
- `outputs.json` — output hashes + G1/G2.
- `landing-paths.txt` — the files in this package.
