# Framework smali patch: X telephony + LocalSend Impeller (#48 horizontal, 5ea34a45) — 2026-09-27

Applied claude-3's framework-fix.patch as a surgical smali patch to the deployed **adapter-runtime-bcp.jar**
(BCP, same jar as CLAMP48), rebuilt the boot image (host dex2oat, oat 247), deployed to 5ea34a45 and tested.
**61b06572 (Toutiao demo) was never touched.**

## Pipeline (validated end-to-end)
baksmali 3.0.9 (dex 039) → 4 smali edits → smali 2.5.2 assemble (dex 037, dex2oat-accepted) → jar → host
dex2oat (`.../verify/out/host-tools/host/objects/bin/dex2oat`, LD_PRELOAD libmap32bit.so, compiler-filter=verify,
27 boot files, all oat 247) → overlay boot/ + fw/adapter-runtime-bcp.jar into each app RT + chown.
patched jar sha256 `a3069ada151d58ff…` (all 4 edits). dex2oat verify PASSED → smali is valid.

## The 4 smali edits (patch_smali.py; + AppSchedulerBridge edit applied separately)
1. `LocalServiceBinders.get()` — early no-op ITelephonyRegistry: reuse the existing pure-DEFAULT Answers
   (`$$ExternalSyntheticLambda2` → `alarm()` → returns the DEFAULT sentinel; the `$1` proxy maps DEFAULT →
   type-default), so `proxy(name,"com.android.internal.telephony.ITelephonyRegistry",lambda2)` = `(call,args)->DEFAULT`.
2. `OHServiceManager.getService()` — route `"telephony.registry"` → `LocalServiceBinders.get(name)` (before
   lookupAdapter's default:null). (getService, `.registers 5`; NOT checkService `.registers 2`.)
3. `ApplicationMetaDataReader.populate()` — inject `EnableImpeller=false` (guarded by containsKey).
4. `AppSchedulerBridge.directLaunchNoBms()` — direct-launch builds an EMPTY `ai.metaData` (bypasses
   PackageInfoBuilder/ApplicationMetaDataReader), so #3 never runs for a direct-launched app; inject
   `EnableImpeller=false` right after `ai.metaData = new Bundle()`. (`.registers 14`→`16` for v9/v10 scratch.)

## Results on 5ea34a45
- **X (Twitter) telephony fix: EFFECTIVE ✅** — the `ITelephonyRegistry.listenWithEventList on null` NPE is GONE
  (0 refs; `com.twitter.util.telephony.a.run` passes). X advances past telephony into WebView/Chromium init and
  then hits a **NEW deeper blocker**: `Fatal signal 5 (SIGTRAP)` during Chromium bring-up (ASurfaceControl NDK
  procs missing + Chromium signal handlers). So X is NOT at first screen — new WebView SIGTRAP wall. This run
  also **validates the whole smali+boot-image pipeline** (the patched BCP is loaded and active).
- **LocalSend Impeller-off (edits 3+4): INEFFECTIVE ❌** — `[DIRECT-LAUNCH] ApplicationInfo built` confirms edit 4
  ran and injected `EnableImpeller=false`, but LocalSend crashes IDENTICALLY: `pc=0` at **libflutter+0x4b6560**
  (crash LR low bits `…6560` match the pre-patch run exactly). **This Flutter build IGNORES the `EnableImpeller`
  meta-data (opt-out deprecated — claude-3 saw `[Action Required]: Impeller opt-out deprecated`).** The intent
  shell-arg path (`--enable-software-rendering`) is also dead: a RELEASE Flutter app's FlutterActivity only reads
  intent shell-args when debuggable. So the meta-data / intent Impeller-off fix cannot disable Impeller here.

## Verdict / next
- Telephony fix is a validated, reusable framework win (jar `a3069ada`); X now blocked on WebView SIGTRAP (separate).
- LocalSend needs the DEEPER path (claude-3's alternative): a **GLES ext-proc shim** — deploy an eglGetProcAddress
  logger to name the NULL extension proc Impeller calls at slot #468, then provide/stub it (so the ProcTable slot
  is non-null), OR binary-patch libflutter. Meta-data Impeller-off is a dead end on this build.

## Files
| Path | What |
|------|------|
| patch_smali.py | edits 1–3 (edit 4 = AppSchedulerBridge, applied inline) |
| build_boot_5ea.sh | dex2oat boot-image build (oat 247) |
| adapter-runtime-bcp.patched.jar | all 4 edits, sha a3069ada (telephony fix reusable) |
| x-telephony-fixed-then-webview-sigtrap.stderr | X: NPE gone, new WebView SIGTRAP |
| localsend-impeller-metadata-ineffective.stderr | LocalSend: same libflutter+0x4b6560 pc=0 (meta-data ignored) |
