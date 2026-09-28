# McDonald's (com.mcdonalds.app 26.31.1, RN) recheck on current runtime — #48 horizontal (2026-09-27)

Goal: confirm McDonald's lights up to first usable screen (old record: home dashboard + 5 bottom tabs).
Result: **launch PASS, RN renders first screen (sign-in sheet), but "dashboard + 5 tabs" NOT reached on the
current runtime** — old record is stale relative to the deployed westlake branch.

| Item | Outcome |
|------|---------|
| Stage + launch | PASS — probe_source_app.py staged runtime `a2hlab-source-489789dd…`, spawned child 21373, RN engine up, stable ~5 min no crash |
| First usable screen renders | YES — "Sign in or sign up" bottom sheet: Terms&Conditions / Privacy / California notice + Continue with Facebook / Google / Email (real logos, styled RN buttons). This is the genuine v26.31.1 first screen. |
| Dashboard + 5 tabs | NOT reached on this runtime |

## Why the dashboard is not reached (two independent gates)
1. **Mandatory sign-in sheet, not dismissable here**: back key broken (prior M4), no guest/skip option, OAuth
   providers (Facebook/Google) unavailable on OH, and swipe-down / scrim-tap / back all failed to dismiss it.
2. **Current runtime lacks McDonald's dashboard fixes**: the deployed westlake is `22b9453`; the fixes that
   previously let the dashboard render are NOT ancestors of it —
   - `2f70628` (M1 home dashboard: Realm sysconf(39) → OH musl `_SC_BC_STRING_MAX`=1000 → unaligned mmap refused) — NOT in runtime
   - `9b8b861` (M2 WebView start-up: in-process IUserManager threw in a JNI callback → Chromium abort) — NOT in runtime
   So even past login, the dashboard would hit the Realm mmap blocker.

## Verdict
McDonald's **lights up to its first usable screen (sign-in sheet) — RN + React rendering confirmed end-to-end**.
The literal "dashboard + 5 tabs" from the old record is **stale for the current runtime branch (22b9453)**: it
was reached on a prior branch carrying 2f70628 + 9b8b861. To reach the dashboard now: (a) deploy/build a runtime
that includes those two fixes, and (b) drive past the login gate (needs a dismiss path or credentials; OAuth
providers absent on OH). Not a clean quick win on the current runtime. Detailed prior analysis:
benchmark/2026-09-23-mcdonalds-ordering/ (M1–M4), benchmark/2026-09-22-mcdonalds-signin/.

## Layout
| Path | What |
|------|------|
| mcdonalds-signin-sheet-first-screen.png | first usable screen (RN sign-in sheet) rendered on current runtime |
| mcdonalds-child.stderr | child stderr (surfaces composited, no crash) |
