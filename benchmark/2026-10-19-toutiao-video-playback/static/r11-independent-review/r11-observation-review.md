# r11 device run #1 — independent review of the actual receipt (no pass claimed)

Raw: `BASE20/toutiao-resume-20261020/r11-observation/{result.json,events.jsonl,exception.txt,
identity-00{1,2}-*}` (read-only). freshboot `d02104c8`. No device call / no change by reviewer.

## What the receipt actually establishes (positive, bounded)
- Admission identity validated and matches the field counter-evidence: boot `d02104c8…`, child **18005**
  uid **20011206**, parent **4952** uid **0**, both exe sha `a7a358c6…`. (`core.validate` passed.)
- `platform select remote-ohos` reached: one event `target_platform name=remote-ohos triple=
  aarch64-unknown-linux-unknown` at 1.99s. `tool_version` = SDK lldb 15.0.4.
- Child survived safely: external bookended `/proc` capture `identity-002-after-detach` →
  `tracer_pid=0, state=S`, child/parent pid+birth unchanged, `lock_matches=true`.

## What FAILED and what stays UNKNOWN
- `ConnectRemote('connect://127.0.0.1:5039','gdb-remote')`: "Process 18005 was reported after
  connecting, but **no stop reply packet was received**" → `Refuse` at `observer.py:162`, before any
  breakpoint install. Root tool cause (CX domain, NOT investigated here): SDK **lldb-server
  `DataExtractor.cpp:526 GetMaxU64 byte_size` assertion → server exited**.
- **Zero call samples:** `fromSurface_count=0`, `lock_count=0`, `pending_return=null`, `events`=only
  the platform line. Therefore **winner = UNKNOWN, lock object type = UNKNOWN, geometry = UNKNOWN**.
  The magic gate (`0x5f776e64`/`0x414e5731`) never ran → **no AdapterAnw determination**.
- `playback=UNKNOWN_NOT_TESTED`, `audio=UNKNOWN`, `same_object_generation=UNKNOWN_NOT_TRACKED`.
  **Neither layout nor playback is pass** — nothing was observed.

## Observer conduct under failure — correct
- Refused on connect (no false attach); cleanup recorded `verified=false`,
  `breakpoint_cleanup_error="wait stopped timeout"`, `detach_error="Process must be launched"` (no
  process to detach), `status=OUTER_RECOVERY_REQUIRED`; `os._exit(2)` on the unverified path. Evidence
  (`result.json`, `events.jsonl`, `exception.txt`) persisted before exit. The external `/proc` proof
  (tracer 0, state S) supplies the recovery evidence the LLDB side could not — no frozen child.
- Outer is rolling back to freshboot on the original plan; that is hygiene, not corruption recovery
  (the child was never truly attach-stopped — "no stop reply").

## Selection-table outcome for this run
Per `fix-selection.md`: the lock-entry object was **never sampled** ⇒ `object = unknown` ⇒
**row 2: NO modification permitted.** The verified-ANW reuse candidate (shim `webview_bionic_shim.c`
`f12c5c92` unwrap+OH `lock`@3962 / `unlockAndPost`@4040, gated on the deployed-shim disasm) **remains
the standing candidate for a future run that actually observes an `AdapterAnw_layout_matches` object** —
but this run authorizes **no change**. Do not infer wrapper-vs-raw, winner, or geometry from a
zero-sample run.

## Reviewer scope
Independent review of the raw receipt + limits only. The lldb-server DataExtractor assertion is CX's
tool investigation; not duplicated here. No layout/playback pass; un-collected ⇒ unknown.
