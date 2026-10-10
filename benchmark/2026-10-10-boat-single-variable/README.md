# BoatAttack single-variable: runtime 18763dd4 → adc125f4 is the render lever (cc-t3 #91)

On-board single-variable experiment on 5ea (v2 + Enforcing + installer 51e1b525, same fingerprint as the lit demo).
Outer-signed render verdict + updated t2b criteria (master 2cbc57ab98).

## Setup (proven, Enforcing, no label wall)
- Baseline = route②d: adapter C8 `8ab85446` → `/system/android/lib64/liboh_adapter_bridge.so`, jar C9 `6333bcab` →
  `/system/android/framework/oh-adapter-runtime.jar`, 3 app-private (`libil2cpp f6b806b5`, `libunity 1bea0fae`,
  `libwestlake_bionic_signal_box 7a931c79`) → the installed BoatAttack lib dir. Applied with the v2 `boat-overlay.sh`
  (labels src→target context).
- **Single variable** = `/system/android/lib64/liboh_android_runtime.so`: U13 `18763dd4` → candidate `adc125f4`,
  bind-mounted + labelled `system_lib_file` per `selinux_label_recipe.sh` (4d97756aff). All binds SHA-verified; Enforcing,
  no seccomp/label wall (prereq: 5ea on v2 so `appdata-sandbox.json`=system_etc_file at appspawn-x preload).
- Install path (replicated from `demo-61b/window_hook.py`): `bm install boat-attack-a.apk` (sha `8dc63665`) →
  `prepare_sandbox` (uid 20011062) → overlay.

## Result — t2b PASS (outer-signed render + LAP proven)
| criterion (t2b 2cbc57ab98) | U13 runtime 18763dd4 | **adc125f4 runtime** |
|---|---|---|
| resolution / HUD sharpness | low-res stretched, HUD big+blurry | **full 1920×1200, sharp HUD** |
| colour | purple/tinted | **correct (blue water/sky, grey rock)** |
| boat moves on the 5-touch replay | stuck | **moves** (scene progresses start→beach→water-slides) |
| steering changes heading | — | **yes** (course navigated) |
| LAP advances | **stuck 0/3** (2:38 still 0/3) | **0/3 → 1/3** (LAP timer 01:51.293, opponent "Florin" passed) |

Five-touch replay = the PASS coords/timing verbatim (`20260924T080718Z-quick/five-touches.txt`):
accelerate `uinput -T -d 1740 1100 -i 9000 -u 1740 1100` (9 s hold) ×2, steer `uinput -T -m 220 1000 70/370 1000 -k 5000 700`,
reset `uinput -T -c 1440 1100 200`. Evidence (for outer sign-off, persisted):
`~/a2hlab-provision/5ea-boat-adc125f4/{boat-t20-adc125f4.png,boat-race-adc125f4.png}`,
`~/a2hlab-provision/5ea-boat-lap/{touch-1..5}.png` (touch-3-accelerate = LAP 1/3). Side-by-side original:
`00.Workspace .../20260924T080718Z-quick/{t3,t9,t15,touch-3-accelerate,touch-4-right}.jpeg`.
Note: `SetBufferColorSpace fail` still logs — it is in the GOOD PASS run too (not the purple cause).

**Conclusion: the render fix lives in `liboh_android_runtime.so` (adc125f4), confirming the source analysis
(`benchmark/2026-10-10-boat-pr03-render-port/SOURCE-PATCH-LIST.md`: the render hunks are runtime-side).**

## Next: ② autostart Boat layer (spec for the v2 installer) + ③ frozen draft
**② (needs cc-wiki installer update — not rushed this window):** to make the Boat layer survive a power-cycle on a v2 board:
1. `install-westlake-u13-autostart.sh` `stage_boat`: add `stage_boat liboh_android_runtime.so adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130`.
2. `westlake-u13-boat-overlay.sh`: add a `bind_over "$ARCH/liboh_android_runtime.so" /system/android/lib64/liboh_android_runtime.so adc125f4… 18763dd4…` (labels per recipe; it currently binds only adapter+jar+3private, no runtime).
3. Ensure the cfg wires the boat-overlay job after recover sets `sys.westlake.demo.u13.ready=true` (payload/ cfg, WITH_BOAT).
4. Install WITH_BOAT=1 on 5ea → `hdc target boot` → no-Mac verify Boat+HW+ZZ (Boat layer replaces shared files → HW/ZZ must still light).

**③ frozen draft:** `frozen-draft.json` here (NOT registered — for outer review). The Boat layer replaces 3 SHARED files
(adapter/jar/runtime) used by all 128 apps, so the gate is a non-regressing full 128 sweep (cx-t0, 5cd baseline → 5ea).

## Discipline
5ea restored to clean U13 (adapter `84695d62`/jar `bbc3f530`/runtime `18763dd4`), BoatAttack kept installed for the next
window, ZZ reverified lit. Zero frozen.json change (draft only). sources-boat staged on 5ea for re-use.
