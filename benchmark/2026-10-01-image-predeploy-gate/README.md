# image_predeploy_gate.py — two offline gates that catch a bad boot image BEFORE the board window

**What was wrong before.** Two boot-image deploys aborted on the board and burned a board window each, even
though every existing gate (`check_boot_oat_rb.py`, `t4b_build_switch_gate.py`) passed offline:

- **T7c** (tagsoup + boot-api stubs image) aborted in `ClassLinker::CheckSystemClass`. Root cause: the image
  was compiled from a NEW `adapter-mainline-stubs.jar` (`366acc27`, dex checksum `0xf731efbe`) but deployed
  image-only over the board's resident jar (`beb369a1`, `0x6bb8936f`). The recorded dex checksum did not match
  the jar in effect → the R155 runtime rejected the image → `InitWithoutImage` → abort. (See
  `../2026-09-30-dex2oat-l2/t7c-FAIL-checksystemclass/ROOT-CAUSE.md`.)
- **T5b** (read-barrier-OFF rebuild) went blank / faulted in app loops. Root cause: its dex2oat emitted
  **implicit** loop suspend checks (`ldr x21,[x21]` — a self-load meant to fault via a page the board never
  arms) instead of the **explicit** style the board R155 libart supports (`ldr w16,[tr];state_and_flags` +
  `tst #0x7` + `bl pTestSuspend`). T5c fixed the entrypoints and passed (T6c PASS).

Neither failure is visible to a read-barrier/kv check — both need to look at *what the image will be loaded
against* (its BCP jars) and *how its code is compiled* (the suspend-check shape).

## The rule this run establishes

**Never deploy a generated boot image to a board until it passes `image_predeploy_gate.py` against a
known-good reference image.** Two deterministic offline gates (no board, no runtime):

- **G1 — image↔BCP dex-checksum consistency.** Each `boot-<jar>.vdex` records the dex location-checksum(s) of
  the jar it was compiled from (parsed from the vdex `kChecksumSection`, version 027). Compare the candidate
  image's per-segment checksums against a reference image compiled from the jars that will be in effect after
  deploy. Any segment that differs and is **not** listed in `swap_jars` (jars deployed *alongside* the image)
  is a hard reject. This is exactly the check the board runtime does at load — done offline.
- **G2 — compiled-code suspend-check shape.** `oatdump` a loop-bearing probe method (default
  `java.lang.String#hashCode`, universal + has a back-edge suspend check) from both the candidate and the
  reference and compare the normalized instruction sequence (absolute addresses stripped). Any difference is a
  reject. T5b's `hashCode` is 32 insns (implicit `ldr x21,[x21]` at insn 24); T5c/v3c are 36 insns (explicit).
- **SKIPPED is not PASS** (the ACK95 hole): if the deploy changes the image or a BCP jar (`swap_image` or
  `swap_jars`), G2 **must** run. If `oatdump` is then unavailable, G2 is **FAIL**, not SKIPPED. G2 may only be
  skipped when the plan declares `changes_compiled_code:false` (a data-only redeploy).

G1 reads a `deploy-plan.json` (authored by oc-t4) to decide which jars to compare against and whether a
segment is being swapped — see `deploy-plan.example.json`. CLI flags override plan fields.

## Evidence — 4 replays (full log: `gate-replays.txt`)

Reference image = v3c (`cc-wiki-v3c-ref`, board resident good image, `boot.oat 25d92cf7`). oatdump =
`aosp-14.0.0_r1-art` host build on hw248.

| # | candidate | deploy | G1 | G2 | VERDICT | expected |
|---|-----------|--------|----|----|---------|----------|
| A | T5c (`boot.oat 0e7dc0e4`) | image-only | PASS | PASS — hashCode 36==36 insns | **PASS** | PASS ✓ |
| B | T5b (`boot.oat 90f82719`) | image-only | PASS | **FAIL** — 32 vs 36; insn24 `ldr x21,[x21]` vs `ldr w16,[tr]` | **FAIL** | FAIL ✓ |
| C | T7c (`boot.oat 3a2737cd`) | image-only (the deploy that aborted) | **FAIL** — mainline-stubs `0xf731efbe`≠`0x6bb8936f` | FAIL | **FAIL** | FAIL ✓ |
| D | T7c | package: `--swap adapter-mainline-stubs`, cand-BCP = T7c jars | PASS (segment swapped) | PASS — hashCode 36==36 | **PASS** | PASS ✓ |

- **B** is the G2 win: T5b would have been caught offline, before locking a board.
- **C** is the G1 win: the actual T7c image-only deploy is rejected offline; the recorded checksum
  `0xf731efbe` (`366acc27` jar) ≠ resident `0x6bb8936f` (`beb369a1` jar).
- **D** shows the *correct* T7c deploy (image + its jar together) passes both gates — this is how the T7c
  board re-test must be run.

Local-only replays (`image_predeploy_gate.py`, no oatdump) confirm the SKIPPED→FAIL policy: T7c image-only →
G2 FAIL (required, no oatdump); T5c `--no-compiled-change` → G2 legitimately SKIPPED → PASS.

**oatdump_remote.sh integration** (`g2-oatdump_remote-integration.txt`): the gate driven from the Mac with
`--oatdump=scripts/lab/oatdump_remote.sh` (oc-t4, master `13de64544`; `LAB_HOME=/home/alvin`) — which scp's
the image `arm64/` dir + BCP jars to hw248 by content hash and runs the host oatdump there — gives the SAME
verdicts as the raw-oatdump replays: T5c vs v3c PASS (G2 36==36), T5b vs v3c FAIL (G2 32 vs 36, insn24
`ldr x21,[x21]` vs `ldr w16,[tr]`). The gate picks the `--image` form by extension: a `*.sh` wrapper gets the
real `<dir>/arm64/boot.art` (it strips the arch itself); the raw oatdump binary gets the `<dir>/boot.art`
location (it inserts the arch). So `oatdump_remote.sh` is a correct drop-in for `GATE_OATDUMP`.

## Wiring

- `knowledge/toolchains/art-r155/image_predeploy_gate.py` — the gate.
- `knowledge/toolchains/art-r155/t5_gen_image.sh` — runs the gate after image generation (env `GATE_REF`
  [+`GATE_OATDUMP`/`GATE_BCP`/`GATE_CAND_BCP`/`GATE_SWAP`], or `GATE_PLAN`); FAIL → exit 7.
- `benchmark/2026-09-30-dex2oat-l2/t6_board_test.sh` — runs the gate as a fail-fast preflight **before the
  board is locked**; FAIL → refuse to deploy (no board touched). Unset `GATE_REF`/`GATE_PLAN` → loud warning.
  Point `GATE_OATDUMP` at oc-t4's `oatdump_remote.sh` to run G2 from the Mac.

## Reproduce (on hw248)

```
OD=/home/alvin/aosp-14.0.0_r1-art/out/host/linux-x86/bin/oatdump
LIB=/home/alvin/aosp-14.0.0_r1-art/out/host/linux-x86/lib64
J=/home/alvin/cc-wiki-t5/jars   V3C=/home/alvin/cc-wiki-v3c-ref
python3 image_predeploy_gate.py --image /home/alvin/oc-t4-t5c --reference $V3C \
        --oatdump $OD --bcp-dir $J --art-lib $LIB           # A: PASS
python3 image_predeploy_gate.py --image /home/alvin/oc-t4-t5b --reference $V3C \
        --oatdump $OD --bcp-dir $J --art-lib $LIB           # B: FAIL (G2)
python3 image_predeploy_gate.py --image /home/alvin/oc-t4-t7c --reference $V3C \
        --oatdump $OD --bcp-dir $J --art-lib $LIB           # C: FAIL (G1)
python3 image_predeploy_gate.py --image /home/alvin/oc-t4-t7c --reference $V3C \
        --swap adapter-mainline-stubs --cand-bcp-dir /home/alvin/cc-wiki-t7c-bcp \
        --oatdump $OD --bcp-dir $J --art-lib $LIB           # D: PASS
```
