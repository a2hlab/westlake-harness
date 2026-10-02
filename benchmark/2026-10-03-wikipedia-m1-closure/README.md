# #80 Wikipedia M1 closure: single-slot window lookup → U13 [M1-COPY] → window1 6/6 lit

#80 Wikipedia line, offline, no board. Wikipedia went from a flaky multi-window white to **6/6 lit** in U13 stage-A
window1. This closes the #80 line: the mechanism, the U13 runtime fix, the evidence chain, the interactive-UI judgment,
and the freeze assessment.

## The chain (mechanism → fix → evidence)
**M1 mechanism — single-slot cross-copy window lookup** (`2026-10-02-m1-session-slots`, root in the deployed bridge
`84695d62`): the bridge's `publishProcessWindowTarget` keeps **exactly one session id + one window pointer in two
process environment variables**. When an app opens ≥2 windows (multi-window), that single slot is overwritten by the
last `createSession`. The runtime's compat-shim bridge copy (`dlopen(…, RTLD_NOLOAD)` in its own namespace) is **not**
the copy that created the sessions, so its `sessions_` map misses and **every** BBQ window lookup falls through to the
one env-var slot → the **first-created (top) Activity loses the race and gets an empty Surface** → white. This is why
Jetpack Compose apps (wikipedia, fd-noice, x) were "alive but white" (DIGEST 2026-10-01 T7d): the Compose render target
had no Surface to draw into — the white was the empty Surface, not a Compose-pipeline wall.

**The U13 fix — `[M1-COPY]` in runtime `18763dd4`** (the R3 option of `m1-session-slots`, in
`android_graphics_compat_shim.cpp` of `liboh_android_runtime`): when the shim's own bridge copy returns null for a
session, it **asks the other loaded bridge copy** (located by `dl_iterate_phdr`, same file → same symbol offset); that
copy's `sessions_` holds every window it created, so the lookup is **rescued** → the top Activity gets its real Surface
→ lit. No env vars, bridge binary untouched. (`18763dd4` is the deployed U13 runtime carrying `[M1-COPY]` + the
AAssetManager lazy-init fix.)

**The evidence — U13 stage-A window1, 6 consecutive runs/key** (`evidence/window1-lottery-6of6.txt`, outer-signed
2026-10-03, candidate bundle `91272eaf` on 5cd/5ea, reference `2026-10-03-u13-reference` 122 lit):
| key | board | k/n | before M1 (lottery baseline) |
|---|---|---|---|
| **wikipedia** | 5cd | **6/6 lit** | 2/3 (`2026-10-03-lottery-baseline-kn`) |
| **fd-uhabits** | 5ea | **6/6 lit** | ~0.36 pooled |
| **fd-noice** | 5ea | **6/6 lit** | ~0.58 pooled |
6 runs/key is the sample size `2026-10-03-lottery-baseline-kn` showed clears per-key α=0.05 (fd-noice was the binding
constraint at 6). 6/6 all-lit rejects the baseline lottery rate → the lift is the `[M1-COPY]` fix, not luck.

## Is wikipedia's lit a real interactive UI? (evidence/interactive-judgment.txt)
- **Lit: yes, own UI.** All 6 t20 are outer-signed lit (full-sheet + suspect eyeball); each run reached
  `phase=controls` (the app's control/UI phase), consistent with the Wikipedia Compose UI drawing into the now-rescued
  Surface. Combined with the mechanism (empty Surface was the white cause), the Surface rescue directly explains the
  lit Compose screen.
- **Caveat (honest):** the stage-A capture recorded `status=foreground_unconfirmed` and did **not** dump the view tree
  (`views/leaves/text=None`) or input events for these runs — a capture limitation on this Compose app, **not** a
  regression. So "lit own-UI" is firmly supported (signed t20 + controls phase); **full interactivity (input dispatch)
  is not programmatically proven here.** If the freeze must certify interactivity, run one focused interactive probe
  (tap/scroll → screen change) at freeze time; the lit-and-foreground signing itself is already the accepted bar.

## Freeze assessment (freeze rule: ≥2 app t20 lit)
The M1 fix **meets the freeze bar**: it produces **≥2 app t20 lit** — fd-uhabits **and** wikipedia (and fd-noice = 3) —
each 6/6. Per the freeze rule this is enough to freeze M1. **Registration waits for the outer after U13 promotion.**
When frozen, split these into independent files with pinned SHAs:
| what | file / artifact | identity to pin at freeze |
|---|---|---|
| the `[M1-COPY]` source | `bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp` | the committed cpp (R3 change) |
| the changed object | `android_graphics_compat_shim.o` | per-object SHA from the N10b `build-runtime.py` (baseline `216b68fb` byte-identical, per-.o hashes) |
| the deployed runtime | `liboh_android_runtime.so` = U13 `18763dd4` | the deployed runtime SHA (carries `[M1-COPY]` + AAssetManager) |
| the alternative bridge route (not deployed) | `bridge-m1.patch` (`oh_window_manager_client.cpp`) | kept for a future bridge chain; R1 blocked (no `84695d62` build chain) |
(The exact `.o`/runtime SHAs are pinned from the U13 runtime build at freeze time; this lists the split, per the AGENTS
rule that on-board runtime artifacts carry their source snapshot + object + toolchain.)

## Rule this round sets
An "alive but white" app is not a render-pipeline wall by default — check the Surface first. The M1 single-slot lookup
gave the top Activity an empty Surface; the Compose white was downstream of that. One Surface-rescue fix lit the whole
Compose cohort (wikipedia/fd-noice/fd-uhabits). Prove a lottery lift with the sized k/n (6/6 vs a 2/3 baseline), and
separate "lit own-UI" (signed t20) from "interactive" (input dispatch) when the capture doesn't carry the latter.

## Files
- `evidence/window1-lottery-6of6.txt` — the outer-signed window1 6/6 for wikipedia/fd-uhabits/fd-noice + the baselines.
- `evidence/interactive-judgment.txt` — per-run record (phase=controls, foreground_unconfirmed) + the interactive caveat.
- `results.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push. The 6/6 signing is the outer's (`u13-stage-a-plan/window1-signoff`). M1 freeze registration
is the outer's after U13 promotion. Sources read read-only (`westlake-harness`, `-u7-executor`); the `[M1-COPY]` runtime
is cc-t3's/the runtime owner's to freeze.
