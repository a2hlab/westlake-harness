# Port PR03 render files into U13 for BoatAttack — static plan, app-private-first (cc-t3 #91)

> ⚠️ **SUPERSEDED (2026-10-10, outer pushback on e34b234aac).** The conclusion below — "**libandroid is the
> render/color/resolution PRIMARY port**, put it app-private" — is **WRONG on both counts**. See
> **`CORRECTION-render-owner.md`** for the symptom-first re-analysis. One-line why: (1) `libandroid` differs from PR03 by
> only a 49-byte class-name patch (0 export delta) and the `ANativeWindow_*` window cluster actually comes from
> **`libhwui`, which is byte-identical** on both bases — libandroid cannot be the lever; (2) the files that *do* differ
> (`liboh_android_runtime`, `liboh_adapter_bridge`, `oh-adapter-runtime.jar`) all load from the **shared `/system` path**,
> so an **app-private port of the render pipeline is architecturally impossible**. Read CORRECTION-render-owner.md instead
> of the plan below.

Zero-board static analysis. Goal: make BoatAttack render like the 00.Workspace PR03 PASS (full 1920x1200, correct color,
double-digit KPH + steering) on our U13 demo board, **without disturbing the 128 apps** — prefer the BoatAttack app-private
namespace (same place as the 3 private files). Evidence: `00.Workspace .../reproduce-boat-attack-apk/20260924T080718Z-quick`
(PASS) + the candidate file set `boatattack-oh61-repro-20260924/candidates/strict-boat-assembled-20260924T074522Z-25403`.

## ① Boat's actual render / color / input dependency libs
From `libunity.so`/`libtuanjie.so` DT_NEEDED + dlopen strings, the PASS proc/hilog/surface evidence:
- **DT_NEEDED** (libunity): `libEGL.so`, `libandroid.so`, `liblog.so`, `libz.so`, `libm/dl/c`, + the 2 private bridges
  (`libwestlake_bionic_pthread_bridge.so`, `libwestlake_bionic_signal_box.so`).
- **dlopen'd** (libunity strings): `libEGL.so`, `libGLESv2.so`, `libvulkan.so`, `libandroid.so`, `libmediandk.so`,
  `libOpenSLES.so`.
- **Surface/buffer (PASS `surface-node.txt`/`buffer-configs.txt`)**: `AdapterSurfaceView` BufferQueue default-size
  **1920x1200**, FIFO=3, 18000 KiB — the correct full-res config; the bad U13 render is low-res-stretched (wrong buffer
  size). The surface/buffer path is driven by the **libandroid interposer** (ANativeWindow), not the GPU driver.
- **Color (hilog)**: `RSUniRenderComposerAdapter::SetBufferColorSpace set color space fail` ×78 — but this appears in the
  **GOOD** PASS run too, so it is **not** the purple differentiator; the color/format that reaches the compositor is set by
  the libandroid ANativeWindow buffer-format path + the engine (Swappy). `ColorSpace` ×78 in hilog.
- **Input**: touch → `libandroid` ANativeWindow input queue (the #8 touch-coordinate mapping) + engine; no separate input
  driver lib.

## ② SHA diff — render-relevant files, three baselines (前16)
| file | role | BoatAttack candidate (PASS) | PR03 backing | U13 (61b) | same ROM? |
|---|---|---|---|---|---|
| libandroid.so | **render/color/resolution interposer** (ANativeWindow buffer size+format) | **adc125f4** | 6e9c0c2c | **9ccf64f8** | all 3 differ |
| libil2cpp.so | engine (Boat APK) | 3bea2f16 (c4) | n/a (app lib) | app-lib | — |
| libtuanjie.so / libunity.so | engine + Swappy/color (c7 disable-swappy) | eb9d8c6d | n/a (app lib) | app-lib | — |
| libmain.so | engine entry (Boat APK) | 2abf2614 | n/a | app-lib | — |
| libmediandk.so | audio (Boat APK) | 110d02fc | n/a | app-lib | — |
| libEGL.so | GPU driver | NOT in port set | system | 96bc1421 (/system) | **system, same ROM** |
| libGLESv2.so | GPU driver | NOT in port set | system | system | **system, same ROM** |
| libvulkan.so | GPU driver | NOT in port set | 711d9723 (/system) | 711d9723 | **system, same ROM** |
| liboh_adapter_bridge.so | route-a infra (shared) | 8ab85446 | 7db99e1b | 84695d62 | backing differs |
| libnativeloader.so | route-a infra (shared) | fde6f31c | f8a5c192 | b8be63d2 | backing differs |
| oh-adapter-runtime.jar | BCP runtime (shared) | 56e4d473 | 06141543 | bbc3f530 | backing differs |

The **GPU drivers are OH system files, not in the port set, same ROM** → the render/color defect is NOT the GPU driver. The
lever is **libandroid** (interposer) + the engine's **Swappy/color** (c7).

## ③ Per-file port judgment (prefer app-private; 128 apps untouched) + rollback
| file | class | decision | why |
|---|---|---|---|
| **libandroid.so** (candidate adc125f4) | **APP-PRIVATE** | **Port into Boat's private namespace** | the render/color/resolution interposer; a Boat-private copy lets only Boat use the PASS version while the 128 apps keep the shared U13 `9ccf64f8`. Not in frozen.json. PRIMARY render port. |
| **libtuanjie.so / libunity.so** (c7 disable-swappy) | **APP-PRIVATE** | keep as a Boat private file (engine+Swappy/color) | already one of the 3 private files; the Swappy-disable is the color/pacing fix. In the Boat APK's own lib dir. |
| **libil2cpp.so** (c4) | **APP-PRIVATE** | keep as a Boat private file | engine; one of the 3 private files. |
| **libwestlake_bionic_signal_box.so** | **APP-PRIVATE** | keep (3rd private file) | engine signal handling; already private. |
| libmain.so / libmediandk.so / libOpenSLES.so | APP-PRIVATE (Boat APK) | ship in the APK; no system change | app's own libs. |
| libEGL / libGLESv2 / libvulkan | SYSTEM (shared) | **keep U13; do NOT port** | OH GPU drivers, same ROM; cannot/needn't be private. |
| liboh_adapter_bridge / libnativeloader / runtime_provider / child / pthread_bridge | SHARED route-a infra | **keep U13** unless render still broken | app lifecycle/spawn, not the render buffer/color; porting these = disturbing the 128 apps. Try render with private libandroid + engine first. |
| oh-adapter-runtime.jar / appspawn-x / boot image | SHARED + **frozen-adjacent** (dex2oat-once, JAR providers, appspawn sealed) | **do NOT port** (frozen) | changing these touches frozen items + the 128 apps; out of scope. Use original 56e4d473 jar only if a full BoatAttack base is built, not for the render port. |

### Port list (minimal, app-private, 128-app-safe)
1. **libandroid.so = adc125f4** → Boat app-private namespace (render/color/resolution). [NEW]
2. **libil2cpp (c4) + libtuanjie/libunity (c7, disable-swappy) + signal-box** → the 3 existing private files (engine + Swappy/color).
That is the whole render/color/input fix in private space; GPU drivers + route-a infra + frozen items stay U13.

### Rollback
App-private files live only in Boat's private namespace / APK lib dir → rollback = remove the private libandroid + restore
the stock Boat APK libs; the 128 apps never referenced them, so there is nothing to undo on the shared/system side. No
/system write, no frozen touch.

### Validation criterion (on-board, later; per t2b spec 781635e518)
Side-by-side with the PASS screenshot: full 1920x1200 (surface-node BufferQueue default-size), correct color (no purple),
KPH double-digit + lap progress + steering; quantitatively compare frame luminance to the PASS `gameplay-difference.env`
(YAVG≈54). First confirm the private-libandroid-only port clears it; if color/purple persists, add the c7 Swappy-disable
engine lib; only if still broken consider the shared backing (which would disturb the 128 apps — escalate).
