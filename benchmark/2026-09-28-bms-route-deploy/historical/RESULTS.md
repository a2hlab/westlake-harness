# app-breadth sweep RESULTS — board 5ea34a45 (LocalSend framework-2 base runtime a2hlab-framework-cab462ff)

> **UPDATE (final):** the tail 10 were re-swept after 5ea34a45 re-attached (physical re-plug; the detach also
> re-locked the screen — fixed with `power-shell timeout -o 3600000` + `uinput -T` swipe-unlock). The
> authoritative final table (66 launches, 13 distinct LIT, ~23%, tail results, the `burgerking`=McDonald's
> mislabel anomaly, and the on-device-confirmed GLESv1_CM finding) now lives in **README.md → 收官总表** and
> **glesv1cm-crux/DECISION.md**. The body below is the pre-tail 56-app snapshot.

Date: 2026-09-27. Runner: claude-3 (authorized self-run). Board **5ea34a45 ONLY** (hard-guarded;
`vm_sweep.sh` refuses if 5ea34a45 not in `hdc list targets` — never falls through to 61b06572 / 5cd1e3dd).

## Headline
- **Swept + classified: 56 apps. LIT 13. BLOCKED 43. Lit-rate ~23%.**
- Classification is **visual** (read each screenshot): the automation's `alive=yes` only means the
  appspawn-x child spawned — it does NOT distinguish "drew its own UI" from "host launcher tho fell back".
  The only discriminator is the screenshot. `screens/<key>.jpeg` holds every capture.
- **Interrupted**: board 5ea34a45 detached from `hdc list targets` at ~19:04 after `mcdonalds`. The 9
  tail commercial apps (burgerking, subwaysurfers, firefox, vlc, localsend, ppsspp, mindustry, x, noice)
  all hit `REFUSE: 5ea34a45 not attached` → NOT swept. `mcdonalds` snapshotted on-device but the board
  dropped during recv → screenshot never reached the Mac → unclassified. Resume needs 5ea34a45 reattach.

## Root-cause of the dominant blocker (markor probe forensics)
NOT a staging/launch bug. probe stages the APK and direct-launches the exact `MainActivity`
(`ASX_LAUNCH_ACTIVITY=net.gsantner.markor.activity.MainActivity`, `ASX_DIRECT_LAUNCH=1`,
`host_spawn result=0`, child alive, touchfwd attached). Decisive evidence from OH RenderService hilog:
**only LIT apps have a `*.MainActivity_content` node in the RS render tree** (auxio/aegis/ooniprobe/
wikipedia/antennapod); the un-lit apps' processes are alive but have **no window/render node** → host
launcher stays on screen. A staging bug would fail all apps identically; instead 13/56 light up through
the same pipeline ⇒ the wall is **per-app runtime window/Activity bring-up**, not "launch never happened".

## LIT (13)
| app | UI reached |
|-----|-----------|
| wikipedia | "All the world's knowledge" onboarding |
| termux | Termux terminal dialog + keyboard (bootstrap-install error is app-internal) |
| ooniprobe | "What is OONI Probe?" onboarding |
| antennapod | "Welcome to AntennaPod!" home + nav bar |
| aegis | "Aegis is a free, secure 2FA app" welcome carousel |
| fd-AppManager | App Manager KeyStore dialog (v4.1.1) |
| fd-auxio | Auxio player Songs/Albums/Artists tabs + "Music sources" |
| fd-com-amaze-filemanager | Amaze file list (/data/data/.../external) |
| fd-com-kunzisoft-keepass-libre | KeePassDX "Create your database file" |
| fd-droidify | Droid-ify Explore/Installed/Updates ("No available apps") |
| fd-fitness | Workouts "Set Preferences" dialog |
| fd-netguard | NetGuard firewall disclaimer dialog (I DISAGREE / I AGREE) |
| fd-noice | Noice "Focus, meditate and relax" onboarding |

Pattern: **all LIT are lightweight local-View apps** (file manager / password vault / podcast / 2FA /
firewall / white-noise / store / fitness). None require heavy native GL rendering, video, or a network feed.

## BLOCKED (43) by category (actionability order)
1. **native-lib missing (most actionable — has a name)**: `fd-stk` (SuperTuxKart) rendered its OWN SDL
   error dialog → `Error loading shared library libGLESv1_CM.so`. OH ships GLESv2/v3 but not legacy
   **GLESv1_CM**. → a libGLESv1_CM shim/symlink would unblock a class of GL/SDL apps.
2. **host-launcher fallback / alive-no-render (~38, the bulk)**: process alive, no MainActivity node in
   the RS tree = window/Activity bring-up silently fails. anki, newpipe, markor, opencamera, fd-android,
   fd-api, fd-app, fd-breezyweather, fd-calendar, fd-catima, fd-etar, fd-feeder, fd-fennec_fdroid
   (Firefox), fd-filemanager, fd-fluffychat, fd-gallery, fd-im-vector-app (Element), fd-immich, fd-k9,
   fd-kitchenowl, fd-libre, fd-libretube, fd-meet, fd-minetest, fd-mpv, fd-musicplayer, fd-notes,
   fd-organicmaps (GL map), fd-plus, fd-reader, fd-saber, fd-seal, fd-shatteredpixeldungeon (game),
   fd-tasks, fd-tusky, fd-tutanota, fd-uhabits, fd-wifianalyzer.
3. **black-render**: fd-mobile (window created, content painted black). **blank-white**: fd-client
   (window created, no content). **exited-to-desktop**: fd-binaryeye (process didn't hold; fell to OS
   home — QR scanner, camera HAL).
4. **base-mismatch**: toutiao — this board runs the generic LocalSend framework-2 base, not toutiao's
   delivery runtime (that lives on 61b06572). Host-launcher here; not a fundamental wall.

## Not swept (need 5ea34a45 reattach) — 10 tail commercial apps
mcdonalds (redo), burgerking, subwaysurfers, firefox, vlc, localsend, ppsspp, mindustry, x, noice.

## Cheap heuristic learned (still verify by reading)
Screenshot JPEG byte-size clusters: ~51.5 KB ≈ the identical host-launcher screen (likely BLOCKED);
>60 KB ≈ real content (likely LIT). BUT false-negatives exist (droidify's empty "No available apps" list
compressed to ~51.8 KB; organicmaps/desktop screens vary), so size is a pre-filter only — every verdict
here was confirmed by reading the image.
