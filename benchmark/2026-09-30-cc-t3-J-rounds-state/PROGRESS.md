# cc-t3 J-rounds state checkpoint (2026-09-30, context near full)

Lane **cc-t3** (Claude inner loop) in the app-lighting 横向点亮 campaign. Build worktree =
`westlake-harness-walls` (branch feat/bms-walls); reports = this worktree (`westlake-harness-t3`,
feat/app-lighting-t3). Deploy = bind-mount JAR overlay (`deploy_jar.sh`=5ea, `deploy_jar_61b.sh`,
`deploy_jar_5cd.sh` in westlake-harness-wiki/benchmark/2026-09-29-wikipedia-line). Board lock =
`scripts/lab/board_note.sh {lock,unlock,held} app-lighting <serial> cc-t3`. Reply to user in Chinese.

## JAR lineage (each cumulative, base b5 250958dc; build via dockbuild `DOCKBUILD_IMAGE=a2hlab-b5-java:24.04 DOCKBUILD_MOUNTS=<walls> dockbuild.sh run -- "python3 <walls>/benchmark/2026-09-29-bms-link-entry-walls/build.py <tag> b5"`)

| JAR | sha256 | walls commit | contents |
|---|---|---|---|
| r17s | 3b523289… | (superseded) | r17r + TLS wiring + RestrictionsManager + dlopen probe |
| r17t | ec583a26… | 6e9a5669 | r17s + AudioProductStrategy stub |
| r17u | 1eac63a6… | 9729ae9b | r17t + binaryeye getServiceInfo |
| J1 (interim) | 51d3e136… | 3a09dee8 | r17u + resolveService + getActivityInfo theme-correction |
| **J1-final** | **faf0782bb3a6dbf67a59022c35f95a1e3d33f35401f36d3a4ddbef309888180e** | **cdb82fe5** | J1 + J04 vibrator + **3 freeze splits** |
| **J2** | **0715c9645652742dbdececd35ad73fab70552c2245bf21be56c04fdc6d04488d** | **e099f7c4** | J1-final + NewPipe getPackageInfo("android") synthesis |
| **J3** | **75c2068ca9818ea8a61cd2d7e258ef70b36fb426c87036f2f8e2c472d47e6697** | (walls uncommitted) | J2 + [B8-AMB] full getCause() chain diagnostic (ActivityManagerBindProxy) + **AliasTargetTheme** (NEW: activity-alias target keeps its own AppCompat theme, fd-api). First J3 attempt 3cfad314 was WRONG (edited baseline-shipped LaunchActivityAliasProjection → silently dropped); 75c2068c uses new-helper+injection. |

vm-copies: `vm-copies/{r17s-3b523289,r17t-ec583a26,r17u-1eac63a6,j1final-faf0782b,j2-0715c964}/oh-adapter-runtime.jar` (+ receipt.txt).
Every build: changed_existing_classes = ONLY `adapter/activity/{AppSchedulerBridge,PackageManagerProjectionProxy}.smali` (the two smali injection targets). build.py has a tolerant `check_frozen.py` guard (skips until knowledge/frozen + scripts/lab/check_frozen.py merged into feat/bms-walls).

## Verified results

- **J1-final on 5ea (U0=v3c+53f00423+r17r+bg-installer), single JAR swap, --reinstall** (benchmark/2026-09-30-j1final-5ea/):
  - **binaryeye LIT** (t20 scan UI; `[B8-PM] projected getServiceInfo …MetadataHolderService`). J01 confirmed (also on cc-wiki's 5ea 32df r17u run).
  - **J04 vibrator PASSES its wall** (fd-reader: `[B8-FETCH] vibrator_manager SystemVibratorManager allocated (getVibratorIds->int[0])`; old "get length of null array" GONE, new death = app-internal `Null reference used for synchronization`).
  - **6 protected + HW: NO regression** (aegis/fd-k9/fd-tusky/markor/fd-etar/newpipe all t20=yes; helloworld lit).
  - compare_runs vs unified-assetfd-5cd = **variables:2** (JAR + board; 117 runtime files identical). `FROZEN checked=4 violations=0`.
- **binaryeye verified LIT twice** (cc-wiki 5ea 32df + my 5ea U0) — but SAME app; freeze needs a 2nd DISTINCT app.

## J1-target NEW first-walls after J1-final (from the 5ea J1 run hilogs) — ownership for the outer loop

| key | t20 | new first-wall after J1-final fixes | layer |
|---|---|---|---|
| fd-binaryeye | LIT | (lit; camera native video black region only) | done (JAR); camera video = native/cx-t0 |
| fd-reader | desktop | `Null reference used for synchronization (monitor-enter)` (app-internal null object) | **app-internal** (vibrator wall passed) |
| vlc | t5 only | `Failed to resolve attribute at index 13` (attr 0x7f040072) ConstraintLayout | **NOT JAR (resource layer) — FINAL, ground truth.** J3 read the J1-final 5ea hilog: `[B47-SLA]`/`[G2.5-SLA-PRE]` show OnboardingActivity `theme=0x7f1402ec` flowed CORRECTLY into LaunchActivityItem (resolveActivityTheme already right). The crash is a nested **forced** `TintContextWrapper.setTheme` under `Theme.VLC.Transparent (0x7f1402f9)` where attr 0x7f040072 won't resolve in OH's resource system → resource-projection lane (confirms r17t-audio row 147). NOT the ActivityClientRecord seam I guessed last — that guess is retracted. |
| fd-api | desktop | Theme.AppCompat ISE `You need to use a Theme.AppCompat theme` | **JAR — FIXED in J3.** Real cause (hilog `[B5-ALIAS]`): TermuxAPILauncherActivity is an **activity-alias**; target TermuxAPIMainActivity (AppCompatActivity) is instantiated with the alias's Theme.Translucent.NoTitleBar (0x1030237). Fix = new `AliasTargetTheme` helper injected after `LaunchActivityAliasProjection.apply`, re-resolves the TARGET's own AppCompat theme. Verify on board: expect `[B8-ALIASTHEME] ... re-resolved 0x1030237 -> 0x<AppCompat>`. |
| fd-meet | desktop | `NPE Collection.iterator() on null` (behind RestrictionsManager, built OK) | app-internal or a 2nd empty-projection |
| noice/fd-noice | desktop | EGL BAD_ALLOC (eglCreateWindowSurface/libhwui/abort); on 32df downstream `NoClassDefFoundError android.net.ssl.SSLSockets` | **native EGL → cx-t0**; SSLSockets → **boot/oc-t4** (non-BCP runtime JAR can't supply a boot class) |
| opencamera | desktop | EGL + `UnsatisfiedLinkError: system library is absent from the adapter manifest` | native → cx-t0 |
| fd-musicplayer | desktop | `can't create bitmap without a color space` (framework Bitmap); SessionToken resolution is secondary | framework/native (bitmap) → likely cx-t0 |
| fd-im-vector-app | desktop | `UnsatisfiedLinkError librealm-jni.so __FD_SET_chk symbol not found` (native realm); Sentry DSN is behind it | native → cx-t0 |
| fd-gallery | desktop | `NoSuchFieldError MediaStore$Images$Media.EXTERNAL_CONTENT_URI` | **boot/oc-t4** (field absent from adapter-mainline-stubs.jar; sget-object bytecode, no JAR hook) |

**JAR-layer new walls to still fix**: **vlc/fd-api theme-flow** (J02) remains JAR-layer for cc-t3 NEXT ROUND — but via the `ActivityClientRecord.activityInfo` / LaunchActivityItem seam, NOT getActivityInfo (proven not-queried-at-launch) and NOT ability-launch resolveActivityTheme (proven not the object the framework applies). This needs no J2 rebuild (J2 is this round's final); it's the next increment's target. Everything else is app-internal / native (cx-t0) / boot (oc-t4). **J2 0715c964 has no further JAR-layer additions THIS round.**

## Freeze inventory (benchmark/2026-09-30-jar-freeze-inventory/)

3 fixes SPLIT into single-fix files in J1-final (cdb82fe5), re-verified by the J1-final board run:
| entry | file (blob @ cdb82fe5) | evidence (≥2) |
|---|---|---|
| FZ-JAR-conscrypt (r17o) | JarVerificationProviderFix.java (c7b15f75511ec20e66bca2411fc1a872e61c7521) | droidify/amaze/antennapod t20 — READY |
| FZ-JAR-alarm (r17e) | AlarmVibratorFetcher.java (9309104882fc982e885ed164f89345d526560b41) | 5cd unified k9/android t20 + logs (fatal=0, alarm fetcher replaced) — READY |
| FZ-JAR-binaryeye (J1) | SelfServiceFallback.java (185c2299ff00baa3622fee1bf4e8dee0d6a4dfbe) | fd-binaryeye 5ea t20 — 1/2, needs a 2nd app |
Draft = `frozen-entries-draft.json` (for outer-loop registration). Relaxed threshold (user): ≥2 apps PASS the wall, ≥1 t20 lit + rest by logs. AlarmVibratorFetcher also carries the new J04 vibrator (fd-reader).

## Pending (outer loop's latest directive, mid-execution)

Directive: J2 (base faf0782b, one JAR merging all JAR clusters):
1. **NewPipe getPackageInfo("android")** — DONE in J2 0715c964 (AndroidFrameworkPackage). STILL TODO: add `ITE.getCause()` print at the in-process bind (diagnostic; not yet added).
2. **J1 targets still on desktop** — analysis above. Only **vlc/fd-api theme-flow** is JAR-layer and unfixed; the rest are app-internal/native/boot (documented above → outer loop routes). The theme-flow needs the correct seam.
3. **3 freeze splits** — DONE in faf0782b (J2's base) + re-verified.

So J2 0715c964 is FINAL for this round: it covers (1) NewPipe + (3) splits. (2)'s only JAR candidate — vlc/fd-api theme — stays JAR-layer but moves to NEXT ROUND (ActivityClientRecord.activityInfo seam), so no J2 rebuild this round. Note: AndroidFrameworkPackage.java already logs `[B8-ANDROIDPKG] getPackageInfo(android) threw <ITE.getCause()>` on the getPackageInfo interception (line 51); the separate "in-process bind site" ITE.getCause() diagnostic is a secondary/optional probe on an already-lit app and was NOT added (near-full context; not worth a rebuild for a diagnostic-only line).

Also pending from outer loop: J1-final **U1 three-board full 66 sweep**; **J2 board verify** (NewPipe); **register FZ-JAR-conscrypt + FZ-JAR-alarm**.

## Boards
5ea/61b/5cd all restored to their baselines and released after each run. No lock held now. Serials:
5ea=5ea34a4500000000000000001123012c, 61b=61b0657200000000000000000324012c, 5cd=1e3dd…=5cd1e3dd00000000000000000923012c.
