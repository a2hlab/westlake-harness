# Boat geometry delta: portable source specification, not a built candidate

## Evidence first / corrected assumptions

The Boat blob **adc125f4** is not a newly built shared runtime. Against its
actual parent **9ccf64f8**, it changes **49 file bytes: 47 executable bytes in
13 AArch64 instructions across four functions, plus two class-name bytes**.
Calling the entire patch `CLASSNAME_FIX` misses the geometry changes. U13's
genuine runtime **18763dd4** already fixes the two class literals, but **does
not** implement any of the four geometry behavior changes.

There is another source-selection trap: the requested smoke-markers and
n3b-webview directories provide startup/publication, **not** the geometry TU
actually compiled into 187. The frozen t2c recipe selects the **M1 session-slots
version** at line 318, not the older b87 geometry file. Replacing it wholesale
with the Boat/9cc source would regress M1. See `evidence/recipe-selection.txt`,
`source-bindings.json` and the exact original snapshot in `source/`.

| Artifact | Full SHA-256 | Bytes |
|---|---|---:|
| U13 root libandroid / actual parent | `9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db` | 744856 |
| Boat libandroid also aliased as runtime | `adc125f4dfb800c25d80e7d73216c8885fd64a31c6b91f064494166c63a59130` | 744856 |
| Genuine U13 shared runtime | `18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae` | 3194328 |

`commands.json` records **15 full-function disassemblies**, argv, raw output
hashes, exit codes and objdump identity. `instruction-deltas.json` accounts for
every changed instruction/byte; no new build, board, VM or SSH operation was run.

## 1. Executable delta, instruction to source

### A. `nwfs_seed_window_geometry`: stop overwriting geometry with panel constants

At **0x407a0**, `bl NativeWindowHandleOpt@plt` becomes `nop` (**4 bytes**).
The surrounding instructions still prepare operation **0**, width **1200** and
height **1920**, but no longer call the OH setter. This preserves whatever
geometry the producer already has; it is not a new window, a display-bounds
query, or a format change. Existing unwrap/raw fallback and null guard remain.

U13 still calls the setter at **0x19732c** with the same constants.
The source is `source/android_graphics_compat_shim.cpp:1225`; line **1227**
sets the constants and **1235** calls the setter. Make the exported two-argument
seed function non-mutating. Its lazy caller is also significant:
`BBQ_nativeGetSurface` calls it at Boat **0x41890** / U13 **0x198918**, source
line **646**; this caller is **not** a fifth binary-patched function.

### B. `ANativeWindow_fromSurface`: the same seed, inlined by the compiler

At **0x40a04**, the fixed 1200x1920 setter becomes `nop` (**4 bytes**).
U13 still executes it at **0x197590**. This is the compiler-inlined seed at
the last-mile handoff, not a new pointer conversion or reference-count rule.

The source function starts at **1241**; line **1273** calls the shared seed and
**1276** returns the existing pointer. Changing the helper covers this site:
keep the call, null/sentinel checks, `Surface.mNativeObject` lookup and returned
pointer. Remove obsolete comments promising a fixed panel-size mutation.

### C. `BBQ_nativeUpdate`: use requested width/height, not 1200x1920

Four changed instructions (**16 bytes**) are:

| Boat PC | Parent | Boat | U13 matching PC |
|---|---|---|---|
| `0x41e8c` | `mov w2,#1200` | `mov w2,w20` | `0x198bd0` |
| `0x41e94` | `mov w3,#1920` | `mov w3,w19` | `0x198bd8` |
| `0x41e98` | `mov w26,#1200` | `mov w26,w20` | `0x198bdc` |
| `0x41e9c` | `mov w27,#1920` | `mov w27,w19` | `0x198be0` |

Entry instructions **0x41c24** / **0x41c20** copy nativeUpdate's **x4 width /
x5 height** into x20/x19. Low 32 bits therefore feed both OH arguments and
the dimension log; the setter call **0x41ea0** itself is unchanged. U13's call
at **0x198be4** still receives hardcoded constants.

Source **551** declares the jlong arguments, **560–561** already cast them
to `b->width/height`; **604** currently invokes the constant seed. Replace only
that call with a static dimensioned helper on the **same resolved window**.
Keep U13's M1/session resolution, child-surface choice, fallback, cache and
format logic. Do **not** silently add a positive-dimensions check or panel-size
fallback: neither is present in the observed 47-byte patch.

### D. `ANativeWindow_setBuffersGeometry`: width zero preserves geometry

The **seven** rewritten instruction slots at **0x40c04–0x40c1c** account for
**23 changed bytes**, not 28 changed bytes. The unwrap `csel` moves one slot;
**0x40c08 `cbz w21,0x40c20`** skips the geometry setter when **width==0**.
The same setter target moves from **0x40c18** to **0x40c1c**. This is not a
different API call. U13's equivalent unguarded block is **0x197790–0x1977a8**.

Source **1327–1343**: guard only the geometry call at **1331** with
`width != 0`. Keep unwrap, format mapping (**1332–1339**) and public return
**0**; null window still returns **-1**. In particular:

| Input | Geometry setter | Format setter (format > 0) |
|---|---|---|
| width=0, height=0 | skipped | retained |
| width=0, height=positive | skipped | retained |
| width=positive, height=0 | called | retained |
| width=negative, any height | called | retained |

### Diagnostic deviations are intentional, not rendering changes

The binary patch leaves broken rc logs. In A/B it removes `bl` but still
copies **w0** (the window pointer's low bits) as rc. In D it removes
`mov w22,w0`; final `str w22,[sp]` logs the original ANativeWindow pointer's
low bits even when a call occurred. Neither is an OH success/failure result.

The source draft deliberately does **not** preserve those artifacts: generic
seed logs `PRESERVE_BUFFER_GEOMETRY` without a pretend rc; explicit update logs
the real setter rc; width-zero setBuffers logs an explicit preserve marker.
Its initialized rc=0 on the skipped path is a local sentinel, **not evidence
that OH was called successfully**. New diagnostic strings require normal
outer review on a future built artifact.

## 2. Exact source mapping / already present versus to change

All four behaviors belong to **one** frozen TU:

`$WORKSPACES/westlake-harness-t3/benchmark/2026-10-02-m1-session-slots/runtime/src/android_graphics_compat_shim.cpp`

SHA `e28f4bc3a7c863defd74bb173146ea89308a6bf952ea1d11c80b00dd87ecd658`;
the same bytes were landed in master **64d7e6594b**. The t2c frozen inventory
SHA is `68924eaf25b164ed19faa5412325a0d0487026cfa7401fa62642203e549d400e`;
recipe SHA is `613102d30077037abd08cc741e65ffbaa3ffd85e157d5100631dc331cfae8ef4`.

`u13-geometry-draft.patch` is an **unapplied source-level review draft** against
that exact TU. It adds a static explicit-dimensions helper, retains the seed's
exported ABI as a preserve hook, switches update to actual dimensions, and
guards only width zero. The draft edits **1 file, +17/-21 physical lines**
(including removed obsolete comments); no new exported helper is requested.
The precise reproducible count is in `results.json`; this is source sizing,
not a new binary SHA or an estimate of board effort.

The smoke-markers `AndroidRuntime.cpp` (recipe **271**) and n3b
`webview_publication.cpp` (recipe publication branch **552–554**) define none
of these five window functions. Startup has two **comment-only** mentions of
`ANativeWindow_fromSurface` at **132/145**, not its implementation.
**No change** to either; retain their
startup/registration/publication object set. Also retain the actual SQLite /
CursorWindow TUs already proved in
`benchmark/2026-10-10-boat-runtime-jni-gap/` (master **1a1eb6e6bd**): the gfx
source's weak placeholders are overridden by those real linked registrars.

## 3. Class-name delta: already fixed in U13

At file offsets **0x2ab5a** and **0x2ca52**, Boat changes `X` to `e` in the
slash/dot forms of `AppSchedulerBridgX`. `class-name-check.json` independently
counts exact NUL-terminated literals: 9cc has **0 correct / 1 wrong** for each
form; adc and 187 both have **1 correct / 0 wrong** for each form.

The actual t2c source is
`$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b87-native/adapter/framework/android-runtime/src/android_view_InputEventReceiver.cpp:255`
(dot lookup), and **267** (slash lookup), SHA
`88ed40dd455fb0aa64e12dad5a71d3c5d099aa444c71d32e24eff8b65c2e7809`.
Both already use **Bridge**. This part requires **zero changed source lines**.

## 4. Feasibility, risks, handoff boundaries

**Yes, source-level feasible:** rebuild the genuine 187 source/object recipe
with this one small TU patch, retaining the 787-export/real-registration owner
rather than loading adc as another runtime. **Rendering equivalence, Boat play
and single live owner remain unverified; measured unlocks=0.** No candidate was
built or deployed here.

Risks / future acceptance requirements:

1. Removing the fallback can leave an early/lazy producer at zero geometry if
   nativeUpdate has not provided dimensions. The old fallback explicitly
   protected that case. Verify Boat's real size, first request, visible frame,
   five touches/LAP and power-cycle behavior, not just a setter log.
2. This TU is shared by ordinary SurfaceView/Unity users. Preserve M1 routing
   and all registration objects; require the rebooted full **128-app** regression
   before any frozen-item replacement is promoted.
3. Width zero is asymmetric; do not broaden to `(width==0 || height==0)` or
   positive-only semantics without a new reviewed hypothesis.
4. U13 already has same-SONAME libandroid/runtime copies and can light apps;
   SONAME alone is **not a new failure proof**. Actual owner/load ordering still
   needs source/namespace and live-map proof. Merely keeping 187 at one pathname
   does not establish single ownership. The new renderer must not be bypassed
   by an old root libandroid copy.
5. Preserve JNI/ABI and NEEDED, isolate geometry-function call differences,
   run open-site/strings/ABI-consumer/N1/N2 gates on the future built candidate,
   and register a new frozen SHA before a separately authorized deployment.
   Rollback is the exact 187 artifact plus the previous reviewed overlay list,
   not adc at the runtime pathname.

cc-t3 owns `benchmark/2026-10-10-boat-overlay-v2/` (master **adec044270**):
adapter/JAR/private-file checks and final overlay routing are **not duplicated**
here. That report's runtime slot references this port specification. Our only
product is the geometry semantics/draft on the exact U13 source; there is no
claim that it supplies the missing real `6333bcab` JAR or proves other shared
members safe.

## Offline reproduction and verification

```sh
python3 benchmark/2026-10-10-boat-runtime-port-spec/collect.py
python3 -m unittest discover -s benchmark/2026-10-10-boat-runtime-port-spec -p 'test_*.py' -v
```

The tests check 13-instruction/47-byte coverage, U13 literal status, exact source
drift refusal, preserved M1/JNI/format logic, non-mutating handoffs, width-zero
guard and **git apply --check** on a temporary source fixture. They do not
compile it or substitute for rendering evidence. Two collector runs are
byte-identical; raw output is in `evidence/verification.txt`.
