# r11 window-call observer — independent review (t6; reviewer lane)

Role: **independent reviewer** of cx-seal's r11 observer (implementation owned by cx-seal in the t4
tree `diagnostic-r11/`). I do **not** implement the observer and I do not prescribe its API choices —
I certify that its **method** honours the t6 contract and that its recorded values are
register/SHA-grounded and self-consistent. No board, no build, no device call.

## Inputs reviewed (read-only, attributed)
- Contract: main tree `specs/toutiao-video-playback/t6-window-call-observation.spec.md` (5 scenarios,
  hardware-only, lint100).
- Backend: t4 `static/window-probe-backend/results.json` — SDK LLDB15 host `c6008509…` + same-SDK
  aarch64-linux-ohos server `d6d9a233…` (NOT Homebrew22, NOT copied r10 server `eb8ce26a…`).
  `target.require-hardware-breakpoint` default false, must be **true before connect**; explicit
  hardware at creation also required. Historical 61b HW-attach: **UNKNOWN** (no receipt).
- API surface: t4 `static/window-probe-backend/python-api-review/{api.json,receipt.json}` — host lldb
  `c6008509…`, rc=0, `stdout_sha256 86fbc0f6…`, `script_sha256 67d397c3…`, device_calls=0.
- **Observer code (real): t4 `diagnostic-r11/{core.py,identity.py}`** — the decision + identity
  layers. The LLDB runtime glue (attach / hardware-bp install / callbacks / detach actions) is **not
  yet landed**.

## Pinned target SHA-256 (full 64-hex, verbatim from t6 / core.py PINS — not split, not truncated)
- player libttmplayer.so = `0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471`
- libandroid.so (`76512d97…`) = `76512d97758c308acf7baff4647f07db792c02b8fae2eda93399bd18eda03727`
- libwebview_bionic_shim.so (`85c789f4…`) = `85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a`
- liboh_adapter_bridge.so (`d4fae8e5…`) = `d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b`
- libhwui (`a11c9154…`) = `a11c9154ca16dd7acf5e3ea99727ae37c25b1b4494a9133816bc58c553c128e2`

The leading 8 hex (`76512d97`, `85c789f4`, …) is only the short prefix **of the same SHA** — do not
treat it as a separate hash. ELF offsets: fromSurface tail-call `0x3bd4`, lock entry `0x5e48`.
Object gate: `+0x00 == 0x5f776e64` → `+0xc8 == 0x414e5731` → `+0xc0` handle.

## API facts (from the verified python-api-review) — review criteria, not API mandates
1. `SBBreakpoint.SetHardware` is **`available: false`**: there is no programmatic HW promotion. The
   contract's explicit-hardware requirement is satisfied by `target.require-hardware-breakpoint true`
   **before** attach **and** explicit hardware at creation — **either** CLI `breakpoint set
   --hardware --address` **or** a by-address breakpoint created under the require setting is
   acceptable. Review checks the **actual result**: `IsHardware()==true` per installed breakpoint
   (that API *is* available) plus the global require setting read back true, and HW-slot allocation
   succeeding; abort+cleanup on any false. No software fallback, no `step-out`/`finish`, no `expr`.
2. `SetThreadID` + `SetOneShot` available: the x30 return read is achievable thread-scoped and
   one-shot without step-out. Review checks that **no step-out/finish** is used — not which primitive.
3. Reads carry `SBError`: the magic gate must be error-checked; any failure ⇒ `unknown`.
4. `GetStopReason` + `GetStopReasonDataAtIndex` give the `{bp id, loc id}` duple: each stop must be
   confirmed as the observer's own breakpoint before recording (thread id + PC + module range logged).

## Code-review verdicts (core.py + identity.py as landed)
### A. 真实身份 / real identity — **pass-logic** (runtime must invoke) ; one gap
- `core.validate`: schema+`execution_enabled`+`approved_by outer(codex)`; serial whitelist;
  `created_at<=300s`, `expires<=created+1800`; budget 120/4/4 exact; boot UUID; parent/child/server
  positive distinct pids, `uid==parent_uid==20011206`, 64-hex exe SHAs; host/server tool SHA pinned;
  `modules`set==PINS exact roles; per-module `sha==PIN` + positive device/inode + `/data/` path +
  local sha==PIN.
- `identity.py` bookended capture: `BOOT==e.boot==BOOT_END`; per-proc stat START==(pid,birth)==END,
  state∉Z/X, `UID==[uid]*4`, child ppid==parent; parent/child exe SHA; per-module actual SHA +
  `(device,inode)` + `mapped_module` dev/ino; **mapped-instance set bookend-identical**.
- `core.biases`: ASLR-safe bias from PT_LOAD vs maps; requires header+executable+`len(rs)>=2`.
- **Gap:** `biases()` returns **all** unambiguous same-name instances (double-mapped namespaces are
  allowed); the **player-slot selection** — which instance libttmplayer's GOT `lock`/`fromSurface`
  calls actually land in — is **not** in these two files. It must be enforced and evidenced in the
  (unlanded) LLDB runtime, and I will review it there. Until then, "winner/object" cannot be tied to
  the player's own window.

### B. 硬件断点 / hardware breakpoints — **pending-observer**
`core.py`/`identity.py` contain no lldb attach/bp code. When the runtime lands I check: require
setting read back true before connect; each bp (`0x3bd4`, one-shot x30, `0x5e48`) `IsHardware()==true`
+ allocation ok; no SW fallback/step-out/expr; host+server SHA == pinned (already enforced by
`validate`).

### C. 返回点关联 / return-point association — **pass-logic**
`core.Calls.tail` refuses overlapping fromSurface and budgets `from_count<4`, recording
tid/sp/ret(pc)/seq/winner; `Calls.returned` matches the return on **(tid,sp,pc)** — stronger than
thread-only — and refuses a mismatch. Cross-thread is allowed; `same_object_generation` defaults
`unknown` (no auto object-lifetime merge). Concurrent fromSurface across threads is *refused*
(conservative) — a limitation, not a violation.

### D. 超时 detach / bounded exit — **partial** (verification strong; action glue pending)
Present: `MAX_SECONDS=120`/`MAX_FROM=4`/`MAX_LOCK=4`, `Calls.complete()`, admission expiry ≤30min;
`identity.py` after-phase asserts `TracerPid==0` **and** child state ∉ `('T','t')` ("still
traced/stopped"), refuses a foreign tracer, and requires mapped-instance stability — a real
recovery check. Pending: the **action** side (delete only self-made bps, `Continue`, `Detach`
keep-stopped=false) lives in the unlanded runtime; and the output must never assert `playback_pass`.

### Object decode — **pass**
`core.wrapper` gates strictly: `+0`==`0x5f776e64` then `+0xc8`==`0x414e5731` then `+0xc0` handle≠0;
any miss/exception leaves `class='unknown'` with a typed reason; success is
`class='AdapterAnw_layout_matches'` (layout-matches, not asserting the object's identity).

## Verdict protocol
Per observer version each axis A–D ⇒ `{pass|fail|unknown}` with the exact evidence line (register
value, `IsHardware` result, stop-reason duple, cleanup rc, TracerPid). Human review (t6 "真机结果
独立审核") owns the final winner/object-type truth and the two-cycle t3 playback; I certify
method-conformance and register/SHA-grounded self-consistency only. Un-collected ⇒ `unknown`.

## Status
- **Decision + identity layers reviewed:** A pass-logic (player-slot selection gap), C pass-logic,
  object-decode pass, D verification-strong. **LLDB runtime glue not landed** ⇒ B pending and D's
  action side pending.
- The late `check_observation.py` under this worktree's `diagnostic-r11/` is **reference only**
  (outer's ruling); this review does not depend on it. cx-seal owns the observer.
