# U11 JAR cluster 4 — keystore / EncryptedSharedPreferences (moodcairns AEADBadTag) (#90)

**App:** `cv2-com-lcdcode-moodcairns`. **On-board wall** (U9 hilog, PID 23919):
```
[WL-KEYSTORE] installed software AndroidKeyStore provider, keys in .../no_backup/westlake-android-keystore
java.security.KeyStoreException: the master key android-keystore://_androidx_security_master_key_ exists but is unusable
  Caused by: javax.crypto.AEADBadTagException: mac check in GCM failed
```
That exact wording is **Tink's `AndroidKeystoreKmsClient.validateAead()`** — it creates/loads the androidx master key,
then runs an **encrypt→decrypt self-test of that key** (same key, same process). The self-test fails with
`AEADBadTagException`, so Tink declares the master key "exists but is unusable" and the app dies in `MainActivity`.

## Probe (Mac JVM) — the crypto is SOUND; result = 6/6 PASS
`KeystoreProbe.java` runs the **real** `SoftwareAndroidKeyStore` (copied unmodified) + minimal android stubs, and
reproduces Tink's path: generate the AES256_GCM master key via the provider's `SecretKeyGenerator` SPI + androidx
`KeyGenParameterSpec`, then Tink's `validateAead` (`iv(12)||ct`, tag 128, with AAD). `run.sh` builds + runs
(`probe-output.txt`):
```
diag: default provider = SunJCE; AES/GCM encrypt-without-params IV length = 12 bytes (matches Tink's 12)
  PASS key gen: 256-bit AES (SoftwareAndroidKeyStore SPI)   [algo=AES bytes=32]
  PASS same-process: getKey stable                          [two getKey() calls equal]
  PASS same-process: encrypt iv==12                         [iv.length=12]
  PASS same-process: validateAead round-trip                [decrypted==plaintext]
  PASS persistence: key reloaded from file                  [bytes=32]
  PASS persistence: decrypt after reload                    [ok]
==== RESULT: 6 passed, 0 failed ====
```
So `SoftwareAndroidKeyStore`'s AES-256 key generation, raw-bytes persistence + reload, the 12-byte GCM IV, AAD, and the
full `validateAead` encrypt→decrypt all round-trip on a desktop JVM. **The on-board BadTag is NOT the key material,
persistence, or GCM mechanics.** (Two desktop-JVM artifacts hit on the way, both absent on ART and worked around in the
probe: JDK8 `crypto.policy` 128-bit cap → `Security.setProperty("crypto.policy","unlimited")`; JCE provider-jar signing
for `KeyGenerator` → drive the SPI directly. Neither exists on-board.)

## Localization — ruled out vs leading hypothesis
Ruled out (probe-verified): key material / 256-bit gen; raw-bytes persistence + reload; GCM mechanics on SunJCE; IV
length (12). Also ruled out by the error *signature*: "exists but unusable" (key **found**, decrypt BadTag) is **not**
"not found" — so a dual-instance / missing-persistence story (which would be a null key, a different error) is not it.

**Leading hypothesis (on-board only, not Mac-reproducible):** `Store.engineGetKey` returns a **plain `SecretKeySpec`**
(raw bytes), not a provider-bound key. So `Cipher.getInstance("AES/GCM/NoPadding")` on-board resolves to the **default
Cipher provider** (Conscrypt/BoringSSL on OH), **not** our provider. On real Android the master key is an opaque
`AndroidKeyStoreSecretKey` and the GCM Cipher is served by the AndroidKeyStore provider (keystore-generated 12-byte IV).
If the on-board default provider's AES/GCM for a plain `SecretKeySpec` diverges from SunJCE's (encrypt-without-params IV
length ≠ 12, or it requires explicit params), Tink's `iv(12)||ct` framing breaks → `AEADBadTagException`. This cannot be
reproduced on this Mac (SunJCE is well-behaved), so it needs a board probe to confirm.

## Board probe (pins the root; diagnostic-only, no persistent change)
`src/adapter/core/KeystoreBoardProbe.java`. **`selfTest()` (key-independent, run at BIND time)** is the primary check:
post-bind the app master key usually does not exist yet (the merged U11g probe only reported "key absent"), so
`selfTest()` generates its **own** random 256-bit AES `SecretKeySpec` and runs Tink's exact framing through the DEFAULT
`AES/GCM/NoPadding` provider (encrypt-without-params → `getIV()` → `iv||ct` + AAD → decrypt). It logs `[WL-KS-PROBE]
selftest cipher provider=… ivLen=… validateAead=…` — directly testing the leading hypothesis without any app key. On Mac
(SunJCE) it is `ivLen=12 validateAead=OK`; on-board it shows what Conscrypt/BoringSSL actually does.
`run(alias)` calls `selfTest()` first, then — only if the app key already exists — the per-key check:
the key class + encoded length, two-`getKey()` byte-equality, provider name, IV length, `validateAead`. Together they say
which is the root:
- `ivLen != 12` → on-board default-provider GCM IV divergence (the leading hypothesis) → fix below.
- `validateAead AEADBadTagException` with `ivLen == 12` → a deeper default-provider/AAD divergence → capture and re-localize.
- `getKey stable=false` or `present=false` → a store/persistence divergence after all (re-open the keystore analysis).

## Candidate fix (ONE new file; NOT written blind — gated on the board probe)
Per campaign discipline (结果说了算), the one-file fix is **not** committed before the board probe names the root. The
leading candidate, if the probe shows the default-provider GCM divergence: **make `SoftwareAndroidKeyStore` own the
AES/GCM Cipher for its keys** — a new `CipherSpi` (new file, additive; does not touch the frozen
`SoftwareAndroidKeyStore.java` beyond registering the service + returning a provider-bound key subtype) that generates a
deterministic 12-byte IV on `ENCRYPT_MODE` without params, matching Android's AndroidKeyStore. For Tink to actually pick
our Cipher, `engineGetKey` must return a key subtype only our provider handles (so JCA routes the Cipher to us, as real
Android does for `AndroidKeyStoreSecretKey`) — that is the real content of the fix and why it needs the probe's
confirmation first (a plain Cipher registration alone won't win provider selection against the default provider).

## Wiring for cc-t3 (U11 JAR)
1. **Now:** add `KeystoreBoardProbe` to the U11 JAR (it is in `adapter.core`, no new deps) and call
   `KeystoreBoardProbe.run("_androidx_security_master_key_")` once in the keystore/bind path (or run moodcairns in the
   U11 window and read `[WL-KS-PROBE]`). Hold the cluster-4 *fix* merge until that line is read.
2. **After the probe:** the one-file fix (new `CipherSpi` + provider-bound key) lands as a new file under
   `framework/core/java/`, registered in `SoftwareAndroidKeyStore`'s constructor via one `service(...)` line; the frozen
   crypto in `SoftwareAndroidKeyStore.java` is otherwise untouched. Re-run `KeystoreProbe` (must stay 6/6) + the board
   probe (now `validateAead=OK`) before merge.
3. Regression control: moodcairns lit; and any already-lit app using `EncryptedSharedPreferences` must stay lit.

## Files
- `src/adapter/core/SoftwareAndroidKeyStore.java` — the real provider (copied unmodified, for the probe build only).
- `src/adapter/core/KeystoreBoardProbe.java` — the on-board diagnostic (ship-able in the U11 JAR).
- `src/KeystoreProbe.java` — the Mac round-trip probe (6/6).
- `src/android/security/keystore/{KeyProperties,KeyGenParameterSpec}.java`, `src/com/.../X509V3CertificateGenerator.java`
  — minimal desktop stubs (probe build only; on-board these are the real boot-image classes).
- `run.sh`, `probe-output.txt`, `results.json`.

Evidence: moodcairns U9 hilog
`westlake-harness-u7-executor/benchmark/2026-10-01-u9-native/rollout/approved-j10g/boards/61b-r2/runner/cv2/…/cv2-com-lcdcode-moodcairns/hilog.txt`;
source `vm-copies/westlake-current/framework/core/java/SoftwareAndroidKeyStore.java` (+ `AppSchedulerBridge.java:475`
`install(no_backup)`).
