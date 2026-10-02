# The 4 unexplained white-cluster keys: two black, two white, four different causes (one is not a fault)

#80/#90, offline, no board. These are the keys `2026-10-02-white-vs-lit` could not separate: dddmodel2, fd-mobile,
itsdicey, fd-AppManager.

**Method.** Each key is dug on its own signing run against the 117 lit signing runs (`evidence.py` →
`evidence.txt`):
- its rare templates;
- window sessions with their Android window type, BBQ lookup outcome and SceneBoard zOrder;
- the ability lifecycle;
- the runtime probe's visibility and view-tree dumps;
- RS composition;
- APK static checks where the hilog stops (aapt2, dexdump).

**Result.** Each key has a mechanism with a direct witness. Two are new walls:
- **M5**: an Android dialog is stacked under its Activity window;
- **M6**: a finishing top Activity leaves its caller in the background.

One key (itsdicey) is not a fault: its correct idle screen is black. U13 (`18763dd4`, M1) moves **none** of the four.
This corrects the earlier "dddmodel2 may move" for M1; the reason is under dddmodel2 below.

## What was wrong before

- **M1 classification by Activity name hid dddmodel2.** `white-vs-lit/multiwin.py` merged VRIs by name, so the
  dialog window and the Activity window (both `VRI[MainActivity]`) looked like one. dddmodel2's top window is a
  **dialog** (`androidType=2`), not an Activity, so "top = last requested ability" missed it.
- **"Black" was read as a render failure.** itsdicey's DiceView paints opaque black by design.

## Black windows

### fd-mobile (Jellyfin), alive-black-window → no WebView (M2 family) + dialog buried under the Activity (M5)

- **The dialog.** `WebViewFragment.showOutdatedWebViewDialog` (dexdump, `org.jellyfin.mobile.webapp`) checks the
  WebView package and shows the "WebView outdated" AlertDialog (`dialog_web_view_outdated` "The WebView
  implementation used by your device is outdated."). The WebView is not loaded, so the Activity's
  `FragmentContainerView` stays empty (view tree: 1 content leaf, 0 text).
- **Window order.** The dialog window is created first: session 636, `androidType=2`; first `addToDisplay` refused
  for flags `0x20002`, retried without them. The Activity base window comes second: 637, `androidType=1`. Both get
  real surfaces (lookups rescued, M1 not involved), and RS composes them (182 lines).
- **SceneBoard stacks by creation order.** Both are sub-windows with zLevel 0, so `onSubSessionZLevelChange` gives
  index 0 → zOrder 103 for the dialog and index 1 → **zOrder 104 for the Activity window, on top**. Android puts a
  dialog (type 2) above its Activity (type 1). The visible window is the dark, empty Activity window: black.
- **Smallest check.** Already done statically from the hilog zOrder lines. On the board (≤ 15 min): `hidumper -s
  WindowManagerService -a -a` after t20 lists 636 under 637. Raising 636 (or re-adding the dialog after the Activity
  window) shows the "WebView outdated" dialog.
- **Predicted move:**

  | fix | result |
  |---|---|
  | U13 (M1) | 0 |
  | + M5 | the app's own "WebView outdated" dialog becomes visible: a WebView fallback page, not functional lit |
  | functional lit | needs a WebView renderer (M2) |

### itsdicey, alive-black-content → not a fault: the black canvas is the app's idle UI

- **The screen.** The toolbar is drawn (red, title) and DiceView fills the rest (1200×1794, DL=T, window composed:
  RS 26 lines).
- **onDraw paints black on purpose.** `DiceView.onDraw` begins with `canvas.drawARGB(255, 0, 0, 0)` (dexdump
  0x0005–0x0008), then draws a circle per touch point from a SparseArray. With no finger on the screen, the app
  draws exactly black.
- **The hint is hidden by the app itself.** The only other view, the hint `TextView` in `res/layout/content_main.xml`,
  has `android:visibility=2` (gone) in the layout.
- **Only visible difference from Android:** the toolbar title is `com.emmanuelmess.itsdicey.MainActivity` instead of
  the label "Its Dicey!". The label resources are zeroed (`[G2.5-PIB] ApplicationInfo … labelRes … zeroed`); that is
  cosmetic.
- **Smallest check.** Static is decisive. Board, ≤ 5 min: touch and hold the canvas, and a colored circle with a
  countdown arc appears.
- **Predicted move:** +1 by re-signing (own UI, the outer reads t20); no code.

## White windows

### dddmodel2, alive-white-window → dialog first (M1: its window gets an empty Surface) and under the Activity (M5)

- **Window order.** As in fd-mobile, a dialog (`androidType=2`, first `addToDisplay` refused for `0x20002`, retried)
  is created **before** the Activity window: sessions 686 then 687.
- **M1.** 686 is not the last-published session, so all 3 of its lookups are `empty` (`[M1 replay]`). 687 is rescued.
- **M5.** SceneBoard zOrder: 686 → 102, 687 → **103**, so the Activity window is on top. Its content is an empty
  `FragmentContainerView` (white).
- **Why U13 alone does not move it.** With M1, 686 gets its surface, but it stays under 687 (M5). The earlier
  white-vs-lit / M1 prediction "dddmodel2 may move" is withdrawn.
- **Smallest check.** Board ≤ 15 min on U13: `[M1-COPY]` for session 686 appears and t20 stays white (M5 is the
  remaining cause); `hidumper` shows 686 under 687.
- **Predicted move:**

  | fix | result |
  |---|---|
  | U13 (M1) | **0** |
  | M1 + M5 | +1 (the dialog becomes visible; medium, its content is unknown) |

### fd-AppManager, alive-white-window → the finishing top Activity leaves its caller in the background (M6)

- **Static sequence** (AMS lines + the runtime's G2.14as-VIS dumps):
  1. SplashActivity is launched, comes to the foreground and adds its window (session 662, rescued, view tree with
     the splash image and 3 text views).
  2. It starts **KeyStoreActivity**, theme `AppTheme.TransparentBackground`: translucent, transparent background.
     AMS brings that ability to the foreground and SceneBoard requests a new scene for it.
  3. KeyStoreActivity finishes in `onCreate` (VIS: `finished=true windowAdded=false lifecycleState=1`, no window ever
     added), and the runtime sends `finishActivity: OH TerminateAbility(token=0x7f352c5c30) rc=0`.
  4. AMS had already moved **SplashActivity to background**: `AbilityTransitionDone … SplashActivity, state:5` then
     `BackgroundLifecycle SplashActivity`. KeyStoreActivity follows into background.
  5. **Nothing re-foregrounds SplashActivity.** The last lifecycle event is 10.3 s before the hilog cutoff. No ability
     of the app is in the foreground: white.

  On Android a translucent Activity does not hide or stop its caller, and finishing it returns to the caller.
- **Population, the stable form** (≥ 2 abilities foregrounded, all end in background, a TerminateAbility, quiet
  ≥ 5 s): white 1/16, lit 0/117. Without the quiet condition, lit fd-organicmaps also matches, because its 6-terminate
  Splash↔DownloadResources loop is cut by the hilog end.
- **Smallest check.** Board ≤ 10 min: after the white t20, re-foreground the app (tap the icon) and expect
  SplashActivity's own UI. DIGEST 2026-10-01 07:09 already saw exactly this on U7: "回前台出自家「正在验证」闪屏" (back
  in the foreground it shows its own "verifying" splash).
- **Predicted move:** with an M6 fix (when a top Activity started from a live caller finishes, foreground the
  caller's ability; or keep the caller foreground when the started Activity is translucent): +1 to its own splash
  screen. Medium confidence: the splash may then wait for KeyStoreActivity's result.

## Predictions (`predictions.csv`)

| fix | moves | keys |
|---|---|---|
| U13 (18763dd4, M1 only) | **0** | – |
| re-sign (no code) | +1 | itsdicey |
| M5 (dialog above Activity) | +1 own-UI dialog | dddmodel2, with M1 |
| M5 | +1 WebView-fallback page | fd-mobile |
| M6 (foreground the caller) | +1 own splash | fd-AppManager |
| functional lit | needs a WebView renderer | fd-mobile |

**M5 regression watch.** 13 lit keys also create a dialog before their Activity window, for example the secuso
apps' first-start dialogs, NetGuard and RPN. Their t20 shows the Activity, not the dialog (sample checked: pin,
netguard, rpn). With M1 + M5 these dialogs appear on top: still own UI, but the t20 picture changes.

**Where M5 and M6 would be fixed.**
- **M5:** the Android window type (dialog vs base) → OH sub-window zLevel is chosen in the bridge's `createSession`
  (both are bound as zLevel-0 sub-windows of the MainSession). The deployed bridge has no reproducible source, so M5
  belongs to the hardened-bridge round (U14+), unless a runtime-side raise exists.
- **M6:** the bridge or runtime lifecycle adapter, on `finishActivity` of the top Activity.

## Rule this round sets

- Classify windows by **Android window type**, not by VRI name. A dialog and its Activity share a name.
- On OH, sibling sub-windows stack by creation order, so read zOrder from SceneBoard (`UpdateZOrderInner`).
- Before calling a black screen a render failure, read the view's `onDraw`: a canvas that paints black by design is
  the app's real UI.
- A lifecycle condition needs a stability margin before the hilog cutoff. A churning launch loop cut by the hilog end
  is not a final state.

## Files

- `evidence.py` → `evidence.txt` (per-key evidence, population rates of the two new features, static checks).
- `predictions.csv`, `results.json`.
