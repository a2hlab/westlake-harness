# U15 host = U14 host 341c1260 + mindustry OpenSLES audio-verify fix

#90, offline build on Mac (DevEco clang) + static replay; no board. The U15 appspawn-x host = the U14 host
`341c1260` (candidate-stock-host.c + the Wall-1 app-ns public-libs inherit) **plus** the mindustry audio-branch verify
fix from `2026-10-03-u15-ndk-private-domains`. A′ standard: reproduce 341c1260, then patch ×2 with the delta confined
to the OpenSLES IID name. (`evidence/build-and-replay.txt` has the raw gate output; `recipe/build_u15_host.py` the
builder; `recipe/win-u15-mindustry-audio.patch` the 2-hunk source change.)

## ① 341c already has the audio branch, and it fires for mindustry
`candidate-stock-host.c` (the 341c base source) `:304-322`: `if (native_private && .../io.anuke.mindustry/ ...)` →
`dlopen_ns("/system/lib64/libOpenSLES.so", RTLD_GLOBAL)` (the OH platform core) and verifies
`{slCreateEngine, SL_IID_ENGINE, SL_IID_VOLUME, SL_IID_PLAY, SL_IID_BUFFERQUEUE}` on that handle; `:352` then
`dlopen_ns(native_abi, RTLD_GLOBAL)`. **So the branch is present and matches `io.anuke.mindustry`** — mindustry's U12
`slCreateEngine` miss was that branch not being active at U12. But the verify has a **bug**: it asserts
`SL_IID_BUFFERQUEUE` (OH libOpenSLES *has* it, but `libarc` does **not** use it) and never asserts
`SL_IID_ANDROIDSIMPLEBUFFERQUEUE` — the Android-extension IID `libarc` actually uses, which lives in **native_abi**,
not OH libOpenSLES.

## ② The fix — verify each symbol against its real provider (`recipe/win-u15-mindustry-audio.patch`)
1. **audio_symbols** (checked on the OH libOpenSLES handle) **drops `SL_IID_BUFFERQUEUE`** → keeps the 4 core
   `libarc` uses from OH libOpenSLES (`slCreateEngine`, `SL_IID_ENGINE/VOLUME/PLAY`).
2. **after the native_abi `dlopen_ns` handle**, `native_private` asserts
   `dlsym(handle, "SL_IID_ANDROIDSIMPLEBUFFERQUEUE")`, reusing the existing `"[N4-AUDIO] provider lacks %{public}s"`
   format (no new log literal).

Why not the naive swap the issue sketched: a pure `SL_IID_BUFFERQUEUE → SL_IID_ANDROIDSIMPLEBUFFERQUEUE` swap **on the
OH handle** would *fail* — OH `/system/lib64/libOpenSLES.so` (66 exports) provably lacks any `SL_IID_ANDROID*`; the
Android IID must be asserted on native_abi. `dlsym` is not a loader open-site, so `open_site_scan` is unchanged.

## A′ gates
Build via `build_u15_host.py --u15` (Mac DevEco clang, recipe `r2-host-build-receipt.json`, reused-object allowlist):
- **determinism:** base341c ×2 = `8be1d6f3…`; u15 ×2 = `08175d18…` (each byte-identical).
- **base341c ≡ 341c1260 (semantic / A′):** not byte-identical — the only diffs are the embedded `__FILE__` build-dir
  paths + `.rodata` reorder noise from the path-length delta (a different benchmark dir, same class as Wall-1).
  **`abi_diff`: exports 15/15, 0 removed/added/drift/breaks → ABI identical.** So base341c faithfully reproduces
  341c1260; byte-identity across dirs is unachievable (embedded path), hence A′.
- **the fix delta, u15 vs base341c (both this dir, single-variable):**
  - `abi_diff`: 15/15, 0/0/0/0 — host ABI unchanged by the fix.
  - `open_site_scan`: **8 open-sites, IDENTICAL** (function/callee/path/flags; PCs shift from the added code only) —
    no new `dlopen`/`dlns`.
  - `deployed_strings_diff`: **only `−SL_IID_BUFFERQUEUE / +SL_IID_ANDROIDSIMPLEBUFFERQUEUE`** (plus the temp
    source-path string). Exactly the intended IID name change.

## ③ libarc 5-symbol replay under the U15 host (0 missing)
Under the U15 host's native-domain visible set (musl global scope: the audio-branch `dlopen_ns` of OH libOpenSLES
RTLD_GLOBAL + the native_abi `dlopen_ns` RTLD_GLOBAL), all five of `libarc.so`'s undefined OpenSLES symbols resolve:

| symbol | provider |
|---|---|
| `slCreateEngine`, `SL_IID_ENGINE`, `SL_IID_PLAY`, `SL_IID_VOLUME` | OH `/system/lib64/libOpenSLES.so` (core) |
| `SL_IID_ANDROIDSIMPLEBUFFERQUEUE` | `libwestlake_native_abi.so` (native_abi) |

**0 missing.** mindustry's `slCreateEngine` wall clears; `libarc` audio init resolves. (Prediction per
`2026-10-03-u15-ndk-private-domains`: mindustry is `bound`, so it proceeds past Arc audio init — lit medium–high.)

## Prediction / scope
- mindustry: all 5 OpenSLES symbols resolve → past the native-domain audio wall. The verify fix also makes the host
  **fail-closed** on the *correct* symbol (`SL_IID_ANDROIDSIMPLEBUFFERQUEUE`) instead of a symbol `libarc` never uses.
- The on-board arm64 confirmation (deploy the U15 host + re-bake) is the deploy owner's step; this is the Mac build +
  static replay only.

## Persisted / files
- `$WORKSPACES/westlake-inputs/generations/u15-host-mindustry-v1/`: `appspawn-x` (`08175d18…`),
  `win-u15-mindustry-audio.patch`, `build-commands.txt`, `logs/`, `SHA256SUMS`. base 341c1260 =
  `341c12608091246a…`.
- `recipe/build_u15_host.py` — the A′ builder (base341c gate + u15 ×2); `recipe/win-u15-mindustry-audio.patch` — the
  2-hunk fix; `inputs/candidate-stock-host.c` — the 341c base source; `evidence/build-and-replay.txt` — the gates +
  replay; `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; Mac build + static replay; no board; no push. The large host binary + logs are persisted under
`generations/` (not committed to the public repo), recorded by path + sha. On-board arm64 pass is the deploy owner's.
Sources read read-only: the 341c base source (`u14-appns-build/inputs`), the recipe + reused objects + sysroot
(`westlake-harness`/`-bms`), OH libOpenSLES + native_abi (`westlake-inputs/generations`).
