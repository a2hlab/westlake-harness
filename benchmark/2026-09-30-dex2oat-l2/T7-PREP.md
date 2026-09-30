# T7 prep — tagsoup + boot-api stubs boot image on 5cd (Wikipedia headline target)

T7 swaps a rebuilt **`adapter-mainline-stubs.jar`** (cc-t3: real tagsoup `Parser.setProperty/getProperty` +
J4 boot-api stubs for fd-feeder/gallery MediaStore) into the 9 bootclasspath jars, dex2oat's a 27-file boot
image, and overlays it on 5cd. It reuses the exact same overlay mechanism as T6.

## ⚠️ Hard dependency added by the read-barrier finding (2026-09-30)
The original T7 dispatch (board ACK 21:32) said generate with "r1+21 补丁的 dex2oat64" — that is the
**read-barrier-ON** toolchain, which produces an image the board R155 runtime cannot run (T6 discriminative:
zygote SIGILL, HW blank). **T7's image MUST be regenerated with oc-t4's T3b `ART_USE_READ_BARRIER=false`
dex2oat64**, exactly like T5b. So T7 is gated behind T3b/T5b, and its boot.oat must show
`concurrent-copying=false`. Do not board a T7 image built with the RB-on dex2oat.

## Prerequisites
- Formal T6 (T5b) PASS first — proves the RB-off toolchain yields a board-compatible image.
- cc-t3 tagsoup + boot-api jar: `westlake-harness-t3` branch `feat/app-lighting-t3`
  (`bms/src/adapter/framework/mainline-stubs/.../tagsoup/Parser.java`; build
  `bms/src/adapter/build/inner/compile_mainline_real.sh` via dockbuild; details in
  `westlake-harness-t3/benchmark/2026-09-30-t7-tagsoup-prep/HANDOFF.md`).
- oc-t4 generates 27 files with **T3b RB-off dex2oat64** + `t5_gen_image.sh` (new jar swapped in) →
  **`/home/alvin/oc-t4-t7/`**; records new jar + 27-file hashes.

## Offline pre-board gates (before asking for the 5cd window)
1. **RB gate:** `python3 knowledge/toolchains/art-r155/check_boot_oat_rb.py --image <t7>/boot.art <t7>/boot.oat`
   → must be `concurrent-copying=false` + `PASS`.
2. **jar-delta gate** (board ACK 21:32 requirement: "只多 Parser 的 setProperty/getProperty 与常量,其余逐字节不变"):
   new `adapter-mainline-stubs.jar` vs board reference **`beb369a1173eec0c…`**
   (v3c payload) — baksmali both, diff the smali trees; only `org/ccil/cowan/tagsoup/Parser` (+ the declared
   J4 boot-api stub classes/fields) may differ, every other class byte-identical; bootclasspath order/position
   unchanged (adapter-mainline-stubs stays #7 of 9).
3. Note: **vdex 9/9 does NOT apply to T7** — changing one BCP jar changes that segment and everything
   downstream in the multi-image chain, so `.vdex`/`.art`/`.oat` legitimately differ from the T5 reference.
   T7's gate is functional (apps below), plus the RB + jar-delta gates above.
4. Fetch 27 files hw248 → Mac by tar-over-ssh (not `scp *`, which silently copies 0 here).

## Board window (≤30 min, 5cd, cc-wiki) — same overlay tester
Restore/confirm U3 (`0b81cdbe0ed9`, HW lit), then:
```
APPS="wikipedia,fd-feeder,fd-gallery" EXPECT_FP=0b81cdbe0ed9 \
  bash benchmark/2026-09-30-dex2oat-l2/t6_board_test.sh --serial 5cd1e3dd00000000000000000923012c --image-dir <t7-stage>
```
begetctl only (never kill -9), socket re-fix after start, `hilog -r` before restart, no awk.

## PASS criteria
| # | check | PASS |
|---|---|---|
| 1 | no RB regression | appspawn-x up, no zygote SIGILL(signal 4), HW/ZZ own-UI still lit |
| 2 | **tagsoup wall cleared (headline)** | Wikipedia advances past `Html.fromHtml` NoSuchMethodError (tagsoup `Parser` no longer an empty shell) — read t20 screenshot + hilog for the class-load, not just "process alive" |
| 3 | boot-api stubs | fd-feeder / gallery advance past the missing-MediaStore-field/method wall (per cc-t3 J4 boot-api list) |
| 4 | CheckSystemClass / cppcrash | none new |
| 5 | rollback | U3 fingerprint `0b81cdbe0ed9` + HW lit, boot_id unchanged |

Wikipedia is the headline app (board ACK 21:32: "T6 过后外环排 5cd 上板验 Wikipedia"). Screenshots are ground
truth — the win is Wikipedia's own content rendering past the tagsoup wall, not an alive count. Record into
`benchmark/2026-09-30-dex2oat-l2/t7/` with the jar-delta report, RB gate output, and per-app screenshots.
