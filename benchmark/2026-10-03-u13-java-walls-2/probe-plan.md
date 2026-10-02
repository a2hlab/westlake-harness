# fd-api theme probe: ≤ 10 min board plan, riding the U13 window (disabled by default)

## What it answers

AppCompat throws "You need to use a Theme.AppCompat theme" when
`activity.obtainStyledAttributes(R.styleable.AppCompatTheme).hasValue(windowActionBar)` is false
(`AppCompatDelegateImpl.createSubDecor`). The logs we have show the *ActivityInfo* was given the right theme:
- `[B8-ALIASTHEME] … re-resolved 0x1030237 -> 0x7f120252`;
- `[G2.5-SLA-PRE] activityInfo theme=0x7f120252`.

They do not show the theme the *Activity instance* holds when AppCompat checks it.

What is static and settled (`theme-scan.csv`):
- `0x7f120252` = `Theme.BaseActivity.DayNight.NoActionBar`. Its default-config bag is empty (`size=0`), and its parent
  chain reaches `Theme.MaterialComponents.Light.DarkActionBar` → AppCompat.
- An empty launch-style bag is **not** unusual: 17 lit keys have one.
- What *is* unusual: fd-api's **application theme is a framework theme**, `@android:style/Theme.Material.Light`
  (`0x01030237`, not AppCompat), and it launches through an **activity-alias** (`TermuxAPILauncherActivity` →
  `TermuxAPIMainActivity`).
- Lit alias apps (fd-calendar, fd-notes, fd-gallery, fd-filemanager) all have an app-local application theme. If the
  Activity silently ends up with the *application* theme instead of the target's, those apps survive (their app theme
  is AppCompat-based) and fd-api dies.
- The probe tells which.

## Artifact

`oh-adapter-runtime-u13-probe.jar` = U13 runtime `0482c9b1` + `adapter.activity.ThemeProbe` + one needle
(`ThemeProbe.install()` right after `ProviderAuthorityRefs.resolve(bindData)` in `AppSchedulerBridge`).
- sha256 `6957f3f9…`, persisted at `$WORKSPACES/westlake-inputs/generations/u13-walls2-v1/`.
- Deterministic (built twice).
- `deployed_class_diff` vs `0482c9b1`: 0 dropped, 0 reshaped, only the 3 probe classes added.
- `oh-adapter-runtime-u13-both.jar` (`6790d500…`) is the same plus the WebView glue, if the outer takes the glue in
  the same window.

**Disarmed behaviour.** `install()` reads one OH parameter through `SystemProperties.get` and returns. No callback is
registered and nothing is printed, so the jar is behaviour-identical to `0482c9b1`.

## Steps (one board, inside the U13 window; ≈ 8 min)

| # | step | time |
|---|---|---|
| 0 | The board already runs the U13 set with the runtime jar replaced by the probe (or both) variant: single-file swap of `/system/android/framework/oh-adapter-runtime.jar`, a runtime PathClassLoader jar, so no image rebake. | (part of the U13 deploy) |
| 1 | `hdc -t <sn> shell param set debug.westlake.theme_probe com.termux.api,org.fossify.calendar` then `param get debug.westlake.theme_probe` (`debug.*` is not persistent; it clears on reboot) | 0.5 min |
| 2 | Run the single-key runner for **fd-api** (launch, t20 screenshot, hilog), then for **fd-calendar** as the control: lit, alias launcher, app theme `0x7f12000d` ≠ target `0x7f1202b1` | 2 × 3 min |
| 3 | `hdc -t <sn> shell param set debug.westlake.theme_probe ""` (disarm) | 0.2 min |
| 4 | `grep '\[THEME-PROBE\]' hilog.txt` for both runs | – |

**Abort rule.** No `[THEME-PROBE] armed pkg=com.termux.api` line means the app process cannot read the parameter.
Disarm and stop; the next window then needs a build-time allow-list variant. Do not retry inside this window.

## Reading the result (lines are `[THEME-PROBE] pre-create <Activity> …`)

| fd-api shows | fd-calendar shows | conclusion → fix layer |
|---|---|---|
| `themeResId=0x1030237` or `0x0` while `activityInfo.theme=0x7f120252` | `themeResId=0x7f12000d` (app theme) instead of `0x7f1202b1` | The Activity does not get its ActivityInfo theme. It runs with the application/default theme for every alias launch, and only fd-api dies because its app theme is not AppCompat. → JAR runtime: where `performLaunchActivity` takes `r.activityInfo` for alias launches. Prediction: fd-api moves; fd-calendar & co. get their real launch theme (visual change, watch). |
| `themeResId=0x7f120252`, `app:windowActionBar resolve=false`, stack has only the leaf style or names `NOT-FOUND` | resolves | Theme id right, resolution wrong (parent chain or an AssetManager without the app package; `assets:` line) → native resources (`nativeThemeApplyStyle` / parent lookup). |
| `themeResId=0x7f120252`, `resolve=true` from an AppCompat style, `hasValue=true` | – | The pre-create theme is fine; something between pre-create and `setContentView` swaps context/theme (AppCompat `attachBaseContext2` wrapper: the `base contexts:` line). → JAR, AppCompat context path. |

Every line also prints `uiMode` (night vs day selects which bag of `0x7f120252` applies) and the base-context chain.
