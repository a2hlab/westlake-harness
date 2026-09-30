# r17s verify on 61b (background-launch installer) + antennapod clean-install A/B (2026-09-30)

**One line:** r17s `606dd2e3` on 61b: its `restrictions` fetcher stub is active and advances **fd-meet**
past the RestrictionsManager NPE (but a new null-`Collection.iterator` NPE is behind it — not lit);
regression controls **markor/etar/amaze** hold; and a same-board single-variable A/B shows **AntennaPod
clean-installs LIT under both r17s and r17r** — so the 5ea r17r clean-install NPE is a *board* difference,
not a JAR regression.

## What this run sets as the rule (background-installer board)

> On the **background-launch installer** board (61b, current), the installer steals foreground focus at
> launch. `bms_batch --focus-check` therefore reports `focused PID is not target` for **every** key, and
> `facts.txt` `alive`/`child_hilog` counts are **unreliable** — e.g. `vlc` shows `child_hilog=0` in facts
> while its `hilog.txt` has **55605** lines and `VLCApplication.onCreate` ran with no FATAL. **Read the t20
> screenshot + the raw child hilog; do not trust the facts liveness counters on this board.** (FLAW-007.)

## Deploy / rollback (bind-mount stack, one-umount rollback)

61b baseline at lock time = **r17p `a0ed5c4f`** (cx-t0's installer state), 1 mount layer. Sequence:
r17s `606dd2e3` mounted as layer2 → antennapod run → r17r `dd4f0eae` mounted as layer3 → antennapod run →
rollback layer3 (→ r17s) → rollback layer2 (→ r17p). Final `status`: effective (shell==appspawnx) =
`a0ed5c4f`, **layers=1** — board restored to exactly the lock-time JAR, then lock released.

## fd-meet (the r17s target) — advanced, not lit

- `hilog: [B8-FETCH] restrictions fetcher replaced (prev=android.app.SystemServiceRegistry$65)` — the r17s
  stub **is installed and hit**; the RestrictionsManager NPE is gone.
- New wall behind it: `java.lang.NullPointerException: Attempt to invoke interface method
  'java.util.Iterator java.util.Collection.iterator()' on a null object reference` →
  `Unable to start activity ComponentInfo{org.jitsi.meet/org.jitsi.meet.MainActivity}`.
- **Verdict:** honest progress (one wall cleared), **not** a lit claim. Next fd-meet wall = the null
  `Collection` (app-internal, or a second empty/absent projection the stub should populate).

## Regression controls (screenshots, since focus-check is unreliable here)

| key | verdict | evidence |
|---|---|---|
| markor | **LIT** | `markor/t20.jpeg` = document browser (school/travel/work, Files/To-Do/QuickNote tabs) — r17r fix held |
| fd-etar | alive | facts `t5=yes t20=yes child_hilog=24251` (r17q fix held) |
| fd-com-amaze-filemanager | alive | facts `t5=yes t20=yes child_hilog=30484` |
| vlc | ran, t20 off-screen | 55605 child-hilog lines, `VLCApplication.onCreate`, no FATAL; `vlc/t20.jpeg` = desktop. **Not attributable** to r17s (launch-only vs r17p reinstall + JAR = multiple variables). |
| fd-api | dead (expected) | termux.api / Theme.AppCompat cluster, dropped per outer loop |

## AntennaPod clean-install A/B (the outer-loop add-on) — the decisive part

Outer loop: under the background-launch installer, antennapod **must be clean-installed** (`--reinstall`);
`--launch-only` reuses an already-configured app and skips the first-run `restartUpdateAlarm`/WorkManager
path where the **5ea r17r** NPE (`FeedUpdateManager` instance null) appeared.

Same board **61b**, same **boot_id `58aef9fc`** (no reboot), same APK, same `--reinstall`; **only variable =
the JAR**:

| JAR | verdict | t20 |
|---|---|---|
| r17s `606dd2e3` | **LIT** | `runs-reinstall/r17s-antennapod-reinstall/.../antennapod/t20.jpeg` = AntennaPod welcome (`欢迎使用 AntennaPod!`) |
| r17r `dd4f0eae` | **LIT** | `runs-reinstall/r17r-antennapod-reinstall/.../antennapod/t20.jpeg` = same welcome |

`compare_runs.py` could not auto-run (these runs predate `runtime-fingerprint.txt`). **By hand (FLAW-008):**
`board=61b (same) · boot_id=58aef9fc (same, no reboot) · jar 606dd2e3(r17s) vs dd4f0eae(r17r) = exactly one
variable`. Both LIT → **the JAR is not the cause**; the 5ea r17r clean-install NPE is a **board (5ea vs 61b)
difference**, not reproduced on 61b under either JAR. No PowerExemption/restartUpdateAlarm fix is warranted
into r17s on this evidence.

> Aside: r17r/r17s hilog do carry an appspawn-x class-linker warning for `FeedUpdateManager`
> (`garbageSetBits=1 (EXPECT 0 => … clone@slot0)`, the same `[IFACE-BITS]` family as vlc's
> `VLCApplication`). It did **not** fault on 61b. If the 5ea NPE is ever chased, that vtable-clone path in
> the **generation's class-linker** (not this runtime JAR) is the place to look.

## Files

- `results.json` — per-key verdicts, deploy/rollback trace, the by-hand FLAW-008 variable line.
- `runs/r17s-61b/.../` — launch-only sweep (7 keys) with t5/t20 + facts.txt.
- `runs-reinstall/{r17s,r17r}-antennapod-reinstall/.../` — the clean-install A/B with t20 screenshots.
