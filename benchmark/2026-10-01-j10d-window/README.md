# J10d window: the activity-theme root fix lights 10 of 12 (5ea, 2026-10-01)

**What was wrong.** Twelve cv2 keys died with AppCompat's "This Activity already has an action bar supplied by the
window decor" (or getActivityInfo NameNotFound). J9 / J10 / J10b attacked the symptom (NoTitle overlays); J10c's
diagnostic showed the activity resolved its *app* attributes from the parent theme (windowActionBar=true) although the
manifest gives it the NoActionBar child. Root (cc-t3, J10d): `AppSchedulerBridge.nativeOnScheduleLaunchAbility` zeroed
`activityInfo.theme` before `scheduleTransaction`; AOSP 14 `performLaunchActivity:3745` then fell back to the
(also zeroed) application theme.

**Fix.** J10d jar `57d62183…` restores `activityInfo.theme` from the manifest right before the launch transaction
(marker `[J10d-THEME]`), on top of J10's ActivityInfo synthesis.

**Result** (RUNTIME `f7fa0244c5a0`, BOOTIMAGE `4db882a81732`; facts `TOTAL keys=12 screenshots_captured=24/24
alive_t5=12 alive_t20=12`; outer read of every t20, contact sheets here): **10 of 12 lit**, all 10 not lit in the U8
sign-off (9 dead, privacyfriendlymemory launcher-foreground). itsdicey now draws its own action bar over a black body
(dead in U8); yahtzeedicer still shows the desktop.

**Rule.** One window, one run: the 10 are confirmed for U9 only by the U9 full sweep. The theme restore is a public
API fix with >= 2 apps lit at t20 -> freeze candidate once it ships in the U9 jar built from master sources.
