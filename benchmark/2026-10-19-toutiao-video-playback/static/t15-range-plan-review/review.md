# t15 fixed-range supplemental log capture — plan/method narrow review

Context (T14 close `$HOME/.local/share/westlake/toutiao-resume-20261020/t14-5cd-window-01/close.json`):
post-play two shots same SHA `ac4cc7…`, `playback: not_verified`; the 64 KiB frame only read the HEAD of
the real range. T15 = read-only supplemental capture of the FIXED range, no UI/runtime change.
Pins: child **1601/b7706984**, parent **19163/7265322**, boot **0525bb05**, fd2
`/data/service/el1/public/appspawnx/adapter_child_1601.stderr` dev **66352** inode **178230**, range
**[26377929, 57241402)** = **30,863,473 B** (< 64 MiB cap). Plan not yet landed; reviewing the method.

## Verdict: method is FEASIBLE — **1 make-or-break item** + reuse map. No big new framework.

## MAKE-OR-BREAK — efficient non-aligned read via ALIGNED blocks + host-precise trim
The range start `26377929` is **not** a multiple of 65536. Read **aligned blocks, then trim** — no
`iflag` and **no on-board iflag probe needed**:
- **Use** aligned block dd covering the range: `dd if=<log> bs=65536 skip=floor(26377929/65536)
  count=(ceil(57241402/65536) − floor(26377929/65536)) 2>{scratch}` — whole blocks
  `[floor_block·65536, ceil_block·65536)` in block-sized I/O (fast), a fixed, known **aligned length**.
- **Frame declares the ALIGNED length; verify-then-trim in that order:** `decode` first checks the
  aligned raw by marker POSITION (`END` at `len(start)+aligned_len`, `END:0`, host rc0, no timeout,
  `POST`), **then** host-trims head `26377929 mod 65536` and tail to exactly `[26377929, 57241402)` by
  byte count. Only a verified-complete aligned frame may be trimmed; otherwise PARTIAL.
- **Forbid** `bs=1 … count=30863473` (30 M syscalls → **timeout**; = T14 `framing.script` bs=1, fine for
  64 KiB, fatal here) and `bs=65536 skip=<blocks>` taken as the final bytes **without** the trim
  (misaligned → wrong bytes).

## Reuse map (don't rebuild)
- **`framing.decode` position-based completeness logic reused, extended to aligned+trim:** verify the
  ALIGNED raw (`startswith(BEGIN:aligned_len)` AND `raw[len(start)+aligned_len:].startswith(END:0)` AND
  host rc0 AND no timeout AND `endswith(POST)`), **then** trim head/tail to `[26377929,57241402)`; else
  `PARTIAL_UNVERIFIED`, bytes preserved, `player_verdict='unknown'`. Binary-safe; detects short-read/
  truncation by marker POSITION. Change `framing.script` to the aligned block-dd line above; keep
  BEGIN:aligned_len / END:rc / POST + the `2>{scratch}` fd2 redirect (stderr = dd's "N records" summary →
  scratch, payload stays clean on the merged stream).
- **observe.py guards reused verbatim:** per-command `guard()` identity bookend for child 1601/parent/
  (host) + boot; `ready()` exact-holder recheck on every command; exact-board-lock + holder↔ISO; 600s
  window; the frame guard already does `stat -L -c %d:%i == <dev>:<inode>` + `size >= <end>` — set to
  `66352:178230` + `>= 57241402`, before AND after the read.
  **Caveat (correction to the first draft):** same inode + `size>=end` does **not** prove the range bytes
  are unchanged since play — it cannot exclude **in-place overwrite** or **truncate-then-regrow** (T14
  README limitation). The dev:inode/size guards bound file identity + extent only, **not content
  immutability**. So the capture records the range's **current** bytes; their equivalence to the
  play-time content is a **residual unknown**, not asserted.
- **64 MiB cap:** payload 30,863,473 B + markers < 64 MiB; keep an explicit transfer/`raw` size ceiling so
  an unexpectedly larger stream aborts to PARTIAL rather than unbounded memory.

## Discipline (confirm present)
Read-only `if=<log>` only; **never write the log**; scratch holds only dd stderr evidence. Short-read /
dd-error / missing-marker / host-timeout ⇒ **PARTIAL, bytes preserved, no UI retry** (a re-read is a
read-only range re-fetch, not a UI action). No UI/runtime/attach/deploy/reboot. Does **not** re-judge
T14 (player stays `unknown` until the range content is human-reviewed). One bounded window, restore not
needed if power untouched (read-only), else reuse T14 restore.

## ACTUAL-CODE REVIEW — `read_range.py` sha `336e81dac5a29e27e43a79a6d86341a7fa87b1987035366f3d821120828e5b60` — **ACCEPT**
Profile pin `eb2887fb…` (68), source-pins enforced (69-70), observe.profile/guard reused (77-78,89).
Four review points all pass:
- **Misalignment — CORRECT (no off-by-one).** `plan`: aligned=`26374144` (=6439·4096, floor≤start),
  trim=`3785` (start−aligned), raw_length=`30867258` (end−aligned), blocks=`7535`, full_end=`57237504`,
  tail=`3898` (=length%4096, ≤4095, the only bs=1 read). Block dd reads `[aligned,full_end)`, bs=1 tail
  reads `[full_end,end)`; `decode` returns `payload[3785:3785+30863473]` = `[26377929,57241402)` exactly
  (3785+30863473 = 30867258 = len(payload), slice lands on both ends). bs=1 confined to the 3898-B tail
  (no bs=1 over the 30 MB bulk).
- **Short-read — PARTIAL, raw preserved.** `decode` is position-based: `END` must be at
  `len(head)+raw_length` with `:0:0` (both dd rcs 0); a short/early END or non-zero rc → `need` fails →
  `PARTIAL_UNVERIFIED`; `stdout.raw` is written by `capture()` regardless (preserved); `selected.raw`
  only on COMPLETE. Binary-safe (exact-position, not search).
- **Post-guard — bookended, gates POST.** guard runs at entry and again before `printf POST` under
  `set -e` (29/36-38); a failed post-guard → no POST → `endswith(POST)` fails → PARTIAL. guard (89) =
  observe.guard(identity bookend child1601/parent/host+boot) + `test -f LOG` + `/proc/1601/fd/2==LOG` +
  `dev:inode==66352:178230` + `size>=57241402`. `board.ready()` lock recheck before+after (94,97).
- **Raw-size boundary — bounded.** `need(raw_length<=64 MiB)` (19); START/END are constants ⇒ dd
  count fixed ⇒ on-wire output bounded ~30.86 MB irrespective of live file size; an oversize stream →
  END not at `at` → PARTIAL. (Minor hardening, non-blocking: an explicit `stat stdout.raw` ceiling
  before `read_bytes` would belt-and-suspender the memory load; the fixed dd count already bounds it.)

Discipline present: read-only `if=LOG` (never writes the log), scratch holds only dd stderr evidence,
`device_application_writes=0`, no UI/signal/attach; 300 s window with 20 s command reserve; status
defaults PARTIAL, FIXED_RANGE_BYTES_COMPLETE only on verified frame; `runtime_verdict='pending_review'`
(player unknown until content human-reviewed; this does NOT re-judge T14). The immutable/deterministic
over-assurance is corrected above — same inode+size bounds identity+extent only, not content.

**Verdict: ACCEPT read_range.py (no blocker).** Re-confirm if the author's final spec-collection changes
the SHA.

token t15-range-plan-review
