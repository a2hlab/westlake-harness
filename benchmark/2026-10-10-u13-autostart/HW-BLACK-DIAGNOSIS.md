# HelloWorld "black" under v2 (5cd) — RESOLVED: capture-state artifact, HW lights under v2 (2026-10-10)

**Conclusion (overturns the earlier "black, unexplained" and the "5cd-specific black" hypotheses):**
5cd HelloWorld **renders the full UI under v2+Enforcing** when captured foreground + screen-unlocked. The earlier
"t20 black" shots were `snapshot_display` taken while the screen was **locked** (`SCBScreenLock`, focus window 15) or
the activity had been **backgrounded** (`activityStopped state=10`) — i.e. a **capture-state artifact**, not a render
failure, not a v2-vs-deploy gap, and not a per-app quirk. This agrees with the outer's 5ea evidence (5ea v2 HW lit):
**both boards light HW under v2.** There is no divergence to hunt.

## Decisive evidence (`evidence/5cd-v2/as-helloworld-foreground.jpeg`, 84 KB)

Same board, same v2 autostart state (uptime 7742 s → no redeploy since the v2 reboot; `state=READY`,
boot_id `900dd8cf-a384-4693-bb02-77b26c234636`, libinstalls `/system/lib64 = 51e1b525` route-a), same HW bundle. The
only change from the "black" captures: **one `uinput` swipe-up to dismiss the lock, then verify `Focus window: 28` is
`com.example.helloworld` before the shot.** Result — the complete HelloWorld UI:

- title **"Hello World!"**, **CHANGE COLOR** button
- **Lifecycle log: CREATED → RESUMED → PAUSED → STOPPED → RESUMED**
- **START SECONDACTIVITY / BIND HELLOSERVICE / UNBIND HELLOSERVICE / L12 VIDEO PROBE** buttons

Full color, full content, fully composited (RenderService skia: `SurfaceNodeDrawable DrawCommSurfaceWatermark
Name:com.example.helloworld/...MainActivity` — RS compositing HW's surface node).

The rendered lifecycle log is **self-proving**: `…PAUSED → STOPPED → RESUMED` is exactly the earlier
background→foreground cycle (the `state=10` at 11:29:19 I had flagged as a possible failure), followed by this clean
foreground relaunch that **RESUMED and redrew**. One `CREATED` → same instance → HW draws whenever it is foreground.

## Why the earlier captures were black (and 5ea's weren't)

| | 5cd (my captures) | 5ea (cx-t0 smoke harness, outer-seen) |
|---|---|---|
| Who/how captured | manual tap + `snapshot_display`, **no unlock** | autonomous smoke harness |
| Screen state at shot | locked (`SCBScreenLock` focus) / HW backgrounded | foreground |
| Result | **black** (lock screen) | **lit** |
| Render capability | **lit when foregrounded+unlocked (this doc)** | lit |

The "5ea lit vs 5cd black" difference the outer saw is a **capture-harness difference, not a board/runtime difference.**
A Unity game (ZigZag) survived my earlier captures because it holds a wake-lock and runs fullscreen-immersive (stays
foreground, keeps screen awake); an ordinary ArkUI app (HelloWorld) lets the screen re-lock, so a delayed snapshot
caught the lock screen.

## What this confirms about earlier flagged anomalies (all non-causal)

- **`/system/android` double-bind on the first-spawned child**: HW renders fully → the double-bind (identical bytes,
  file resolution unaffected) is **confirmed non-causal**, as flagged.
- **GLES-load-fail (`libGLESv3.so … ndk no inherits, errno=2`, ×66) + `Bufferqueue SetMetadata -5`**: present under
  BOTH v2 and the deploy baseline, and HW lights anyway → board-wide noise, **non-causal**, as flagged.
- **spawn/domain/caps, SELinux labels, env/boot-image, app-crash**: all previously ruled out; still ruled out (HW is
  up, foreground, drawing).

## The "修法" (it's the capture method, not the board)

No board or payload change is warranted. The fix is the **capture discipline**, now a DIGEST pitfall:

> After `power-shell wakeup`, `snapshot_display` can capture the **lock screen / a backgrounded activity**, not the
> app. Before trusting a "black" screenshot: (1) dismiss the lock (`uinput` swipe-up or keyevent), (2) verify
> `hidumper -s WindowManagerService` **`Focus window` == the target app's persistentId**, then capture. A "black" shot
> with focus on `SCBScreenLock`/desktop is a **capture artifact**, not a render failure — do not report it as lit=0.

This also tightens the `facts.txt` / screenshot-ground-truth rule: a screenshot is ground truth **only once focus is
verified on the target window**; otherwise it is ground truth about the *lock screen*.

## Board state

5cd read-only throughout this diag (launched/foregrounded HW, swipe-unlock, `snapshot_display`, read hilog + /proc; no
`/system` write). v2 state intact (libinstalls `51e1b525`, autostart enabled, READY). 5cd UNLOCKED on completion.
