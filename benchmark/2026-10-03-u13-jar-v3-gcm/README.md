# U13 JAR v3 = 506abe23 + a GcmDefaultNonce that works on Android: proven on ART with the boards' boot class path, with the old jar as a negative control

#90, JAR, offline. Nothing was deployed to a board; the tests ran on hw248's host ART.

`2026-10-03-u12-predicted-vs-actual` found that U12 R3 `adapter.core.GcmDefaultNonce` never initialises its Bouncy
Castle delegate on Android:
- it wraps the delegate as `new Cipher(spi, provider, transformation) {}`;
- libcore's `Cipher.init()` returns that specified spi from `SpiAndProviderUpdater.updateAndGetSpiAndProvider()`
  **without calling `engineInit`**;
- result: `GCM cipher needs to be initialised` for every process's default AES/GCM. moodcairns dies in our SPI, and the
  `[WL-KS-PROBE]` self-test fails in 154/174 U12 runs.

The U12 host test passed because OpenJDK's `Cipher` does call `engineInit`.

## The fix (only this class; `gcm-v2-to-v3.diff`)

- `Spi` now holds the next provider's **`CipherSpi` itself**, with no `javax.crypto.Cipher` wrapper.
- It calls the delegate's protected `engineInit` (both forms), `engineUpdate` (both), `engineDoFinal` (both),
  `engineUpdateAAD` (both), `engineGetIV`, `engineGetParameters` and `engineGetOutputSize`. These are resolved once
  from `CipherSpi.class` with `setAccessible(true)` and invoked on the BC instance, so dispatch stays virtual.
- `InvocationTargetException` is unwrapped and the delegate's own exception is rethrown unchanged (`AEADBadTagException`,
  `ShortBufferException`, …).
- Everything else is as in U12:
  - the provider sits at position 1 and finds the delegate the way `Cipher.getInstance` would;
  - a parameterless ENCRYPT/WRAP init gets a 12-byte nonce and a 128-bit tag;
  - decryption and explicit parameters pass through.
- The anonymous `Cipher` subclass (`GcmDefaultNonce$2`, the bug's vehicle) no longer exists.

## Test on Android semantics (`test/`, `evidence/`)

**Environment.** hw248, android-14.0.0_r1 host ART (`dalvikvm64`, `-Xint`, imageless). Inputs are pinned in
`evidence/hw248-inputs.txt`.
- **Boot class path:** the boards' exact BCP jars in board order:
  - core-oj `e5b18770`, core-libart `4e767490`, okhttp `d510981a`, bouncycastle `8b15216d`, apache-xml `f79af065`,
    core-icu4j `f31e34e2`;
  - framework `3e106350`, adapter-mainline-stubs `615b8bbe` (U12/U13), oh-adapter-framework `2257b835`.
- **Test-only Log shim:** one addition, `host-log-shim.jar`, an `android.util.Log` with no liblog natives (host ART has
  none), placed before framework.jar. It is never deployed.
- **Route-A JCA setup first:** the test calls the runtime jar's own `AppSpawnXInit.overrideJcaProvidersForOH()`, which
  gives BC + CertPath, then `OHSecureRandomProvider` and `TlsShim`, exactly as on the board. Without it, Android's
  `Providers.<clinit>` asserts on the missing `com.android.org.conscrypt.JSSEProvider`, which `ProviderDiag` showed.
- **Test:** `GcmAndroidTest`, dexed:
  1. `Cipher.getInstance("AES/GCM/NoPadding")`, parameterless encrypt → doFinal → decrypt with `getIV()`;
  2. explicit 12-byte IV + AAD round trip;
  3. Tink framing: `iv(12) || ct` from a parameterless encrypt, decrypted by reading the first 12 bytes;
  4. the runtime's own `KeystoreBoardProbe.selfTest()`, the `[WL-KS-PROBE]` self-test.
- **Runner:** `test/run_gcm.sh <runtime jar>`, with `GCM_RUN_DIR` and `ART_HOST_OUT` from the environment.

| runtime jar | case 1 | case 2 | case 3 | `[WL-KS-PROBE]` self-test | exit |
|---|---|---|---|---|---|
| **v3 `bbc3f530`** | **PASS** (provider WestlakeGcmNonce, ivLen 12) | **PASS** | **PASS** (ivLen 12) | **`validateAead(random 256-bit SecretKeySpec)=OK`** | 0 |
| v2 `506abe23` (negative control) | FAIL `IllegalStateException: GCM cipher needs to be initialised` | FAIL (same) | FAIL (same) | `selftest error … GCM cipher needs to be initialised`: **the exact line the boards log** | 1 |

The negative control reproduces the board's failure byte for byte. So this environment has Android's `Cipher`
semantics, which the U12 OpenJDK test did not. Logs: `evidence/hostart-run-v3.log` and
`evidence/hostart-run-v2-negative-control.log` (ART debug chatter filtered).

## Artifact and gates

| | |
|---|---|
| jar | `oh-adapter-runtime-u13-v3.jar` = `bbc3f530190fe98e2979dc4059379f8a0259d1f6ab243830347ca875cdb62f9b` |
| base | U13 JAR v2 `506abe23` |
| build | `build_v3.py`: base disassembled, the `adapter/core/GcmDefaultNonce*` smali family replaced, **every other smali file asserted byte-identical to the base**, reassembled with the pinned toolchain; built twice, byte-identical |
| `deployed_class_diff --deployed 5ae3dd29` (the boards' runtime jar) | **0 dropped, 0 reshaped**; additions = the known U12 r1/r2 + U13 classes (19, listed in `gates/class-diff-vs-5ae3dd29.txt`); GcmDefaultNonce's family is now `GcmDefaultNonce`, `$1` (the Service), `$Spi` |
| vs 506abe23 | 0 reshaped, 0 added, 1 dropped: `adapter/core/GcmDefaultNonce$2`, the anonymous `Cipher` subclass that carried the bug (`gates/class-diff-vs-506abe23.txt`) |
| deploy | runtime PathClassLoader jar: single-file replacement, no boot-image rebake |
| persisted | `$WORKSPACES/westlake-inputs/generations/u13-jar-v3/` (`SHA256SUMS`) |

## Prediction

| | |
|---|---|
| every process | the `[WL-KS-PROBE]` AES/GCM self-test is back to `validateAead=OK` (U12: error in 154/174 runs) |
| moodcairns | **the first fatal moves again (high)**: no `IllegalStateException` in our SPI. Tink's master-key self-test now gets 12-byte nonces from a working GCM. Lit unknown (next wall). |
| others | 0 at t20 (no other key reached JCA AES/GCM before t20 in U12); any later in-app AES/GCM use works again |

## Rules this round sets

- **Test JCE wrappers on ART with the boards' boot jars, not on OpenJDK.** The javax.crypto/libcore semantics differ:
  Android does not `engineInit` an explicitly constructed `Cipher(spi, …)`.
- **Make the old artifact fail the same test.** A behaviour test of a fix must also run the old artifact as a negative
  control and reproduce the board's failure. Otherwise the environment is not proven to have the board's semantics.

## Files

- `src/adapter/core/GcmDefaultNonce.java`, `gcm-v2-to-v3.diff`, `build_v3.py`.
- `test/GcmAndroidTest.java`, `test/ProviderDiag.java`, `test/hostshim/android/util/Log.java` (test-only),
  `test/run_gcm.sh`.
- `evidence/`: host-ART logs v3 / v2 and pinned inputs.
- `gates/`: class diffs vs 5ae3dd29 and 506abe23.
- `results.json`.
