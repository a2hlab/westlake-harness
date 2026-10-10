# BoatAttack render owner — symptom-first re-analysis (cc-t3 #91, corrects e34b234aac)

Zero board. Responds to the outer pushback: my earlier README named **libandroid adc125f4** the "render/color/resolution
primary port file" and proposed an **app-private** port. Both are wrong. This file redoes the three asks the outer set:
① pin "拉伸/stretch" and "偏紫/purple" each to the first *differing* evidence; ② reverse-find the code that owns that
evidence and check whether **that file** (not libandroid) differs PR03 vs U13; ③ re-order the port list with honest
private-vs-shared and rollback.

Evidence used (all on disk, no board):
- PASS (PR03 backing): `00.Workspace .../reproduce-boat-attack-apk/20260924T080718Z-quick/{surface-node.txt,buffer-configs.txt,hilog.txt}`
- Our 61b route②d run: `westlake-harness-tools-inventory/benchmark/2026-10-09-demo-boatattack/demo-61b/{evidence/boat-review.json,window1/apply/hilog.txt}`
- SHA bases: `games-c-5ea1/{SO-INVENTORY.tsv,SHA256SUMS}` (PR03 `pr03-74e6-portable`), `demo-61b/prelock-identity/runtime-fingerprint.txt` (U13 live)
- t2b capability diff: `westlake-harness-wiki/benchmark/2026-10-09-demo-boatattack/evidence/our-side-and-diffs.txt`

---

## 0. What I got wrong (先写原来错在哪)

| claim in e34b234aac | reality | evidence |
|---|---|---|
| libandroid adc125f4 = render/color/resolution **primary** lever | libandroid vs ours = **49-byte CLASSNAME_FIX, 0 export delta, 28/97 NDK identical** — a class-name patch cannot produce low-res+purple ("论断与对象不符", DIGEST 偏移对上≠对象对上) | our-side-and-diffs.txt rows 10/28/30 |
| the `ANativeWindow_*` buffer size/format path lives in libandroid | `ANativeWindow_*` comes from **libhwui**, and **libhwui is byte-identical** on U13 and PR03 (`be59260f…`) | DIGEST line 314; SHA matrix §3 |
| put the render file **app-private** (Boat ns), 128 apps untouched | the render pipeline runs in **shared `/system` libs** loaded before any app child → a private copy is never selected; app-private render port is **impossible** | hilog resolves `lib=/system/android/lib64/liboh_android_runtime.so`; §4 |

---

## ① Symptom → first *differing* evidence

### "拉伸 / low-res stretch" is NOT the window/surface — it is the INTERNAL render resolution
Both runs put Boat on a **full 1920×1200 `AdapterSurfaceView`**:
- PASS `surface-node.txt`: `default-size = [1920x1200]`, `config = [1920x1200, 8, 12, …], scalingMode = 1, HDR = 0`,
  buffer `1920x1200` ×2 (`buffer-configs.txt`).
- 61b `boat-review.json`: ffprobe `dimensions [1920,1200]`, "full racing scene … to all edges"; apply hilog line 46103
  `CreateNodeAndSurface … name:AdapterSurfaceView` for Boat pid 28544.

So the window is the same size in both. The "HUD 字大且糊 / 低分拉伸" therefore means **Unity rendered to a smaller internal
framebuffer that was upscaled to the 1920×1200 surface** (`scalingMode = 1` = scale-to-window). Unity derives that internal
size from the **EGL window-surface query + DisplayMetrics**, not from the surface node. → the first differing evidence for
stretch is *Unity's resolution query result*, which is **not captured** in either artifact set (see §2 gap).

### "偏紫 / purple" is NOT the SetBufferColorSpace/metadata path
`SetMetadata Failed with -5` → `RSUniRenderComposerAdapter::SetBufferColorSpace set color space fail` fires **in the PASS
(GOOD) run too**: **310 / 78** times (`hilog.txt`), and the PASS screen is correctly colored. A failure present in the good
run cannot be the purple cause. (The 61b counts 8692 / 2285 are a **162k-line whole-apply-window across ~11 apps**, not
Boat-isolated — not comparable; do not read them as a Boat differentiator.) → purple must come from the **color format Unity
chose at `eglChooseConfig` / the buffer pixel-format channel order (RGBA vs BGRA)**, i.e. the EGL/format mapping layer — not
the colorspace-metadata call.

## ② Capture gap — why a single "first differing log line" cannot be pulled from existing artifacts

The reproduce PASS run captures per-process `surface-node.txt` + `buffer-configs.txt` + a Boat-only `hilog.txt`. **Our 61b
route②d run captured none of these** — only screenshots + one mixed `window1/apply/hilog.txt` (162049 lines, all apps, the
EGL14 lines at 23:59 are pid 26939, not Boat's 28544 at 00:17:40). There is **no `config = […]` buffer tuple, no
eglChooseConfig attrib list, no DisplayMetrics line for Boat** in it. So the exact "拉伸=这一行、偏紫=那一行" line-diff the
outer asked for is **not extractable from the data we have**; it needs a new capture (see §5). What *is* rigorously
derivable is the **code owner** of each symptom and whether that owner differs PR03↔U13 (§3) — done below.

## ③ Reverse-code: who owns stretch/purple, and does THAT file differ PR03 vs U13?

Render-relevant SHA matrix (U13 live 61b vs PR03 backing; prefixes):

| file | role for the symptoms | U13 (61b) | PR03 base | differs? |
|---|---|---|---|---|
| **liboh_android_runtime.so** | EGL14 JNI: `eglChooseConfig` (color format), `eglCreateWindowSurface`, display/metrics queries → **both** stretch & purple | `18763dd4` | `9689ce76` | **YES** |
| **liboh_adapter_bridge.so** | `AdapterAnw → oh_anw` buffer **geometry + pixel-format + colorspace** conversion (DIGEST 450) → stretch (geometry) & purple (format order) | `84695d62` | `7db99e1b` | **YES** |
| **oh-adapter-runtime.jar** | Java `Display`/`DisplayMetrics`/`WindowManager` → the internal render resolution Unity reads → stretch | `bbc3f530` | `06141543` | **YES** |
| libhwui.so | `ANativeWindow_*` NDK window cluster (DIGEST 314) | `be59260f` | `be59260f` | **NO — identical** |
| libandroid.so | NDK shim; exports ~identical to PR03 (49-byte classname) | `9ccf64f8` | `6e9c0c2c` | yes but inert (0 export delta) |
| libEGL/libGLESv2/libvulkan | GPU drivers | system | system (same ROM) | NO — same ROM |

**Owner verdict**: the EGL config + ANativeWindow format/geometry + DisplayMetrics — the exact code that decides *resolution*
and *color* — lives in **`liboh_android_runtime.so` + `liboh_adapter_bridge.so` + `oh-adapter-runtime.jar`**, and **all
three differ PR03↔U13**. The parts that do *not* differ (libhwui identical; GPU drivers same ROM; libandroid exports inert)
are ruled out. The hilog proves the EGL14 entry points resolve into `liboh_android_runtime.so`
(`android.opengl.EGL14::eglChooseConfig … lib=/system/android/lib64/liboh_android_runtime.so`, apply hilog line 2232).

## ④ The app-private design is impossible for the render pipeline (open-site / linker-ns)

The three differing owners all live at **`/system/android/lib64/…` and `/system/android/framework/…`** and are **loaded by
the host/runtime into the shared bridge namespace before any app child spawns** (hilog: every EGL/GLES hook resolves to
`lib=/system/android/lib64/liboh_android_runtime.so`, the shared system path — not an APK-private path). Consequences:
- Putting a PR03 copy in Boat's APK/private ns would **not be selected**: the app namespace inherits the already-loaded
  shared runtime/adapter, and the jar is a boot-classpath provider. This is exactly the outer's libandroid concern — and it
  applies to **all three render owners**, not just libandroid.
- Therefore **porting PR03's render files = replacing the SHARED files that all 128 apps use.** That is not an app-private
  overlay; it is a change to the unified/frozen state, and must go through the AGENTS.md rule-3 frozen-change process
  (single-variable `compare_runs.py`, re-verify the frozen apps don't regress, register in frozen.json before deploy), not
  a "128-app-safe private port".
- The genuinely-private files (`c4` libil2cpp, `c7` libunity disable-swappy, `signal-box`) are the Boat **engine** libs and
  stay private — but they are **not** the render-pipeline owners; they can only *mask* a symptom (e.g. Swappy pacing), not
  set resolution/EGL color.

## ⑤ Re-ordered plan (honest: shared-file single-variable bisect, not private port)

Because the owner is a shared file and the static diff can't say *which of the three* (the capture gap), the correct next
step is the minimal on-board experiment AGENTS.md prescribes for render behavior that's invisible statically — a
**single-variable swap bisect on a spare board**, each step with the reproduce's surface/buffer/EGL capture + a screenshot:

| order | swap (from U13 → PR03 base) | symptom it should move | can be private? | prove selection | rollback |
|---|---|---|---|---|---|
| 1 | **liboh_android_runtime.so** `18763dd4→9689ce76` | **both** (EGLConfig color + surface/metrics → stretch) — highest-yield | **No** (shared /system) | n/a (shared) — confirm via maps that Boat loads the swapped inode | restore `18763dd4`; 128-app full sweep must not regress |
| 2 | **liboh_adapter_bridge.so** `84695d62→7db99e1b` | purple (format order) + stretch (buffer geometry) | **No** (shared /system) | maps inode | restore `84695d62`; full sweep |
| 3 | **oh-adapter-runtime.jar** `bbc3f530→06141543` | stretch (DisplayMetrics/internal res) | **No** (BCP provider, frozen-adjacent) | n/a | restore `bbc3f530`; full sweep — **frozen gate**, needs user sign-off |
| — | libhwui / libEGL / GLESv2 / vulkan / libandroid | — | — | — | **do NOT port** (identical / same-ROM / inert) |

Rules this plan honors: swap **one file at a time** (so the screenshot change is attributable, DIGEST 偏移对上≠对象对上);
each swap is a **shared** change → single-variable `compare_runs.py` + **128-app full sweep must not regress** before it can
stand; the jar is frozen-adjacent → **user sign-off required**. Validation per t2b spec `781635e518`: side-by-side with the
PASS screenshot — full-res (sharp HUD), no purple, KPH double-digit + steering + lap; quantitative luminance vs PASS
`gameplay-difference.env` (YAVG≈54).

**Needed capture (so step N can pin the line, not just the file):** run the swap with the reproduce's
`surface-node.txt` + `buffer-configs.txt` + a **Boat-pid-filtered** `hilog.txt` (include `eglChooseConfig`/`eglGetConfigAttrib`
attrib dump + `ANativeWindow_set*` + DisplayMetrics), so "拉伸" lands on the resolution/metrics line and "偏紫" on the
EGLConfig/format line — the artifacts the 61b route②d run omitted.

## Bottom line
- Render/color owner = **shared** `liboh_android_runtime` + `liboh_adapter_bridge` + `oh-adapter-runtime.jar` (all differ
  PR03↔U13); **not** libandroid (49-byte inert) and **not** libhwui/GPU drivers (identical/same-ROM).
- An **app-private** port of these is impossible; the port is a **shared frozen-state change** → single-variable board
  bisect (runtime → adapter → jar), full-sweep gate, jar needs user sign-off.
- Nothing here is in frozen.json; no board was touched.
