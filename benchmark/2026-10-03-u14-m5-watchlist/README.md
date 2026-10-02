# U14 M5 regression watchlist — the 13 dialog-first lit keys whose t20 picture changes (but stay lit)

Offline, board #90, no board action. M5 (cc-t3 `07fd530a`, `westlake-harness-t3/benchmark/2026-10-02-u14-bridge-r1r3`)
raises an Android `TYPE_APPLICATION` sub-window (a Dialog) above its Activity window. U10.1T8 has **13 lit keys that open a
dialog before their Activity** (`white-unexplained-4` `dialog_before_main`, lit 13/117). Today they are lit because the
dialog is pressed *under* the Activity, so the signed t20 shows the Activity's content. After M5 the dialog comes to the
top, so their **t20 picture changes** — it is still the app's own UI, still lit, **not a regression**. This watchlist
names each key, its dialog (from hilog `createSession` type + window name), what t20 shows now, and what t20 should show
after M5, so a U14 signer does not misread "the app's own dialog is now on top" as a fallback.

## Headline
All **13/13** keys are witnessed to have the exact M5 shape in their signed-lit run: a type-2 (TYPE_APPLICATION/Dialog)
window created before the type-1 Activity window, with the **dialog's zOrder below the Activity's** (`evidence/zorder-proof.txt`).
So M5 will move the dialog on top for **all 13**. Expected post-M5 verdict for every one: **lit, own UI** — the only
change is which own-UI layer is on top. A true regression would be a **white/black** t20 or a **non-app** surface, not a
different own-UI screen.

## The 13 keys (full table in `watchlist.csv`, witness in `evidence/`)
| key | component (VRI) | dialogs→Activity | zOrder d<a | now (U10.1T8 t20) | after M5 (predicted t20) |
|---|---|---|---|---|---|
| cv2-com-asdoi-timetable | com.ulan.timetable…MainActivity | 2 | 102<104 | lit: timetable UI; 2 dialogs under | own dialog on top (lit) |
| cv2-com-ath0-rpn | com.ath0.rpn.Main | 1 | 102<103 | lit: RPN UI; dialog under | own dialog on top (lit) |
| cv2-com-github-dfa-diaspora-android | …diaspora_android…MainActivity | 1 | 102<103 | lit: diaspora UI; dialog under | own dialog on top (lit) |
| cv2-com-harr1424-listmaker | com.harr1424.listmaker.MainActivity | 1 | 102<103 | lit: listmaker UI; dialog under | own dialog on top (lit) |
| cv2-com-knirirr-beecount | com.knirirr.beecount.WelcomeActivity | 2 | 102<104 | lit: BeeCount UI; 2 dialogs under | own welcome dialog on top (lit) |
| cv2-de-koelle-christian-trickytripper | …trickytripper.TrickyTripperActivity | 1 | 102<103 | lit: TrickyTripper UI; dialog under | own dialog on top (lit) |
| cv2-org-secuso-privacyfriendlymemory | …privacyfriendlymemory.ui.MainActivity | 1 | 103<104 | lit: memory-game UI; dialog under | own first-launch dialog on top (lit) |
| cv2-org-secuso-privacyfriendlypin | …privacyfriendlypinmnemonic.MainActivity | 1 | 103<104 | lit: pin UI; dialog under | own first-launch dialog on top (lit) |
| cv2-org-secuso-privacyfriendlyruler | …privacyfriendlyrulerapp…RulerActivity | 1 | 103<104 | lit: ruler UI; dialog under | own first-launch dialog on top (lit) |
| fd-netguard | eu.faircode.netguard.ActivityMain | 1 | 102<103 | lit: NetGuard UI; dialog under | own first-run dialog on top (lit) |
| fd-stk | org.supertuxkart.stk.SuperTuxKartActivity | 1 | 103<104 | lit: SuperTuxKart UI; dialog under | own dialog on top (lit)¹ |
| newpipe | org.schabi.newpipe.MainActivity | 1 | 102<103 | lit: NewPipe UI; dialog under | own first-run dialog on top (lit) |
| opencamera | net.sourceforge.opencamera.MainActivity | 1 | 102<103 | lit: OpenCamera UI; dialog under | own intro dialog on top (lit) |

¹ fd-stk is GL-based; if it fails to light after M5 the cause is its GL path, not M5 (score separately).

## The dialog's identity — what the hilog does and does not give
The `createSession` line gives the window **type** (`androidType=2` = TYPE_APPLICATION / Dialog) and **name** (the same
component as the Activity, e.g. `org.schabi.newpipe.MainActivity`). The dialog and the Activity therefore share one VRI
name; they are told apart **only by `androidType`** (DIGEST 2026-10-02 line 690). The app's own `Dialog` *subclass* is an
in-process `View` and is **not** named in the hilog — OH logs only its own `WMSDialog`/`SCBDialog` wrapper. So the
hilog-authoritative dialog identity is "**a type-2 window under `<component>`**" (column `dialog_identity_hilog`). The
"what the app shows" column (`dialog_app_hint_inference`) is an app-level guess (first-run / onboarding / help dialog),
**explicitly not from the hilog**; a signer should rely on the type-2 witness, not the hint.

## Why this is the right signing frame (what was wrong before)
`white-unexplained-4` could not separate the **white** `dddmodel2` from these 13 **lit** keys because **all 14 share the
identical window topology**: a type-2 Dialog created first (lower zOrder), a type-1 Activity second (higher zOrder, on
top). They diverge only in whether the *Activity's* Surface has content: `dddmodel2`'s top Activity gets an **empty**
Surface (that is **M1**, a different defect) *and* its dialog is pressed under (M5) → white; these 13 have a **content-
ful** Activity → lit, despite the same M5 press-under. So **M5 and lit/white are orthogonal**: M5 decides only *which
own-UI layer is on top*, never whether the app lit. M5 alone does not move `dddmodel2` (it needs M1 too) and does not
turn any lit key white — it only re-stacks the 13's own UI.

## Sign-off rule this round sets
For these 13 keys under U14-with-M5, **an own dialog on top of the Activity is the expected, correct M5 result — score
lit.** Judge the window by `androidType`, not the VRI name. Do **not** file a regression for "a dialog I did not see on
U10.1T8": that dialog was always created, only pressed under; M5 raising it is the fix working. A regression is a t20
that is **white or black**, or shows a **non-app** surface — not a different screen of the app's own UI. If a key both
lit before and lit after but with a different own screen, that is **expected (on this list)**, not a fallback. (A key
*not* on this list that suddenly shows a dialog-on-top would be worth a look — but all 13 known dialog-first lit keys are
enumerated here.)

## Files
- `watchlist.csv` — the 13-key table: component, dialog count, dialog/Activity zOrder, hilog dialog identity, app-level
  hint (inference), current t20, predicted post-M5 t20, and the per-key sign-off rule.
- `evidence/zorder-proof.txt` — per key, every window session's `androidType` + final `zOrder` (dialog zOrder < Activity
  zOrder, 13/13), with the signed-lit run path. Parsed with the `white-unexplained-4/evidence.py` regexes.
- `evidence/createSession.txt` — the `createSession` order per key (type-2 before type-1) + the M5 mechanism and the
  `07fd530a` fix (what it changes in `oh_window_manager_client.cpp`).
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; nothing deployed. The M5 patch `07fd530a` and the U14 baseline candidate (`e34de8ab`, cc-t3) are not
mine to deploy — this is the observation list for whoever signs U14-with-M5. Sources read read-only from the shared
checkout and sibling worktrees (`westlake-harness`, `-t3`, `-u7-executor`); no other worktree was modified.
