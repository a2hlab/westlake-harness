# Round-one localization addendum

The frozen forecast is unchanged (`240f0f85…`). This re-read covers **all six unresolved/input entries and all 12 member apps**. [Machine addendum](v1/plan-addendum.csv) includes the layer, lane, confidence, original file/line, remaining observation boundary and next check. [JSON](v1/addendum.json) also retains the original J1/N1/U1 labels.

| Entry | Evidence-based routing | Remaining limit |
|---|---|---|
| A01 — LibreTube | App/Coil maxSizeBytes boundary → J1 triage | Capacity producer is not logged; StatFs/native blame is unproven. Later TagSoup wall stays boot. |
| A02 — Immich | Framework class-surface candidate → J1, boot if loader scope requires | APK defines d7.c; it implements NsdManager.DiscoveryListener, absent from the 12 supplied exact-package/r17r JAR definition sets. Runtime resolution and sole-cause attribution remain unverified. |
| A03 — BreezyWeather/WifiAnalyzer/Catima | J1 triages exact null receiver; Catima narrows to widget refresh | No evidence yet identifies the null producer; no generic service stub is prescribed. |
| A05 — Feeder | **boot / oc-t4**: NetworkRequest.getNetworkSpecifier missing; main-thread uncaught error followed by exit(1) | The previous terminal matcher missed W-ROOM-SURVIVE. |
| A05 — PPSSPP | **native / cx-t0**: libppsspp_jni needs libGLESv2 in app domain; caught error followed by exit(-1) | Add to N03 namespace consumer checks, not an unidentified crash bucket. |
| A05 — fd-mobile | **native / cx-t0**, FZ-003 retention: asset-FD background worker failure | The log explicitly keeps the process alive; UI causality and U0 benefit are unknown. |
| A05 — Termux | App/JAR lifecycle → J1 triage: bind OK, finishActivity/TerminateAbility rc=0, no added window | Finish caller and intended successor are unknown; not evidence of EGL failure. |
| INPUT01 — Seal/Toutiao | **host input/assembly / cx-bms**: sidecar ELF gate before install | No app hilog exists for these attempts. Reconcile approved exact-input exceptions; do not alter frozen installer binaries. |
| INPUT02 — SubwaySurfers | **host identity / cx-bms** before install | Record contains expected pin, not proof of replacement bytes. Reconcile input identity separately. |

The class-surface check pins the APK and each JAR and records DEX class-definition offsets in [immich-class-surface.json](v1/immich-class-surface.json). It is a definition inventory, not a live boot-loader test. Historical source hilogs/records are read-only; exact line excerpts and hashes are in `v1/evidence/`. All 12 original frozen files still verify; the addendum regenerates byte-identically (17 JSON/CSV artifacts). No new predictions or UI verdicts were made.

Reproduce into a fresh directory: `python3 build_addendum.py --out NEW_DIR`. Public API implementation changes are separate lane work; this addendum does not authorize weakening FZ-001/002/003.
