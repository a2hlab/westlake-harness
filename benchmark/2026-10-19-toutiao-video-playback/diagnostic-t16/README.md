# diagnostic-t16 — executable post-load ANW object sampler (5cd successor of R13)

Minimal read-only hardware-breakpoint observer for the deployed shim lock object + fromSurface winner,
run by the outer **after** the R8 candidate loads. It **reuses R13's proven device glue verbatim** and
changes only the admission (5cd, fresh post-restart profile, player-SHA pivot), the offset source, and the
board-identity serial — via injection, never by editing/hot-modifying R13 or the public `identity` module.
Does **not** install R15 (`OFFLINE_ADAPTER_ONLY`). No board, no push here. Card + pins:
`static/t16-postload-observer/`. Root-cause anchor: full-range `87be9dff…`, offset `26606466` (audio OpenSL
IID is the first wall; the ANW object is downstream — and the current first fatal `ff_listen_connect2 -97`
is upstream of it, so this window likely never reaches the render path).

## What is reused vs new (base5 blockers 1–3)
- **Reused verbatim (pinned R13, SHA-verified at load):** `observer.Session` — HW-bp arm (`--hardware`,
  `IsHardware()` re-check), object gate `wrapper()` (magic@0 / tag@0xc8 / handle@0xc0, SBError-checked, no
  deref), return-point filter, bounded exit + `detach --keep-stopped false` + `os._exit(2)` fail-safe, raw
  stdout/stderr. And the **original on-device gate** `identity.Guard.capture` — bookended boot/PID/birth,
  four-UID check (parent/child/**server**), exe SHA, module SHA+inode, TracerPid, mapped-instance drift.
  `test_t16.ReuseStructure` proves only `__init__`+`prepare_addresses` are overridden; every other method
  **is** the R13 method by identity.
- **Blocker 1 — 5cd Guard by isolated injection (`t16_identity.py`):** R13's `Guard.capture` reads its
  module-global `SERIAL`, so the archived Guard emits `held 61b…` / `hdc -t 61b…`. We do **not** rebind the
  shared public `identity` module. Instead `make_guard()` loads the exact pinned R13 `identity.py` into a
  **uniquely-named private module** (`t16_r13_identity_5cd`), binds 5cd on *that* module only, and returns a
  `Guard` subclass of its Guard. The observer injects it through the R13 `Session(guard_factory=…)` seam.
  Result: every device argv carries 5cd (`test_t16.GuardArgv` whitelist), the public `identity` module stays
  61b (untouched, asserted), and the archived file is never modified.
- **Blocker 2 — exact pinned triples, not self-reported (`t16_core.PINNED_ADDRESSES`):** addresses must be
  **exactly 2 rows** (len-checked, so a duplicate role cannot set-mask), each equal to the REA-proven triple
  keyed by the player SHA: android `(slot=0x472688, expected_elf=0x3b9c, pc=0x3bd4)`, shim `(0x472490,
  0x5e48, 0x5e48)`. A player SHA field alone is **not** an offset proof; a different player (e.g. 5cd-deployed
  `b427614d`) is refused until its own re-derived triples are pinned here. The reused `prepare_addresses`
  still computes `bias+pc`, but validate now gates the pc/slot before any device delegation.
- **Blocker 3 — complete R13 roles + actual local bytes:** validate requires the **exact** R13 module set
  (player/android/shim/bridge/hwui), each pinned with dev/inode + `/data/…` remote_path; `parent_uid == 0`;
  parent/child exe == `EXE_SHA` (appspawn-x, not merely hex); server pid/birth > 0 and **server pid ≠ the
  business parent/child pid**; `server.uid` is `int ≥ 0` (the independent lldb-server may be root — the
  reused Guard does the real four-UID on-device check). With `files=True` the **actual local** host/hdc/
  lock-script and every module `.so` are SHA-verified **last** (a declared-correct `sha256` with a
  nonexistent/mismatched path is refused). Self-reported contract fields are never their own proof.

## Pins / rules (enforced by t16_validate + the injected Guard)
- Tools: host SDK15 `c6008509`, server NDK r23b `13c0b4bf` (5cd HW-proven); **forbid** old `d6d9a233`.
  `require-hardware` + no software-fallback/stepout/expr.
- Target: shim `85c789f4` lock PC **0x5e48** (player-independent); fromSurface winner @0x3bd4.
- Identity: **fresh post-restart profile** (new boot/parent/child/birth/uid/mnt + exact holder); **refuse**
  historical boot `0525…` / parent `19163` / child `1601`; host UID `20011300`; parent UID `0`.
- Scope: observe only `{magic, tag, handle, winner_module}`; `playback=UNKNOWN_NOT_TESTED`; R15 not installed.

## Use
- Preview (default, 0 device calls): `python3 run.py`
- Execute (outer only): `python3 run.py --execute --admission A.json --out DIR --r13 <pinned diagnostic-r13>`
  → validates the fresh-profile admission; returns `ADMISSION_VALID_AWAIT_PORT`. Outer starts the NDK r23b
  server `13c0b4bf` on device + `hdc forward`, then re-runs with `--port N` (inside the SDK15 host python) →
  reused R13 Session (with the **injected 5cd Guard**) connects, arms HW bps, samples, detaches time-limited.
- Offline tests: `python3 test_t16.py` (set `T16_R13_DIR` to also run reuse-structure + Guard-argv checks).

## base5 re-verification (the injected guard, not public identity)
base5's probe's `production_validation` now shows all four mutations **REFUSED** (acceptance bug closed).
Its `actual_guard_argv_prefixes` still reads 61b **because it calls the public `identity.Guard` directly** —
which is 61b *by design* under this isolation. To re-verify the actual T16 argv, call the injected guard:

```python
import t16_observer, t16_identity, sys
Guard = t16_observer.make_guard("<pinned diagnostic-r13>")   # SHA-verifies R13, binds 5cd on a private module
priv  = sys.modules[t16_identity._PRIVATE_NAME]
# patch priv.subprocess.run, then Guard(admission, out, deadline).capture('pre-connect')
# → every argv carries 5cd; sys.modules['identity'].SERIAL stays 61b.
```

The real fresh profile (new identity) is supplied by the outer once the R8 candidate module appears.
