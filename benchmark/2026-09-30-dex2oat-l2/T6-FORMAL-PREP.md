# Formal T6 acceptance prep — T5b (read-barrier-OFF) boot image on 5cd

This is the **一劳永逸 acceptance**: if the boot image our own toolchain generates (T5b) runs apps on the
board R155 runtime, then dex2oat-once is solved — we can regenerate a board-compatible boot image offline.
The T6 discriminative run (2026-09-30, `t6-rb-discriminative/`) already proved the **RB-on** T5 image
fails (zygote SIGILL, HW blank). T5b is the RB-off rebuild that should now pass.

## Prerequisite (oc-t4 T3b/T5b)
- oc-t4 rebuilds r1 ART with `ART_USE_READ_BARRIER=false` (T3b), then regenerates 27 files with
  `knowledge/toolchains/art-r155/t5_gen_image.sh` into **`/home/alvin/oc-t4-t5b/`** (hw248).
- Their own check: boot.oat kv `concurrent-copying=false`, vdex 9/9.

## Offline pre-board gate (run BEFORE asking for the 5cd window — do not burn the short window on a bad image)
1. Fetch the 27 files hw248 → Mac (tar-over-ssh; a quoted `scp *` glob silently copies 0 files here):
   ```
   ssh hw248 'cd /home/alvin/oc-t4-t5b && tar cf - *.art *.oat *.vdex' | tar xf - -C <stage>/arm64
   cp knowledge/toolchains/boot-image-inputs.sha256 <stage>/
   ```
2. **Read-barrier gate (the decisive new check):**
   ```
   python3 knowledge/toolchains/art-r155/check_boot_oat_rb.py --image <stage>/arm64/boot.art <stage>/arm64/boot.oat
   ```
   Must print `concurrent-copying=false` + `PASS`. If it says `true` → NOT RB-off, do NOT board; oc-t4 must
   rebuild with T3b's RB-off dex2oat. (Verified discriminating: T5 RB-on → FAIL, v3c board ref → PASS.)
3. vdex byte-identity (9/9) vs reference: `cd <stage> && shasum -a256 -c <(grep '\.vdex$' boot-image-inputs.sha256)`
   (`.art`/`.oat` differ by embedded cmdline path strings — expected, not a gate).

## Board window (≤30 min, 5cd, cc-wiki lane)
Board must first be at **U3** (fingerprint `0b81cdbe0ed9`). Restore it exactly as in the T6 run if needed:
`deploy_generation.sh 5cd… westlake-generation-v3c-candidate` → `… n2-51a78bde --upgrade` →
`replay_unified_state.sh 5cd… --lane cc-wiki` → confirm fingerprint `0b81cdbe0ed9` + HW own-UI.

Then run the (fixed) overlay tester:
```
board_note.sh lock <app-lighting.md> 5cd1e3dd00000000000000000923012c cc-wiki "formal T6: T5b RB-off image"
APPS="aegis,ooniprobe" EXPECT_FP=0b81cdbe0ed9 \
  bash benchmark/2026-09-30-dex2oat-l2/t6_board_test.sh --serial 5cd1e3dd00000000000000000923012c --image-dir <stage>
```
(`t6_board_test.sh` already: APPSPAWN_SVC=appspawn-x, no-awk parent check, `hilog -r` before restart,
socket re-fix after start, begetctl only — **never kill -9**. The script's verdict wording is written for
the *discriminative* run; for FORMAL acceptance read the criteria below.)

## PASS criteria (formal — the opposite of the discriminative run)
| # | check | PASS | FAIL (regression) |
|---|---|---|---|
| 1 | appspawn-x parent after overlay | `=1` | `0` (image rejected) |
| 2 | zygote SIGILL during restart (`hilog … grep 'signal: 4'`, exclude __membarrier) | **none** | any signal-4 in forked children |
| 3 | HelloWorld screenshot | own-UI, "Hello World!" (~78–88 KB) | blank (~38 KB) |
| 4 | ZigZag screenshot | own-UI | blank / no process |
| 5 | bms_batch APPS (aegis,ooniprobe) | lit as at U3 | worse than U3 baseline |
| 6 | CheckSystemClass abort / new cppcrash | none | any |
| 7 | rollback → fingerprint | `0b81cdbe0ed9` + HW lit | drift |

**Verdict = PASS iff 1–7 all hold** → T5b image is board-compatible → dex2oat-once acceptance met.
Screenshots are ground truth (own-UI, not alive count). Whole run: boot_id must not change (no reboot).

## After PASS
Record T5b hashes (27 files + jars), the RB gate output, HW/ZZ + app screenshots into
`benchmark/2026-09-30-dex2oat-l2/t6-formal/`; add a bold Layout row + DIGEST line; then T7 (below) reuses
the same RB-off toolchain.
