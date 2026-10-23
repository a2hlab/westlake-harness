# T71 — passive attribution of the T68 first-launch exit (61b, child 8088)

Read-only; board free, zero writes, no reboot/reopen, no REA/debugger/hook; only the head of one existing faultlog record (up to `Registers:`).

## Evidence
- `/data/log/faultlog/temp` (path from `scripts/lab/sc17_run.sh:64-66`, script not run) has exactly one record for PID 8088: `cppcrash-8088-1792728897556` (sha256 e656461f…).
- Header binds it to T68's child: Pid 8088, `com.ss.android.article.news`, Uid 20011206, Timestamp 12:14:57.556, life time 15 s — matching the T70 child-stderr mtime 12:14:57.76 and the guardian exit window on boot 33f35797.
- Reason `SIGSEGV(SEGV_MAPERR)@0x0`; fault thread `ChromiumNet0`; frame #00 musl `__libc_malloc_impl` pc 0xd6e20 (build-id a9d01819…), called via app-bundled `libc++_shared.so` from `libsscronet.so` (Toutiao's bundled Cronet).

## Result
The first-launch exit is a native crash surfacing in musl malloc on Toutiao's own network thread. Frame #00 matches, at signature level (same musl build-id and pc), the heap-integrity class already recorded in `.octos/KNOWLEDGE-DIGEST.md` (A.9, A.18–A.20). In that class the faulting thread is a victim, so the owner of the corruption (bridge vs app) stays **unknown**. No direction or fix is proposed.

## Rule
Bind a crash record by pid + process name + timestamp + boot window before reading it, and read only the header up to `Registers:`.

## Status: blocked
The follow-up reasoning step was stopped at ~13:03 by a safety classifier (reason not provided: unknown). Work stopped there: no further device reads, source tracing or retries. High-level attribution is **not sufficient** to assign ownership.

Outer review: [outer-review.json](outer-review.json). All 31 private manifest entries and five cited receipt hashes were checked; no post-refusal source analysis was performed. Private originals remain at `$HOME/.local/share/westlake/first-exit-attribution-20261023/`.

The public header excerpt removes trailing whitespace only; its untouched original remains in the private receipts with the original SHA in results.json.
