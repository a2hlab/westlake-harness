# t2b — BoatAttack on the demo board's unified state (static shared-path comparison + route judgment)

#90, **static / zero-board / not pushed** (demo-baseline campaign #91, contract `specs/demo-baseline/t2b-boatattack.spec.md`).
Can `com.Unity3d.BoatAttackDay` (APK `8dc63665…`, a 1920×1200 Unity racing demo) run on **our unified state (U13)** plus
only BoatAttack's **three app-private files** — without swapping the whole runtime generation? This is the offline
difference table the spec's `demo_baseline_boatattack_static` scenario requires, plus the route call.

Sources (read-only): BoatAttack = `~/orca/00.Workspace-games-ad1ab0a7` (branch `games/boatattack-repro`, HEAD `43ec24af9`),
bundle `strict-boat-assembled-20260924T074522Z-25403`. Our side = U13 (deployed `plan.expected`, jar anchor `bbc3f530`).

## Bottom line
**Route ① (unified state's 9 shared paths + BoatAttack's 3 app-private files) is the right first attempt and is
well-founded.** Every Unity-specific adaptation lives in the 3 app-private files; the 9 shared paths carry **no**
Unity patch — they are generic route-a generation drift. The one shared path the private files depend on
(`pthread_bridge`) is **byte-identical** across both generations. The only shared-path delta that encodes a *fix* our
U13 lacks is a **49-byte `CLASSNAME_FIX`** in `libandroid.so`/`liboh_android_runtime.so` (identical symbols + strings) —
a trivially portable patch if route ① stalls (route ②). No whole-generation swap is warranted.

## The 9 shared paths (authoritative: `boat-attack-apk-lightup.sh` device_hash gate, lines 346–354)
| # | device path | our U13 SHA256 | BoatAttack bundle SHA256 | same? | equivalent fix on our side? |
|---|---|---|---|:--:|---|
| 1 | `/system/bin/appspawn-x` | `2a87118e…` | `76e6df93…` | ✗ | generation drift (no Unity patch); our U13 appspawn hosts 94+ apps → generically equivalent |
| 2 | `…/liboh_adapter_bridge.so` | `84695d62…` | `8ab85446…` | ✗ | ours = the **846 bridge** (bench 2026-10-01-bridge-846), a superset of the pulled baseline; exports 2358 vs boat 2360 — ABI-equivalent |
| 3 | `…/liboh_android_runtime.so` | `18763dd4…` | `adc125f4…` | ✗ | boat folds runtime+libandroid into one blob (`adc125f4` = base `9ccf64f8` + `RUNTIME_CLASSNAME_FIX`); ours is a distinct file → same fix family as row 4 |
| 4 | `…/libandroid.so` | `9ccf64f8…` | `adc125f4…` | ✗ | **boat = our base `9ccf64f8` + 49-byte `CLASSNAME_FIX`**; 0 symbol delta, 0 string delta → our U13 ships the *unfixed* base. The one portable fix (route ②). |
| 5 | `…/libnativeloader.so` | `b8be63d2…` | `fde6f31c…` | ✗ | generation drift (no Unity patch) → generically equivalent |
| 6 | `…/libwestlake_bionic_pthread_bridge.so` | `db31d6d8…` | `db31d6d8…` | **✓** | **byte-identical** — the one shared path the 3 app-private files `add-needed`; load-bearing for route ① |
| 7 | `…/framework/oh-adapter-runtime.jar` | `bbc3f530…` | `56e4d473…` | ✗ | different route-a jar generation; no Unity-specific content; our bbc3f530 hosts the campaign |
| 8 | `…/appspawn/libwestlake_android_child.z.so` | `dc73a28d…` | `47f238ae…` | ✗ | generation drift → generically equivalent |
| 9 | `route-a/<gen>/libwestlake_android_runtime_provider.so` | `0509fe23…` (dir `74d1d6d4…`) | `f821d20e…` (dir `74e6f759…`) | ✗ | different route-a generation id; provider is route-a infra, not Unity-specific |

**"Introducing commit" (boat side): there is none per file.** `.bridge-payload/` is gitignored (0 tracked files); every
boat binary is a board-pull / assembled artifact tracked only by SHA in `manifest.env`. Nearest git anchors (tracked
scripts, not the binaries): `ae8ef1fcc` (switch the shared candidate to this bundle) and `43ec24af9` (pin the jar).
Provenance: `ASSEMBLED_FROM` a line-B strict-runtime candidate; `ADAPTER_ORIGIN`/`RUNTIME_ORIGIN` = board pull
`boat-hw248-20260924` (hw248 build run `boatattack-runtime-source-20260813…`), SHA-matched to the bundle.

## The 3 app-private files (bind into `/data/app/…/com.Unity3d.BoatAttackDay/android/lib/arm64/`, never the 9 shared)
| file | device-pinned SHA | what it does (the Unity-specific fixes) |
|---|---|---|
| C7 `libunity.so` | `1bea0fae…` | 8/13 identity byte-patched: `add-needed pthread_bridge`; `0x761ed8` Unity core resolver→`eglGetProcAddress`; `0x690ac0` disable optional phone listener; `0x67a554` **disable unsupported Swappy predicate** |
| C4 `libil2cpp.so` | `f6b806b5…` | same-source rebuild: `rename-dynamic-symbols` (signal map) + `add-needed signal_box` + `add-needed pthread_bridge` |
| signal-box `libwestlake_bionic_signal_box.so` | `7a931c79…` | bionic/musl signal-ABI shim for Unity; copied from the shared candidate, bound app-private |

These three are the *entire* Unity-specific surface. They touch no `/system` shared path; both depend on
`pthread_bridge` (shared, byte-identical here) and the signal-box is app-private.

## Why route ① holds (capability diffs, `evidence/our-side-and-diffs.txt`)
- **Unity NDK contract is provided equally.** `adapter-gap-seed.txt` (97 syms: `ASensor×15`, `ALooper×6`,
  `ANativeWindow×6`, libc++, logging) are *UND/needed*, not adapter exports (both adapters export 1/97). They are
  satisfied by `libandroid.so`, which covers **28/97 on both sides with an identical exported symbol set** (0 delta).
- **`libandroid` delta = 49 bytes, non-ABI.** `cmp -l` = 49 differing bytes; `strings` delta = 0; symbol delta = 0.
  So boat's `adc125f4` is our base `9ccf64f8` + a surgical `CLASSNAME_FIX` instruction patch — not a feature gap.
- **The private three's shared dependency is exact.** `pthread_bridge` is byte-identical, so the C7/C4 `add-needed`
  resolves against our U13 without change.
- **The runtime downstream contract** (`oh-native-contract.txt`, 161 syms: `OH_NativeXComponent` touch×14 incl.
  `GetTouchEvent`/`RegisterCallback`, `OH_NativeVSync×3` — load-bearing because C7 disables Swappy app-side,
  `OH_NativeDisplayManager×5` for 1920×1200) is OH-platform surface our U13 runtime already wires for the campaign's
  interactive apps. It is the thing to **watch** on board (touch projection + vsync pacing + landscape geometry).

## Route judgment
1. **Route ① — unified state + the 3 app-private files (no shared-path change). RECOMMENDED first.** Overlay C7/C4/
   signal-box app-private on a spare board already on U13; launch BoatAttack; 5-touch check. Supported by: all Unity
   fixes app-private, `pthread_bridge` byte-identical, `libandroid` ABI identical, adapter ABI superset.
   **Watch:** the `CLASSNAME_FIX` our U13 lacks — since symbols+strings are identical, route ① should *load*; the risk
   is a Unity activity/class-resolution failure (`com.unity3d.player.UnityPlayerActivity`). Also watch touch/vsync/
   landscape (the OH native contract) in the t28 screenshots.
2. **Route ② — if ① fails with a class-resolution symptom: port the `CLASSNAME_FIX`.** Apply the 49-byte
   `libandroid`/`liboh_android_runtime` patch (boat `adc125f4` relative to base `9ccf64f8`) as **new files** overlaid on
   the unified state — no ABI/symbol/string change, no frozen-file change. This is the single most likely missing piece.
3. **Route ③ — only if ① and ② both fail: report to the outer loop.** Do **not** swap the whole generation (the board
   constraint "两代不能同路径共存" and the spec forbid it).

## Boundaries & gate
Static only — **no board, no deploy, no push, no APK re-sign, no whole-generation swap** (spec 排除范围). On-board
verification (`demo_baseline_boatattack_run`, human-reviewed) is a later spare-board window: screenshot = ground truth
(1920×1200 racing scene, same PID, scene changes after 5 touches), and if the overlay un-lights any of 10 previously-lit
keys it is rolled back. The spec's reject-before-write gate: any APK or private-candidate SHA mismatch exits nonzero
naming the file before any board write (already enforced by `boat-attack-apk-lightup.sh require_hash`).

## Files
- `evidence/boat-side-facts.txt` — the 9 shared paths + 3 private files + Unity native-contract families (boat side).
- `evidence/our-side-and-diffs.txt` — our U13 SHAs, the symbol/byte/string diffs behind the "equivalent fix" column.
