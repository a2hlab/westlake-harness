# v1 permissive-route orchestration — dry-run evidence (cc-t3 #91)

Written evidence the whole lighting campaign ran **Permissive**: `benchmark/2026-09-30-board-inventory/{61b,5cd,5ea}/misc.txt` line 1 = `selinux: Permissive` on all three boards (board_inventory.sh). User rule: once 5cd confirms, if it was permissive use permissive. This wires the v1 permissive route in `demo_seal_61b.py`, ready to use after 5cd confirmation. **Enforcing behaviour is byte-for-byte unchanged.**

Both transcripts are `demo_seal_61b.py --dry-run --mode v1` (preview; zero board/transport/writes).

## Permissive plan (selinux_mode=permissive, reference 61b-t3) -> `dryrun-permissive.txt`
Adds exactly three steps vs enforcing, in the existing safe sequence (DISABLED -> bare boot -> assert_bare_base -> installer REUSE; no extra installer re-run):
- `installer: ... ALLOW_REMOUNT=1 RECOVER_VARIANT=v3 /system/bin/sh .../install-westlake-u13-autostart.sh`
- `selinux-mode-file: ... echo permissive > /data/westlake-demo/u13/selinux-mode && cat ...` (before ENABLE; readback must be `permissive`)
- `post-enforcing: getenforce == plan selinux_mode (Permissive)` and `post-receipt-selinux: cat .../receipt.env` requiring `selinux_requested=permissive` + `selinux_mode=Permissive`

## Enforcing plan (default, reference 5cd) -> `dryrun-enforcing.txt`
`RECOVER_VARIANT=v3` absent (installer defaults v2), no `selinux-mode-file`, no `post-receipt-selinux`; `getenforce == plan selinux_mode (Enforcing)`. Identical to the pre-change flow.

## Unchanged in both
sepolicy gate and reboot_sim still run (labels still per `selinux_label_recipe`); they are no longer gated on "Enforcing" — the enforce criterion is `== plan selinux_mode`. validate() fail-closes unless the plan declares `selinux_mode`; seal.json records it.

Tests: `scripts/lab/test_selinux_mode_switch.py::OrchestrationTwoMode` asserts the permissive transcript has the three steps and the enforcing transcript has none (14/14 total).
