# T99 — observed static clock binding

Earlier numeric log values did not establish their clock. This run establishes the producer expression in the SHA-pinned library; it does not establish runtime alignment or a performance fix.

Java 21 `-version` returned **rc=0**. One TOUCH21 search, two direct-reference queries and two decompilations all returned **rc=0**, using Ghidra 12.1.4 and the prescribed T98 compiler/SDK/cache environment. Target SHA before and after: `8ab6742d58de5b9df94a2bfa80cebed46f136c0251083793fcbef8293cc23ab1`; 2,206,152 bytes.

| Marker | String address | Direct reference PC | Observed enclosing function |
|---|---|---|---|
| POLL enter | `0x1369ba` | `0x2bd768` | `tracePoll` |
| POLL exit | `0x13b425` | same returned function; no separate xref query | `tracePoll` |
| WAKE | `0x135196` | `0x2bd858` | `traceWake` |

Both functions obtain `now` from **`clock_gettime(1, &timespec)`**, converted as **`tv_sec * 1000 + tv_nsec / 1000000`**, i.e. integer milliseconds. POLL enter and exit use separate calls. PCs above are reference sites, not claimed function-entry addresses.

Reproducible locations: `.private/logs/03-poll-decompile.pseudocode.txt:314` (enter clock), `:326` (enter print), `:345` (exit clock), `:349` (exit print); `.private/logs/05-wake-decompile.pseudocode.txt:18` (clock), `:29`–`:30` (print/conversion). `evidence-index.json` retains exact Evidence IDs and selected line excerpts; full JSON and snapshot stay private with SHA/length inventory in `raw-manifest.json`.

A separately pinned local Linux UAPI header defines clock ID 1 as `CLOCK_MONOTONIC`; that header is a naming reference, **not** a proven producer header or runtime libc binding. Static API/argument/unit are established. Wall-clock/trace alignment, runtime symbol binding and overall launch-delay attribution remain **unknown**. No target execution, device action, MCP query, permission change or binary modification occurred. T96/T97/T98 failures remain unchanged.

Validation: `python3 benchmark/2026-10-23-permission-restored-clock/check_evidence.py` checks successful receipts, artifact identity, returned xrefs and timing expressions, then records raw hashes. `.private/` is excluded from the commit. Returned Evidence is retained completely; no separate successful compiler stdout/stderr was emitted by REA, so none is fabricated.

Outer verification independently hash-checked all files in `raw-manifest.json`, replayed `check_evidence.py` against persistent private copies, and compared the Evidence index exactly. Private replay root: `$HOME/.local/share/westlake/permission-restored-clock-20261023/outer/`. Public checkout alone does not include `.private`; use that complete archive for replay.
