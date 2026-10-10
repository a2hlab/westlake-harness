# 5cd v2 — libinstalls swap + autostart v2 + real reboot: ZigZag lit autonomously (2026-10-10)

Outer-approved 5cd window (option ①). Flow: peel my dispatch-1 boat binds → install.py libinstalls swap → v2 autostart
(WITH_BOAT=0, surgical, reuse clean archive) → snapshot → reboot → no-Mac verify → tap HW/ZZ. Board left **working v2 +
UNLOCKED**. Evidence: `evidence/5cd-v2/`.

## Verdict: autostart v2 PROVEN end-to-end — power-cycle → working route-a runtime → ZigZag lit, autonomously

All three walls the earlier rounds exposed are cleared, verified after a reboot with **no Mac interaction**:

| Acceptance check | Result |
|---|---|
| install.py libinstalls swap (both paths → `51e1b525`), persisted across reboot | PASS |
| v2 recover ran at **post-fs-data** autonomously | `recover-v2b.log`: 56/56 replayed, relabel verified, READY |
| **dmesg `invalid:appspawn-x`** (INVALID latch) | **0** ✓ (post-fs-data timing fix) |
| appspawn-x exec label (errno-13 EACCES fix) | `u:object_r:appspawn_exec:s0` ✓ |
| **whole-tree `data_local_tmp`/`data_file` count** (exit-127 fix) | **0** ✓ (`find -exec chcon`, not the non-recursing `chcon -R`) |
| appspawn-x bin sha | `2a87118e` ✓ |
| appspawn-x on first app tap | **spawned, PPID=1 (init)** ✓ (pids 3858/3874/4035; "NativeLoader initialized") |
| seccomp **"get filter name failed"** (61b's wall) | **NOT observed on 5cd** ✓ |
| **ZigZag t20** | **LIT** — full Unity render (`as-zigzag.jpeg`: ZIGZAG / TAP TO PLAY / BEST SCORE:0) |
| HelloWorld t20 | **black** (`as-helloworld*.jpeg`) — window visible (WMS), appspawn-x spawned, no seccomp/SIGSEGV → per-app content-draw quirk, **not** the runtime; recorded as-is (不现场修) |
| label scope (outer: don't touch factory `/system/lib64`) | compliant — only ours: `appspawn/child`, `libwestlake_thread_guard_registry`, `westlake/route-a`, `/system/android` tree; `/system/lib64/seccomp` untouched |

## The v2 fix that made it work (3 layered walls, each caught by a fail-closed check)

1. **INVALID latch** (`init_common_service.c:674-692`): recover moved to **post-fs-data** (before foundation/AMS) + never
   umounts (stat continuous) → the first ServiceStart stats real bytes → never latched. dmesg has 0 `invalid:appspawn-x`.
2. **errno-13 EACCES**: appspawn-x exec entry relabeled `appspawn_exec` (PR03 `:158-161` order), **non-silent**, `ls -Z`
   read-back, fail-closed.
3. **exit-127**: the libs appspawn-x maps must not be `data_local_tmp`. The board's toybox **`chcon -R` does not recurse**
   (v2's first 5cd reboot caught this: `MISLABEL_COUNT=267`); fixed to **`find … -exec chcon`** (PR03 method) → whole-tree
   count 0. The whole-tree read-back is the gate that turned a silent white/127 into a loud, fixable failure.

## Notes / open

- **HelloWorld black**: not blocking the "power-cycle demo" hard requirement (ZigZag demonstrates it); a per-app render
  gap (process + window up, no content). Left for separate review per "不再新点亮 / 别现场修".
- **Power-cycle**: validated via soft `reboot` (init runs post-fs-data identically on a power-cycle). A literal pull-the-
  power test is a physical/user action; the autonomous-boot mechanism it depends on is proven.
- recover.sh label part still ours; switch to cx-bms's single recipe (`knowledge/gates/selinux-label-recipe.json`) when it
  lands, then re-verify same result (outer directive).
- No `setenforce`; `/` remounted rw only for placement/physical writes, re-sealed ro; only serial `5cd1e3dd…` touched;
  dispatch-1 boat binds peeled (my own leftover); install.py STOP on the first (non-pristine) attempt left the board
  unwritten. Not pushed.
