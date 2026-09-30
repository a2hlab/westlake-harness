# J4 prep notes (cc-t3, 2026-09-30) — accumulating targets before cx-bms's cluster table

J4 = next JAR-layer increment on J3 75c2068c. This file collects J4 candidates as the outer loop routes
them; the authoritative cluster/priority table is cx-bms's U2-scoring output (ACK 3285, pending). Build
only after that table lands.

## Routed to J4 by the outer loop (board 13:52 ACK 90)

### noice — IMediaRouterService null
- **Wall**: MediaRouter path NPEs on a null `IMediaRouterService` (route-A returns none).
- **Fixability**: **JAR, high confidence.** Same shape as the existing `WlMediaSession` helper (a local
  `ISessionManager` so a `MediaSessionCompat` service does not NPE on a null `MediaSessionManager`,
  build.py:64-66). A local `IMediaRouterService` stub (type-zero / no-op returns) installed at bind
  should clear the null. Verify the exact call site (getSystemService(MEDIA_ROUTER_SERVICE) fetcher vs a
  direct ServiceManager.getService) at J4 build time.

### fd-noice — NoClassDefFoundError android.net.ssl.SSLSockets
- **Wall**: okhttp/conscrypt references `android.net.ssl.SSLSockets` (API 29 util: isSupportedSocket /
  setUseSessionTickets); route-A's boot framework lacks the class → NoClassDefFoundError.
- **Fixability**: **UNCERTAIN — re-open my earlier "boot/oc-t4" classification (it was untested).**
  I previously routed this to oc-t4 on the rule "a non-BCP runtime JAR cannot supply a boot-package
  (android.*) class." That rule is UNVERIFIED for a class the boot is *missing*:
  - Parent-first delegation: the boot classloader is asked for `android.net.ssl.SSLSockets` first, does
    NOT have it, so the child PathClassLoader (the runtime JAR) gets a turn — and could provide it IF the
    JAR ships it.
  - BUT the build currently DROPS `android.*` classes (they are compiled only for linking and resolve to
    boot at runtime, per the OnlineConnectivityManager pass, build.py:75-90). Shipping SSLSockets means
    NOT dropping it — and then ART may reject a non-boot classloader *defining* a class in the `android.`
    package (prohibited-package). Whether ART allows it for a boot-missing android.* class is the crux.
  - **J4 minimal experiment (do before committing a fix)**: add a compiled `android.net.ssl.SSLSockets`
    (the two static methods, delegating to the socket) to the runtime JAR WITHOUT dropping it; deploy;
    check the fd-noice hilog. Three outcomes: (a) app finds it, TLS proceeds → JAR-fixable, keep in J4;
    (b) ART throws "Prohibited package name: android.net.ssl" at class define → genuinely boot, bounce to
    oc-t4 with that log as proof; (c) some other conscrypt wall behind it → new triage. AGENTS.md 做事
    方式 3: run the smallest key experiment, let the result decide — do not ship a fix on the assumption.
  - Also confirm whether the app reference is a direct symbol (compile-time) or `Class.forName` — a
    reflection lookup fails identically but a direct symbol may fail at verify/link time, which changes
    the seam.

## Pending
- cx-bms U2-scoring J4 cluster table (ACK 3285) — fold these two in by priority (apps-blocked count).
- After J3 board results (outer loop, 5ea+61b): if the NewPipe `[B8-AMB]` cause chain names a
  JAR-fixable internal cause, that becomes a J4 target too.
