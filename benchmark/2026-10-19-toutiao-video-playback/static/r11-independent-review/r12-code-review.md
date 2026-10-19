# tool-compat-r12 — incremental code review (current SHAs; re-verify at final SHA)

Files (t4 `tool-compat-r12/`): `policy.py 8aa6308ec6f867ff`, `guard.py dbbebcb6d17ba9d6`,
`engine.py 8ee1fe0ea1877819`. Probe build `8ab9acaf`, marker ELF `0x1af0`. Still changing — re-check
at final SHA. Read-only, no device call.

## Five focus areas — all PASS (no substantive blocker)
### pin / target-PID boundary — STRONG
- `policy.validate`: schema `r12-admission-v1` + `execution_enabled` + `approved_by outer(codex)`;
  serial 5cd + port 5039; probe/server `pid>1`, `sha256==PROBE_SHA/SERVER_SHA`,
  `remote_path==owned_root+'/probe'|'/lldb-server'`, `device/inode>0`, distinct PIDs; host SHA pin;
  `remote_root` regex `=/data/local/tmp/wl-debug-compat-<boot[:8]>-[a-z0-9]{8,32}`.
- `policy.preflight`: port proven free (no `0A` listener on 5039), `ROOT==ABSENT`, probe/server PID
  **not** in the before-PIDs set → proves they are new processes.
- `guard.capture`: `od -An -v -tx1 /proc/<pid>/cmdline` byte-compared — server argv must be
  `gdbserver 127.0.0.1:5039 --attach <probe.pid>` (server bound to the probe only); `readlink exe`,
  `sha256sum exe`, `stat inode` all match; PID/birth bookended; `Uid==[uid]*4`.
- `engine`: after connect `need(GetProcessID()==probe.pid)`, re-checked every `guard_now`. No
  name-based selection anywhere.

### SDK implicit teardown on handshake failure — STRONG
- `connect` uses `need(e.Success() and proc.IsValid())`; a no-stop-reply (the r11 assertion mode)
  raises → `cleanup` → `entry` `os._exit(2)` on unverified. No reliance on LLDB's implicit quit.
- **Recovery proof is server-independent**: `guard.capture(after=True)` reads the probe `/proc` via
  `hdc` (not via lldb-server), so a dead server still yields the after-detach proof (TracerPid=0,
  state∉T/t, probe stdout counter increasing across two 0.6s-apart captures). Target is a disposable
  probe, removing the frozen-target risk. Raw handshake/exception persisted before exit.

### hardware Continue — STRONG
- `install`: `breakpoint set --hardware --address`; records IDs even on failure; `need(IsValid and
  IsHardware and GetNumLocations==1)`; loc resolved at exact addr. `resume`: `Continue` (no step-out).
  `hit`: stop reason == Breakpoint with the owned `{bid,locid}` duple, `IsHardware` re-checked; raw
  pc/x0/tid/stop_id logged before any refuse.

### new StopID — STRONG
- `wait` returns only on `eStateStopped ∧ GetStopID()>resume_id`; `Hits.add` enforces
  `stop>resume_stop` and, for the 2nd hit, `stop>prev.stop_id ∧ x0>prev.x0 ∧ tid==prev.tid`.

### timeout force-exit — STRONG
- `deadline=min(start+60, start+(expires-now))`; `budget`/`wait` raise at deadline; `packet-timeout 4`
  bounds a hung server packet; SIGTERM/SIGINT collapse the deadline; unverified cleanup → `os._exit(2)`.
  Probe 120s self-exit is backstop, not evidence.

## Non-blocking notes (for final-SHA recheck / CX)
1. A dead server leaves the probe kernel-detached (TracerPid→0, resumes) so the after-detach proof can
   look healthy while `c['detached']=False` → `verified=False` → `os._exit(2)` → outer recovery. Correct;
   the receipt distinguishes via the `detached` flag. "probe healthy" ≠ "clean LLDB detach".
2. Success status is `PROBE_COMPATIBILITY_ONLY_PENDING_OUTER_FORWARD_CLEANUP` — correctly NOT claiming
   Toutiao/playback, and the 5039 forward teardown is explicitly left to outer (matches my t7 note).
3. Confirm the probe's launch redirects stdout to `remote_root+'/probe.stdout'` (guard reads `COUNTS`
   from there); marker `r12_marker` is `noinline` FUNC and unique (policy.marker enforces uniqueness).

## Verdict
No substantive blocker at these SHAs. Will re-verify the 5 areas at the final SHA. No device call.
