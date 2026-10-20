# R26-001: idle geometry cache blocked a new legacy RGB lock

**Closed by an actual host C regression check. Device/runtime acceptance remains unknown.**

Before the fix, eight completed RGB geometry requests occupied eight IDLE cache entries. A ninth distinct RGB window then received `-ENOSPC` from `r26_lock_begin`, even though scratch reservation was zero and no lock was active. This could prevent the old RGB pass-through route before prepare. The fix admits the new lock when idle cache capacity can be reclaimed.

| Check | Exact yv12.c SHA-256 | Observed result | Process rc |
|---|---|---|---|
| Original bug detector | `85b5f9a72519fc5d9cf5affd4ec009dd5b53a5265db317fa77108e6a1cbf8391` | ninth lock=-28; reserved=0; destroy=0 | 0, bug present |
| Same detector, unchanged | `28827c1c8eaef3212c13ed2be2399ec4b51ff4501abf3b5a75c6df6f933e5f97` | ninth lock=0; reserved=0; destroy=-16 | 5, old failure expectation no longer holds |
| Normal success lifecycle | same fixed SHA | lock/prepare/before_unmap/finish/destroy all0; output descriptor unchanged | 0 |

The unchanged detector deliberately did not finish a lock because the original lock failed. After the fix, `destroy=-EBUSY` correctly protects that active lock. `capacity_after.c` extends the same setup with a non-YV12 packed RGB descriptor, checks exact output preservation, and finishes before destroy. All three compilations returned 0.

## Reproduce

Use the exact source hash for the intended row and supply its `yv12.h` plus the R14 `window_module.h` (pins in `results.json`). A snapshot with these files is retained in the private index.

```sh
# SOURCE_DIR contains yv12.c, yv12.h and window_module.h at the listed pins.
cc -std=c11 -pthread -Wall -Wextra -I "$SOURCE_DIR" \
  "$SOURCE_DIR/yv12.c" capacity_after.c -o capacity_after
./capacity_after
```

For the original detector, replace both `capacity_after` names with `capacity_before`; interpret its exit status using the table. The fixture source and the small original stdout files are included. `private-index.json` gives exact hashes for both source snapshots, compiler receipts, original binaries, and the independent wiring review without publishing user-specific absolute paths.

This isolates cache capacity and legacy descriptor preservation. It is not a production ELF/provider binding or screen/video proof. No main files or devices were modified by this review lane.
