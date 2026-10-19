# r4 minimal load-experiment card (61b, outer-run, read-only after deploy)

**Purpose.** r4 removes one *deterministic* crash: the GLES/EGL proc-loader writing a resolved pointer into provider code (symbol preemption). Whether the player then proceeds is to be read, not assumed. Card, not a script; four-file apply/rollback is cx-seal's CAS (r6). All reads after one video tap in the Toutiao child `C`.

## Preconditions (apply by the executor)
Four files at postimages: run.sh `79275cf9`, compat `9f558aaf`, libmffmpeg `d2882303`, libttmplayer **`5fba8050`**. libttmplayer single-file backup `...ttvideo-before-<boot8>` (sha `b427614d`). Fresh reboot → new parent.

## Proven statically (do NOT re-litigate on the board)
- Root cause: 105 gl*/egl* OBJECT GLOBAL `.bss` cache slots; their `GLOB_DAT` was preempted by provider FUNC (OH musl L1389 self-binds only `STB_LOCAL`), so the proc-loader `str x0,[x9]` wrote into libEGL r-x (fault `0x7d1d95e1f8`, pc `0xde714`).
- `5fba8050` rewrites those 105 `GLOB_DAT → R_AARCH64_RELATIVE(addend=st_value)`; musl L1452 `*slot = base+addend` → each GOT slot self-binds to libttmplayer's own `.bss`. 627 bytes differ, all in those relocs; symbol table/hash/code/perms unchanged; 4 C++ vtables excluded.

## Verification items (the window's purpose)

| # | Read (no writes) | Pass | If not |
|---|---|---|---|
| V1 | deployed `$RT/lib/arm64-v8a/libttmplayer.so` sha == `5fba8050`; no `.libttmplayer*.westlake-init*` sibling (it has no null init) | right file, single inode (Java-explicit == DT_NEEDED) | STOP: wrong/stale file |
| V2 | in `/proc/C/maps`+mem, `GOT[libttmplayer_base+0x473e58]` resolves **inside libttmplayer `.bss`** (base+0x47b380), NOT inside libEGL | self-bind holds | report where it points |
| V3 | no cppcrash for `libttmplayer+0xde714`; thread `async_video_pla` does not SEGV at the proc-loader | the preemption crash is gone | capture the new fault verbatim |
| V4 | player proceeds past proc-loader; record the next `[SOURCE-NATIVE-LOAD-FAIL]`, ULE, or cppcrash (if any) | — | this is the next first-fatal (record, do not fix here) |

## Verdict rules
- "r4 crash removed" = V1–V3 pass. V2 unreadable ⇒ unknown.
- V3 still SEGV at `0xde714` ⇒ the self-bind did not take (check the deployed bytes / that musl honored RELATIVE) — record, do not relax page perms.
- No audio/video/surface success claimed. V4 names the next wall only. Preserve P0; ≤30 min; read-only; rollback or hold per outer.
