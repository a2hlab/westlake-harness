# Optional v1 boot-permissive switch (default OFF, new-file v3) — cc-t3 #91

An **opt-in, default-OFF** way to boot a demo board into SELinux **permissive** via a NEW recover variant, for the case the user approves running the 128-app demo the way the original t3 baseline was captured (permissive). **Nothing changes until the user both installs v3 AND creates one file.** Not deployed, not enabled; staged for approval.

## Why a NEW file (v3), not an edit
`westlake-u13-recover.sh` (v2) is cited as evidence by `knowledge/gates/selinux-label-recipe.json`, so `land.py` refuses to overwrite it. This redo leaves **v2 byte-for-byte unchanged** (pinned SHA `95eb4f6efd3c…`) and adds the switch in a new `westlake-u13-recover-v3.sh` + a new cfg, selected by an installer param. Background for *why permissive*: 10-09 t3 signoff had studytracker zero-CANTOPEN and lit; the donor autostart did a global `setenforce 0` at boot while v2 keeps Enforcing (`benchmark/2026-10-09-demo-baseline/autostart-plan.md:80`) — so the original 128 baseline was almost certainly Permissive, and the el2 `SQLiteCantOpen` cluster only appears once v2 turned real enforcement on (`benchmark/2026-10-10-el2-cantopen/`).

## What changed (v2 untouched; no frozen item touched)
1. NEW `benchmark/2026-10-10-u13-autostart/payload/scripts/westlake-u13-recover-v3.sh` — identical to v2 **plus** a marked switch block after bind+labels+socket+receipt: reads `/data/westlake-demo/u13/selinux-mode`; **only if the content is EXACTLY `permissive`** does it `setenforce 0` and append the read-back to the receipt. File absent / any other content ⇒ untouched (stays Enforcing). Never implicit. The header documents the v3-vs-v2 delta and drops v2's "never make the board permissive" line. Functional diff vs v2 = exactly the 10-line switch block, nothing removed (asserted).
2. NEW `benchmark/2026-10-10-u13-autostart/payload/init/00_westlake_u13_recover-v3.cfg` — the v2 cfg with the `westlake-u13-recover` service path pointing at `westlake-u13-recover-v3.sh`; everything else identical.
3. `install-westlake-u13-autostart.sh` — adds one param `RECOVER_VARIANT` (default `v2`). `v2` places the original recover + cfg (unchanged behaviour); `v3` places the v3 recover + v3 cfg instead (the supersede guard keeps whichever cfg this run places, so there are never two boot workers). The original cfg file is not modified.
4. `scripts/lab/demo_seal_61b.py` — pre/post-reboot `getenforce` acceptance is now **plan-driven** (`== plan selinux_mode`: `enforcing`→`Enforcing`, `permissive`→`Permissive`); `validate()` fail-closes unless the plan declares `selinux_mode`; `seal.json` records it.
5. `benchmark/2026-10-10-demo-seal-61b/plan-template.json` — declares `"selinux_mode": "enforcing"` (safe default).
6. NEW `scripts/lab/test_selinux_mode_switch.py` — 12 tests: switch behaviour (missing / wrong / exactly-permissive, via the REAL extracted v3 block), switch contract, **v2 SHA unchanged**, **v3 == v2 + only the switch** (functional difflib), and the seal criterion (mapping both modes + validate() requires explicit selinux_mode).

## How to use (only after user approval)
```
# install the v3 recover variant (default stays v2):
RECOVER_VARIANT=v3 WITH_BOAT=<0|1> ... sh install-westlake-u13-autostart.sh
# enable permissive on that demo board:
hdc -t <sn> shell "echo permissive > /data/westlake-demo/u13/selinux-mode"
hdc -t <sn> target boot          # recover-v3 applies setenforce 0 after recovery; receipt records selinux_mode=Permissive
```
Seal/accept under permissive: set `"selinux_mode": "permissive"` in the seal plan (demo_seal then requires `getenforce==Permissive` and records it).

## SECURITY IMPACT (read before enabling)
- **Whole-board**: `setenforce 0` is global — SELinux enforcement is OFF for the ENTIRE device while enabled, not just demo apps.
- **Persists across reboots**: recover-v3 re-applies it every boot while the file says `permissive`. Not one-shot.
- **Demo boards only**: acceptable only on a dedicated demo/lab board with no sensitive data; never on a board with real user data.
- **Two independent gates**: must install `RECOVER_VARIANT=v3` AND create the `selinux-mode` file; a default (v2) board can never go permissive, and a v3 board with no file stays Enforcing.
- **Auditable**: the receipt records `selinux_requested` + live `selinux_mode` each boot; demo_seal records the plan's `selinux_mode` in seal.json, so a permissive seal can't be mistaken for an Enforcing one.
- **Revoke** (back to Enforcing): `hdc -t <sn> shell "rm -f /data/westlake-demo/u13/selinux-mode"; hdc -t <sn> target boot` (or reinstall default `RECOVER_VARIANT=v2`).

## Tests
`python3 -m unittest scripts/lab/test_selinux_mode_switch.py` → 12/12. `bash -n` on recover-v3.sh + installer OK; v2 recover.sh + ka_tests unchanged (ka 46/46); `build_seal` 18/18; `check_user_paths` 0; `check_frozen` 0 (no frozen touched).
