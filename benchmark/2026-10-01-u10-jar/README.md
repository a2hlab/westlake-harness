# U10 JAR — split base + Predicate (packlist); AccountManager assessment

Two parts, both for the outer loop to act on:

## 1. boot-assessment.md (which fixplan J entries are adapter-layer vs boot-image)
Predicate → runtime jar (Mac-doable, in this U10 jar). musicplayer Bitmap + libresudoku Locale → stock
boot classes the app calls directly, need a dex2oat boot-image rebuild (not Mac-reproducible) → image/
native lane. See `boot-assessment.md`.

## 2. U10 JAR (built here) = split base `11974b7b` + `com.android.internal.util.Predicate`
- Output `a41793ce6af614aff0030dd9907ed0fa64a960c37a3051b1c24ab66ae0c82129`, runtime_fp **`99c13a821ae4`**,
  boot_fp `4db882a81732`. Deterministic (built twice). `build/build_u10.py --extra-sources
  …/j10-prep/src/Predicate.java` on the split base (one version per round).
- **dexdump class-list diff vs the split base: +1 class `com/android/internal/util/Predicate`, nothing
  else** (185→186). The split base is itself method-identical to signed J10g `238ffc14`. See
  `u10-classlist-diff.md`.
- **Predicate beneficiary (run_index, U8): exactly 1 — `cv2-com-nbossard-packlist`** (ClassNotFoundException
  com.android.internal.util.Predicate). Placed in the runtime jar as the first candidate (app-referenced,
  boot lacks it); fallback if it still NoClassDefFounds on-board = BCP stubs jar + image rebuild.
- Offline gate `test_u10.py` **4/4** (Predicate interface shape + present + the only added class).

## AccountManager (fd-client) — NOT re-added (pre-existing stub)
The `"account"` binder stub already exists and is wired in the base (`LocalServiceBinders.account` +
`B8BindExtras` SERVICES + `B7BindFixes.apply`), and was in U8 — yet fd-client (`com.nextcloud.client`)
still died on null `accountManager` in U8. So this is **not a missing-stub gap**; a duplicate stub would
do nothing. fd-client needs a diagnostic (dagger/UserAccountManager path or the upstream Conscrypt/
SSLEngine wall), run against its own corpus (corpus100, not apps-v2) — **out of this U10 shard**. Detail +
recommendation in `u10-classlist-diff.md`.

## Window (pending U9 sign-off)
`u10-plan.json` — 5ea, `--detach`. Smoke controls + probe jar `a41793ce`; shard = packlist (Predicate
wall) + knot + caniwebview (regression). `offline_precheck.expect`: confirm = packlist no longer
ClassNotFoundException Predicate; refute = still NoClassDefFound (→ runtime jar not on the app's
resolution path, need BCP+image). runtime_fp self-computed `99c13a821ae4`.
