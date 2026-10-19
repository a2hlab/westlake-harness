# candidate-r3 — Toutiao video load blocker (three-file: run + compat + mffmpeg)

**Status: static proposal, no board.** Supersedes r2 (`79275cf9`), which the outer and cx-seal both rejected on static evidence. r3 keeps r2's run.sh **unchanged** and adds one byte-exact derived file. The three-file CAS executor is outer executor r5 (89b054e1, independently reviewed by cx-seal); this directory supplies the reviewable inputs, the reproducible derivation, and the load-experiment card.

## What was wrong with r2 (proven, not inferred)

r2 moves `libttmplayer.so` into the android-native namespace so its NDK-C++ chain (`libvcbasekit` → `libc++_shared` needing `std::__ndk1`) binds against the APK libc++ instead of OH's. Correct idea, fatal side effect:

- `libttmplayer` `DT_NEEDED libmffmpeg.so` is resolved by musl's **by-name** path (`find_library_by_name` → `load_library`, oh61 dynlink `e50b30f2` L2408/L2552).
- That path **never** runs RouteB `SanitizeInitArray`, which fires only on ART's explicit `System.loadLibrary` entry (`link_stubs_arm64.cc` `87a2e823` L552-559).
- APK `libmffmpeg.so` (`fecf91e1`) has one `INIT_ARRAY` slot at vaddr `0x45c168`, file value `0`, **zero** relocations (`evidence/r2-review/object-facts.txt`).
- musl `do_init_fini` has **no null guard** (`e50b30f2` L3446-3457: `while (n--) ((void(*)(void))*fn++)();`) → it would call address `0` — a **predicted** crash (static); the observed P1 window LOAD-FAIL was the libvcbasekit ns0 relocation, which masks this.

Adding `libmffmpeg` to `NATIVE_TARGETS` (as r2 does) does not save it: ART loads it, `SanitizeInitArray` writes the dotted sibling `.libmffmpeg.so.westlake-init.<pid>.<seq>`, and the by-name `DT_NEEDED` lookup misses that dotted shortname and reloads the original — null slot included.

## The fix (minimal, reuses the loader's own semantics)

Replace the physical `$RT/lib/arm64-v8a/libmffmpeg.so` with a pre-sanitized copy produced by exactly what `SanitizeInitArray` would write:

- sole slot is effectively null → `kept=0` → `DT_INIT_ARRAYSZ = kept*8 = 0`.
- the slot bytes are already `0`, so the **only** on-disk change is the `DT_INIT_ARRAYSZ` d_val at file offset `0x48aca8`, `8 → 0` (one word).
- `before fecf91e1 → after d2882303`, 4870376 B, metadata unchanged.

Because `INIT_ARRAYSZ=0`, `SanitizeInitArray` now hits its `kept == array_size/8` early-return and opens the **real path**, so no dotted sibling is made and the ART load and the `DT_NEEDED` load share **one inode** (the outer's requirement). It is byte-identical to the loader's own output: no new filter, no security-logic change.

## Files

| File | What |
|---|---|
| `derive_mffmpeg.py` (`2165a64f`) | reproducible derivation; mirrors `SanitizeInitArray` L344-466; reject gates below |
| `deploy-inputs/run.sh` (`79275cf9`) | **identical to r2**; 2 token lines vs P1 (`run.sh.diff-vs-p1`, `run.sh.diff-vs-orig`) |
| `load-experiment-card.md` | read-only small-window verification (V1-V6), proven vs to-verify kept separate |
| `receipt-tests/reject-gates.txt` | drift / size / live-slot refusals + happy path |
| `receipt-tests/gate_probe.py` | slot-liveness logic probe (SHA pin removed) — not a deploy entry |
| `logs-sanitized/`, `raw-log-manifest.txt` | sanitized derive logs + per-file SHA manifest |

Large derived `.so` (4.87 MB) is **not committed**: persistent in the raw receipt dir, outer mirrors to hw248. The recipe (`derive_mffmpeg.py`) is committed.

## Reject gates (derive_mffmpeg.py)

input SHA ≠ `fecf91e1` · size ≠ 4870376 · packed/undecodable relocs · any init slot live/relocated (refuse to drop a real constructor) · byte diff ≠ the single `DT_INIT_ARRAYSZ` word · output SHA ≠ `d2882303`. On the pinned input the SHA gate subsumes the slot-liveness gate; `gate_probe.py` exercises the latter directly.

## Raw execution receipt

`$HOME/.local/share/westlake/toutiao-video-r3-derive/20261019T192945/` — `command.txt`, `derive.stdout.txt`, `derive.stderr.txt`, `derive.rc` (= 0), `SHA256SUMS`, `derive_mffmpeg.py`, `libmffmpeg.so`. Prior run `20261019T192754` kept. Independent cross-check: outer `video-r3-readonly/independent-derived-sha.json` (same offset `0x48aca8`, same `d2882303`); three-way agreement.

## Not claimed

Playback / audio / decode / surface. r3 removes one proven **load** fatal. "Routing becomes correct" is an **inference** until the card's V3/V4 reads; see `selected-change-r3.json` `closure_by_real_provider` for the proven vs unproven split. No constructor added, no security mechanism changed, no runtime re-baked.
