# T52 window — executed and restored (5cd)

- **Window**: LOCK 21:33:29 → UNLOCK 21:46:59 (held about 810 s). Four normal boots: R1 8507f097 (maintenance),
  R2 f9be62ba (candidate), R3 37e763f1 (maintenance), R4 89388a7b (baseline). Every guard, put and rboot rc was 0,
  checked explicitly.
- **Isolation**: R1 and R3 maintenance isolation held. ready=true; the boots list was unchanged (38, then 39); no new
  boot directory; no ROOT process.
- **Candidate (R2)**:
  - The boot copies match the candidate SHAs. One normal tap at 21:38:18, planned observation <=180 s; the last sample started at +183.217 s (deviation below).
  - seq1 and seq2: `classified=gone phase=first_birth` during capture → `classified=gone phase=monitor_birth` →
    process_exit → RECOVERING.
  - seq3: READY (bridge state) → `classified=zombie phase=monitor_birth` → RETRY_LIMIT.
  - No guardian-refusal file was written. Screenshots t30 and after are **white**.
  - This shows only that the owned exit classification triggered naturally on the device. It is not a white-screen fix.
- **Deviation**: obs12 at 21:41:21.497 and the after-shot at 21:41:22 came about 3 s past click + 180 s.
- **Restore (R4)**:
  - The six originals were restored. Six files and 13 members: SHA, mode and owner equal T46-P2; 17 `ls -Z` paths are
    `data_file`. R4 boot copies 13 = baseline. One tap → SUPERVISOR_STARTING.
  - runtime124/boot36, HAP b189, bundle, datadir unchanged; stops absent; `.new` absent; power 10000/10000; final rc
    all 0.
  - `final.jpeg` shows the Toutiao feed. It was taken on the **restored baseline**, so it is not a candidate result
    and not a close-reopen acceptance.
- **Retained**: the T52 stage/backup (backup of the originals plus the staged bytes); the T48 objects are untouched.

Raw: `$HOME/.local/share/westlake/t52-owned-exit-fix-window-20261022`, MANIFEST 60ccfa48e4280a9129fa1a3e9cb336313c7fa0cd2e023935a38d149b18319256 (2430 files).
