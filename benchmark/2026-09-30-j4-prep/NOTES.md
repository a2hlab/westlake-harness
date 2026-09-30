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

## J4 delivered (1c1bbef) + J4.json triage (19 items) — 2026-09-30

**J4 = 1c1bbef** (base J3 75c2068c): NewPipe platform signature (AndroidFrameworkPackage) + noice
IMediaRouterService (WlMediaRouter). Built after OrbStack recovery; host-verified (cert parses X.509).
fd-api routed OUT (resource layer; cx-bms J4.json also labels it 层=资源).

**cx-bms J4.json triage by layer:**
- runtime-JAR (mine): noice (DONE) · fd-musicplayer (J5 candidate, see below) · maybe fd-meet /
  fd-im-vector (need diagnosis) · J4-null-producer 3 (fd-breezyweather/catima/wifianalyzer — getClass
  NPE, null producer unknown = investigation).
- NOT mine: J4-boot-api 5 (fd-feeder/gallery/plus/wikipedia/x = boot-jar missing method/field in
  adapter-mainline-stubs.jar; wikipedia = my T7) · fd-api (资源→oc-t4) · J4-tls-java 2 (fd-client
  SSLEngine / fd-noice SSLSockets = cc-wiki TLS or boot).

**fd-musicplayer (J4-media-session) — J5 candidate, JAR-fixable but native wall behind it:**
Wall: androidx.media3 `SessionToken(context, ComponentName(PlaybackService))` calls
`queryIntentServices(new Intent("androidx.media3.session.MediaSessionService").setPackage(self))` and
PlaybackService is not in the results, so it throws "Failed to resolve SessionToken ... Manifest doesn't
declare one of MediaSessionService/...". The OH BMS PM does not project the self-package's services with
their `<intent-filter><action>` for queryIntentServices. Fix = extend SelfServiceFallback (my binaryeye
getServiceInfo helper's domain) to answer `queryIntentServices` for the self-package by matching the
requested action against the manifest's per-service intent-filter actions. PREREQ to verify offline:
does ManifestComponentProjection / ManifestJsonFallback capture service `<intent-filter><action>`? (The
binaryeye path used getServiceInfo + meta-data, not intent-filter actions — may need to add action
parsing.) CAVEAT: a native/framework wall is right behind it —
`IllegalArgumentException: can't create bitmap without a color space` (fd-musicplayer hilog line 52109,
j3-61b) — so a SessionToken JAR fix advances the wall but does NOT light the app; lighting needs the
bitmap-color-space fix too (framework/native → cx-t0). Lower priority than a lighting fix.
