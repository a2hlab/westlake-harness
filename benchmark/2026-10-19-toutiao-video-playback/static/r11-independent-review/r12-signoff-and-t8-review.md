# R12 probe tool-compat SIGN-OFF (independently verified) + t8/r13 contract review

Offline, no device call. Scope strictly limited per t7/t8: sign tool compatibility on the 5cd
self-owned probe ONLY; Toutiao object/winner/geometry/playback remain UNKNOWN.

## R12 probe compatibility — SIGNED (method + evidence independently confirmed)
Raw: `BASE20/toutiao-resume-20261020/r12-r12oct20b-observation/` (read-only). Every claimed fact
reproduced from the raw receipt:
- `result.json` + `raw-hits.jsonl` agree: marker `0x557bae4af0` (=367147240176); **two hardware hits**,
  same **TID 1610**, pc==marker both, **x0 9→10** (+1 counter), **StopID 2→4** (two distinct new stops,
  Continue between).
- `commands.jsonl`: `settings set target.require-hardware-breakpoint true` ok, `breakpoint set
  --hardware --address 0x557bae4af0` ok → hits were real hardware; `process detach --keep-stopped false`
  ok.
- `cleanup.verified=true` (deleted+detached); after-detach bookend TracerPid=0, state=S, **counter
  12→16** (probe resumed), identity stable, `outer_owned_process_recovery_required=false`.
- `host.rc.json` rc=0 not-timed; pre-connect tracer=server-pid 1758 state=t (server-attached, expected).
- `toutiao/playback=UNKNOWN_NOT_TESTED`; status `PROBE_COMPATIBILITY_ONLY_PENDING_OUTER_FORWARD_CLEANUP`.

**SIGNED:** SDK15 host `c6008509` + NDK r23b static server `13c0b4bf` can **attach + install one
hardware breakpoint + read a register (x0) + Continue + clean keep-stopped=false detach** on a 5cd
self-owned OH probe, working around the r11 SDK15-server `DataExtractor GetMaxU64` assertion.
**NOT signed:** the probe read only a *register at a marker*; it did NOT exercise the ANW object
**memory** reads (`+0/+0xc8/+0xc0`) or the business handshake. Toutiao window-object type, winner,
geometry, and playback stay UNKNOWN. This does not extrapolate to 61b/Toutiao.

## t8-window-call-r13 contract — reviewed: NO substantive blocker
`specs/toutiao-video-playback/t8-window-call-r13.spec.md` (5 scenarios, lint100). It is **t6
(window-call-observation) with exactly two changes**: (1) server pin `d6d9a233`→**`13c0b4bf`** (the
r12-validated r23b); (2) `diagnostic-r13` / r13 deployment prefix. Verified preserved from r11/t6:
- all gates: 61b whitelist + outer-given boot/PID/birth; full-64-hex libandroid `76512d97…` / shim
  `85c789f4…`; PT_LOAD/maps/inode ASLR-safe addressing + player-slot selection; `0x3bd4` (x2 winner +
  x30 return) / `0x5e48` lock; magic gate `+0=0x5f776e64 → +0xc8=0x414e5731 → +0xc0 handle`, fail⇒
  unknown, no raw guess, no target-fn call; winner bound to actual mapped module (no dlsym/union);
  cross-thread not auto-merged; require-hardware + explicit `--hardware`, no SW fallback/step-out;
  ≤120s, ≤4+4; delete-own-bp + detach keep-stopped false + TracerPid/state verify; **禁止 kill 全局
  hdc/server 或按名杀** (the 61b child is Toutiao — NOT killable, unlike r12's disposable probe —
  retained); r10 apply-plan rollback 20/30min.
- correctly scoped: records the r12 evidence and states "r12专用探针证明不外推为头条兼容 / 实际业务
  握手失败仍unknown"; human receipt signs only actual captured winner/object, playback via t3.

### The one substantive residual (contract already acknowledges — not a blocker)
R12 proved the server on a **register** read; r13 performs ANW **object-memory** reads
(`ReadMemory`/`ReadPointerFromMemory` at `window+0/+0xc8/+0xc0`). The r11 `GetMaxU64` assertion fired
during the SDK15 server's read path; whether the r23b server survives the **object-memory** path is
NOT proven by the probe. The contract captures this as an explicit unknown ("业务进程兼容仍未知") —
so it is honestly scoped, and r13 is the real test. No change required; just flag for the human receipt.

## Final small-diff review (pending CX r13 code)
When diagnostic-r13 lands, verify the diff vs the passed r11 observer (core/identity/observer/observe)
is **ONLY**: `SERVER_SHA d6d9a233→13c0b4bf`, the r13 deployment-dir prefix, and the `_r13` test name —
with **no** change to the observer logic, magic gate, return-point association, cleanup, or the no-kill
rule. Any logic delta beyond these three is out of the "minimal successor" scope and must be reviewed.
