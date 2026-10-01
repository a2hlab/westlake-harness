# U10 JAR — dexdump class-list diff + run_index beneficiary + AccountManager finding

## U10 JAR
`a41793ce6af614aff0030dd9907ed0fa64a960c37a3051b1c24ab66ae0c82129` = split U10 base (`11974b7b`) +
`com.android.internal.util.Predicate` (packlist), built by `build/build_u10.py --extra-sources
…/j10-prep/src/Predicate.java`, deterministic (built twice identical).

## dexdump class-list diff (U10 vs split base 11974b7b)
- split base: **185** classes · U10: **186** classes
- **Added (1):** `com/android/internal/util/Predicate`  — the only change.
- **Removed:** none.

So U10 is the split base plus exactly one new class (the re-added pre-API-28 hidden interface). No other
class is added, removed, or renamed; the 185 base classes are set-identical (the split base was itself
proven method-identical to J10g 238ffc14).

## run_index beneficiary surface (U8 e953c0921536)
`cause ~ Predicate`:
```
cv2-com-nbossard-packlist   Caused by: java.lang.ClassNotFoundException: com.android.internal.util.Predicate
```
**Predicate beneficiary = exactly 1 key: `cv2-com-nbossard-packlist`.** No other corpus app hits the
Predicate wall. (The runtime-jar placement is a candidate per the boot-assessment — app-referenced class,
boot lacks it — to be confirmed on-board; fallback is the BCP stubs jar + image rebuild.)

## AccountManager (fd-client) — the "account" binder stub already exists; this is NOT a missing-stub gap
The U10 scope named an AccountManager service stub for fd-client modelled on the telephony stub. On
investigation, **that stub already exists and is already wired in the U10 base** (and was in U8):
- `LocalServiceBinders.get("account")` returns a local-Binder IAccountManager proxy whose `account()`
  answers "signed in nowhere" — empty account list, no features, no token, booleans false (exactly
  "返空账户,不伪造").
- `B8BindExtras.installServiceStubs()` has `"account"` in its `SERVICES` list and puts that binder into
  `ServiceManager.sCache`, so `getServiceOrThrow("account")` finds it. It is invoked from
  `B7BindFixes.apply` (`B7BindFixes.smali` → `B8BindExtras;->installServiceStubs()V`). All present in the
  U10 base jar.

**Yet fd-client (`com.nextcloud.client`) still died in U8** on
`NullPointerException: … method com.nextcloud.client.mixins.SessionMixin.<init>, parameter accountManager`
(`first-wall.json`), i.e. with the account binder stub already deployed. It also has an earlier
`MainApp.insertConscrypt → SSLEngine.getEnabledProtocols() on null` NPE (`npe-8.json`).

**Conclusion: the standard "account" binder stub is NOT fd-client's fix** — the binder is already non-null,
so `accountManager` is null for another reason (likely Nextcloud's dagger graph passing a null where its
`AccountManager`/`UserAccountManager` provider resolved null, or the SSLEngine wall upstream). Adding
another account binder stub would be a no-op duplicate. **Recommend: a short diagnostic window** (log
`getSystemService(ACCOUNT_SERVICE)` result + the Conscrypt/SSLEngine path for fd-client on the U10 jar)
**before** committing any fd-client J-layer code. Do NOT duplicate the existing stub. Outer loop decides.

## U10 effective J-layer delta
U10 adds **one** genuinely-new J-layer class over the signed U9/split base: `Predicate` (packlist). The
AccountManager "account" stub is pre-existing. fd-client needs diagnosis, not a duplicate stub.
