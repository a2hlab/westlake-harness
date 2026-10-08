# route-A signal chaining defeats app SIGILL-guarded probes — deployed-artifact analysis + 166-key exposure scan

#90, cc-t3, offline, **no board**. Follow-on to `mcdonalds-sigill.md` / `disappeared.md`. Establishes, from the
**deployed artifacts named in `composition.json`** (not hw248 source — the deployed binary is the source of truth, per the
repo's "静态优先 / 判断对象=对的部署件" rule), exactly where route-A's signal chaining deviates from AOSP and why a rethrown
SIGILL produces no cppcrash; then scans the full native corpus for every key exposed to the same defect.

Effective artifacts (U14 `composition.json`): `libsigchain.so = 6d5d5538…` (AOSP/ART sigchain) +
`ld-musl-aarch64.so.1` (OH musl, the `MUSL-SIGCHAIN` logger). Both read as deployed; strings/symbols quoted below are
from those binaries.

## ① Where route-A deviates from AOSP libsigchain (deployed `ld-musl` `signal_chain_handler`)

### What the deployed OH musl chain actually does (proven by its own format strings)
`ld-musl-aarch64.so.1` is the kernel-installed handler for chained signals. Its `signal_chain_handler`, per the deployed
format strings, runs this order for a delivered signal:
1. **Loop over "special" actions** — `"%s call %d rd sigchain action for signal: %d sca_sigaction=%llx noreturn=%d …"`.
   Registered via the exported `add_special_signal_handler` / `add_special_handler` / `add_special_handler_at_last`
   (and `remove_*`). These are the privileged in-runtime handlers (ART's fault manager registers here).
2. If none: `"signal_chain_handler sca_sigaction all null for signal: %d"`.
3. **One** "usr" slot — `"%s call usr sigaction for signal: %d sig_action.sa_sigaction=%llx"`. Note the **singular** "usr
   sigaction" (one slot per signal) versus the **looped** special actions. This is the slot an *application's*
   `sigaction()` is meant to occupy.
4. `"%s SIG_DFL handler for signal: %d"` if the usr slot is `SIG_DFL`.
5. `"pid(%ld) rethrow sig(%d) success."` / `"Failed to rethrow sig(%d), errno(%d)."` — re-raise.

The deployed AOSP `libsigchain.so` (6d5d5538) exports the matching `AddSpecialSignalHandlerFn` / `add_special_signal_handler`
/ `EnsureFrontOfChain` — i.e. **two** sigchain managers ship in route-A and they share the *special*-handler ABI, but each
keeps its **own per-signal tables**. The kernel only enters the OH musl one.

### The deviation, pinned to the mcdonalds log
mcdonalds SIGILL(4), thread 15285:
```
MUSL-SIGCHAIN: signal_chain_handler call usr sigaction for signal: 4 sig_action.sa_sigaction=7f095d6a6c   <- libart, NOT akamai
MUSL-SIGCHAIN: signal_chain_handler SIG_DFL handler for signal: 4
MUSL-SIGCHAIN: pid(15264) rethrow sig(4) success.
```
No special action claimed SIGILL (ART's fault manager claims SIGSEGV/SIGBUS/SIGABRT, not SIGILL), so the chain fell through
to the single **usr** slot — and that slot held **libart's** handler (`7f095d6a6c`), **not akamai's**. libart did not fix
up the probe's PC → `SIG_DFL` → `rethrow` → fatal.

**Deviation vs AOSP** (single libsigchain, one table): on stock Android akamai's `sigaction(SIGILL, akamai_h)` is recorded
as the app action *behind* ART's specials; when SIGILL fires, ART's special declines it and libsigchain invokes
**akamai_h**, which advances the PC past the illegal `MRS` and returns → execution resumes, probe "fails closed", app lives.
Under route-A the app's bionic `sigaction` is ABI-bridged (`westlake_musl_sigaction_bridge` / `unity_signal_box`, the
sigset_t-size shims) into a table that is **not the one the kernel-level OH musl chain consults for the usr slot** — the usr
slot the OH musl chain ultimately calls is ART's handler, so **akamai's recovery handler is never invoked**. Net: the two
tables disagree (AOSP-libsigchain may hold akamai; OH musl holds libart), and the kernel path uses OH musl's → libart →
rethrow. (Whether the exact mechanism is "ART shadows the usr slot via EnsureFrontOfChain" or "the bridge records app
handlers in the wrong table" is the one open variable — resolved by the ③ experiment; both are route-A deviations with the
same fatal outcome.)

### Why the rethrown SIGILL writes no cppcrash (corrected — not the EACCES fd)
The chain terminates by setting **`SIG_DFL`** and **`rethrow`**-ing (`rethrow sig(4) success`). Re-raising against
`SIG_DFL` takes the **kernel default** action for SIGILL = *terminate*, which **does not pass through OH's
`DfxSignalHandler`** → no cppcrash, no faulting PC. SIGSEGV (firefox/localsend) instead reaches DFX and dumps a cppcrash —
the difference is signal-specific, this SIGILL ended in rethrow→SIG_DFL. The `[ROUTE-A] child diagnostic fd unavailable:
errno=13` line is a **red herring**: the outer verified it appears in **386/386 U14 hilogs (incl. lit helloworld)** and
firefox/localsend wrote cppcrashes *with* that line present. The empty faultlog is a downstream symptom of the sigchain
rethrow path, not the fd.

## ② Full-corpus exposure scan — keys with (signal-handler install + probe instruction)

Scan (`probe_scan.py` → `probe_scan.json`): the U11-native per-key APK native corpus (`2026-10-01-u11-native/.artifacts/
window-r{1,2,3}-scan/consumers/<key>/…/*.so`, dedup by (key, soname), WORKSPACES-anchored). A lib is flagged when it BOTH
(a) imports a signal-handler installer (`sigaction`/`signal`/`sigprocmask`/`sigaltstack`) AND (b) contains a probe
instruction: `MRS` of an **EL0-illegal** system register (S3_[567]_*, TRC*, DBG*, impl-def — the EL0-legal set
CNTVCT/CNTFRQ/TPIDR/CTR/DCZID/MIDR/ID_* is whitelisted), `RNDR`/`RNDRRS`, PAC sign/auth, or `udf`. Such a lib can raise a
SIGILL/SIGSEGV it expects its own handler to recover — exactly the pattern route-A's chain defeats.

Scan output: `probe_scan.json` (491 unique (key,lib), **87 install a signal handler**, **25 also carry a probe
instruction**); classified by `classify_probe.py` → `probe_classified.json` into three tiers because **presence of a probe
lib ≠ exposure** — the register matters:

| tier | meaning | lib-hits | distinct keys |
|---|---|---|---|
| **A** | **deliberate ALWAYS-EL0-illegal sysreg read** (trace `TRC*`, `S3_6/7/4/5_*`, impl-def) — an anti-tamper probe that *intends* to trap; THIS defect's true class | 2 | **1: mcdonalds** |
| **B** | **feature-gated EL0 read** (`DIT`/`SVCR`/`GCSPR_EL0`/`RNDR`) — traps **only** if the board lacks the feature AND the app mis-gates HWCAP | 13 | 10 |
| **C** | `udf`/`brk` stub only, **no** sysreg MRS — abort/trap codegen (Flutter/mpv/Qt/Go), **unrelated** to this defect | 40 | 21 |

### Class A — the only key the defect actively blocks today
| key | lib | illegal MRS | note | current first-fatal |
|---|---|---|---|---|
| **mcdonalds** | libakamaibmp.so | **170** (TRCSSCSR6, S3_6/7_*, …) | Akamai Bot Manager anti-tamper **sysreg sweep** — reads 170 EL0-illegal regs behind a `sigaction`+`sigprocmask` guard | **SIGILL (this defect)** |
| mcdonalds | librealmc.so | 11 (+ 4× RNDR) | secondary; Realm normally HWCAP-gates RNDR, lower confidence | (same process) |

**mcdonalds is the ONLY key in the whole 166-corpus whose current first-fatal is a SIGILL *and* that carries a Class-A
always-illegal probe.** The defect's active blast radius today = **1**.

### Class B — latent, with a built-in control group that proves it is NOT currently firing
10 keys read a feature-gated reg behind a handler: burgerking, fd-client, fd-feeder, fd-fennec_fdroid, fd-fluffychat,
fd-immich, fd-minetest, firefox, ooniprobe, x. Two facts make these **latent, not active**:
1. **Control group (same libs, LIT)**: `fd-client` (libcrypto `RNDR`), `fd-feeder` & `ooniprobe` (Go `libgojni` `DIT`),
   `fd-minetest` (`libluanti` `GCSPR_EL0`) are **LIT** despite carrying the identical feature-probe reads → those libs
   **HWCAP-gate correctly**, so the reads never execute on this A55 board. Presence ≠ trap.
2. The **unlit** Class-B keys crash for **unrelated** first-fatals, not a SIGILL: fd-fennec = libmozglue **sysconf**
   SIGSEGV, fd-fluffychat = **libflutter** raster SIGSEGV, fd-immich/firefox/x = no-U14-obs (prior disappeared/singleton).
   None is currently blocked by the sigchain defect.

→ **Class B adds 0 to the current wall count via this defect.** It is the *future* risk surface: if a Class-B app ever
mis-gates a feature the board lacks, it would hit the same rethrow-no-recovery path. Worth re-checking only if a new board
or a HWCAP-masking change lands.

### Class C — not this defect
21 keys' hits are `udf`/`brk` in abort/panic stubs (Flutter `libflutter`, `libmpv`, Qt, Hermes, Go). No system-register
probe. Their first-fatals (Flutter raster, FDSAN, no-termination, sysconf, singletons) are the ones already clustered in
`README.md` — listing them here would be double-counting. Excluded.

## ③ Fix direction + predicted move + minimal critical experiment (runtime behaviour — NOT frozen; no board here)

Signal chaining is **not** in `frozen.json` → the outer may approve a change. But this is **runtime** behaviour (table
ordering, handler-return semantics) that static reading narrows but does not fully settle, so per repo rule the change must
be gated behind a minimal experiment with a written criterion and fallback — stated here, **not run in this lane**.

**Fix direction** (owner: route-A signal-chain compat — the `bionic-signal-box` / `unity_signal_box` bridge + OH musl chain;
NOT ANW, NOT Flutter/sysconf):
1. **One usr table**: an app `sigaction(sig, h)` must update the *same* per-signal usr slot the kernel-level OH musl
   `signal_chain_handler` consults (and return the prior usr for the app to chain). Today ART's handler occupies that slot
   for SIGILL; the app's registration lands elsewhere.
2. **Honor recovery**: when the usr handler returns without re-raising, resume at the (handler-modified) PC — do **not**
   force `SIG_DFL`+`rethrow`. Only rethrow when usr ∈ {SIG_DFL, SIG_IGN}. (bionic / AOSP-libsigchain semantics.)
3. **Keep DFX terminal**: when the chain must kill, route the terminal through `DfxSignalHandler` so genuine fatals still
   produce a cppcrash, instead of a raw `SIG_DFL` rethrow that blinds DFX.

**Minimal critical experiment** (distinguishes the one open variable; criterion + fallback):
- *Probe*: a trivial bionic test `.so` loaded the route-A way (`System.loadLibrary` from a one-Activity APK) that does
  `sigaction(SIGILL, h)` where `h` advances PC+4 and sets a flag, then executes `mrs x0, TRCSSCSR6` (same illegal class as
  akamai).
- *Criterion*:
  - Process continues, flag set → a **lone** app SIGILL handler DOES recover under route-A; mcdonalds' failure is
    **usr-slot shadowing by libart** (fix #1 is the lever).
  - Process dies; MUSL-SIGCHAIN shows `usr sigaction sa_sigaction=<h>` (our handler) then `SIG_DFL`+`rethrow` → the chain
    **does not honor recovery** (fix #2 is the lever).
  - Process dies; log shows `usr sigaction sa_sigaction=<libart>` (not `<h>`) → **shadowing confirmed directly** (fix #1).
- *Fallback (退路, fully static, no board)*: disassemble OH musl `signal_chain_handler` + the bionic→musl `sigaction` bridge
  to read (i) whether the usr slot is a single global and who wins last-writer, and (ii) whether the usr-return path
  unconditionally sets `SIG_DFL`+rethrow. This static read alone separates fix #1 vs #2; it is the safe path if no free
  board or the test `.so` won't load.

**Predicted move**: mcdonalds **0–1, uncertain → 搁置** (anti-tamper may refuse to run even after recovering, stopping at a
verdict wall rather than lighting). The payoff is **class-wide**: see the ② table for every key exposed to the same chain
defect and its current first-fatal.

## Summary
Route-A ships two sigchain managers (OH musl built-in + AOSP libsigchain) with independent per-signal tables; the kernel
enters only OH musl's, whose **single usr slot for SIGILL holds ART's handler, not the app's** — so an app's SIGILL-guarded
probe never gets its recovery handler, and the chain ends in `SIG_DFL`+`rethrow`, which kills the process **outside DFX**
(hence no cppcrash — the EACCES fd is unrelated). Fix = one usr table + honor handler recovery + DFX-terminal; gate it
behind the stated SIGILL-probe experiment. Exposure beyond mcdonalds is enumerated in ② (`probe_scan.json`).
