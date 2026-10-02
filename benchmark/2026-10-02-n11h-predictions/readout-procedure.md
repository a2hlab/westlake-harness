# N11h 61b window — readout procedure

How to read the N11h observation window (plan-n11h-61b.json). Verdict is always the outer t20 screenshot; this
procedure is the hard-smoke / marker checklist the window must pass before per-key observation counts.

## 1. bridge / runtime = 1 load-base (the N11h goal) — from the child maps
Target: in the bridged child process, `liboh_adapter_bridge.so` and `liboh_android_runtime.so` each have **exactly
one load base** (U9/U10.1 have two each; N11f/N11g proved the child is clean, so the 2nd copy is host-side).

Method (per `maps-t5-<pid>.txt` / `maps-t20-<pid>.txt` of the app's child, pid from the run's processes files):
```
# count LOAD BASES = distinct executable (r-xp) segment start addresses for the lib's own path
for lib in liboh_adapter_bridge.so liboh_android_runtime.so libart.so libopenjdkjvm.so; do
  n=$(grep " r-xp " maps-t5-<pid>.txt | grep -E "/$lib$" | awk '{print $1}' | sed 's/-.*//' | sort -u | wc -l)
  echo "$lib load-bases=$n"
done
```
- **Count by LOAD BASE, not inode and not line count.** One mapped .so shows several lines (r--p header, **r-xp**
  code, rw-p data, often a `.bss`); count only the **r-xp** segment, and count **distinct start addresses** (each
  distinct r-xp base = one independent load of the file). The same path appearing on multiple non-r-xp lines is one
  copy; two different r-xp base addresses for the same path = two copies.
- **PASS**: `liboh_adapter_bridge.so` = 1 AND `liboh_android_runtime.so` = 1 (and `libart.so` = 1, `libopenjdkjvm.so`
  = 1 as controls). This is also what `knowledge/smoke/n11h.json` probe `expect_copies` asserts.
- **FAIL**: either owner still = 2 -> single-owner NOT achieved -> stop before observations, rollback. (U9/U10.1
  baseline reference: both owners = 2; the failing T8-window wikipedia maps-t5-16137 showed bridge=2, runtime=2.)
- Reference precedent: the N11g window (PID 6873) counted bridge at `7ef6080000 / 7efddc0000` and runtime at
  `7ee0700000 / 7ef6240000` = 2 load bases each -> that was the REFUTED (still-double) outcome. N11h PASS is one
  r-xp base per owner.

## 2. `[U10-COMPAT-VISIBLE] unavailable` — how to judge (it is non-fatal)
The N11h host keeps the U10 compat-owner step. In `stock-host.patch` the only place this marker is emitted is:
```
if (compat_ready && !compat_sealed) {               // the compat owner exists but is NOT the sealed ns
    ... APPSPAWN_LOGE("[U10-COMPAT-VISIBLE] unavailable inherit result=%d; namespace continues", compat_result);
}
```
So `[U10-COMPAT-VISIBLE] unavailable` means: the **optional** non-sealed compat-owner inherit did not attach, and
the code **explicitly continues** ("namespace continues"). It is **informational / non-fatal**, NOT a smoke failure.

Judgement:
- The authoritative host proof is **`[N11h-HOST-OWNER] action=inherit ... owner=westlake.sealed.child ... rc=0`**
  (plus `action=resident-check ... rc=0`). On the normal N11h path the app domain inherits from the **sealed** owner
  (`compat_sealed` true -> `N11H_COMPAT_LIBS` = bridge:runtime:libbionic_compat), so the `[U10-COMPAT-VISIBLE]
  unavailable` branch is **not taken** and the marker is simply absent.
- If `[U10-COMPAT-VISIBLE] unavailable` DOES appear while `[N11h-HOST-OWNER] action=inherit ... rc=0` is present →
  **PASS**: the compat (non-sealed) owner was absent but the sealed-owner inherit still ran; the namespace continues
  by design. Do not treat "unavailable" as a regression.
- Only treat it as a problem if it appears **together with** a failing `[N11h-HOST-OWNER]` (rc!=0) or a
  `[N11h-HOST-OWNER] action=reject` (sealed owner namespace missing) — that is the real failure, caught by the
  HOST-OWNER marker, not by the COMPAT line.

## 3. Host markers (from knowledge/smoke/n11h.json; literals verbatim from cx-bms source)
- REQUIRED (fire every spawn, helloworld control): `[N11h-HOST-OWNER] action=resident-check target=.. owner=.. rc=0`
  and `[N11h-HOST-OWNER] action=inherit target=.. owner=westlake.sealed.child shared=.. rc=0`.
- CONDITIONAL: `[N11h-HOST-OPEN] action=(resident|reject) ..` fires only when StockOpenNamespace gets an exact
  owner-path request; the control may not reach it. Do not fail the control gate on its absence (see n11h.json).
- FAILURE marker: `[N11h-HOST-OWNER] action=reject ... owner=sealed` = the sealed owner namespace was missing ->
  the spawn fenced -> stop + rollback.

## 4. Per-key verdict (after hard smoke passes)
- Verdict = outer reads each key's t20 and compares cell-by-cell against the U9 reference contact sheets
  (`benchmark/2026-10-02-u10-1-t8-rerun/u9-reference/u9-ref-<board>.{jpeg,txt}`) and the prediction
  (`n11h-predictions.csv`), via predict_vs_actual.
- Gain = a key predicted `lit` (4 session-miss high-conf + 7 other no-fatal) that is now lit at t20. A session-miss
  target still white refutes the gain. The 3 another-wall keys (x / cv2-dev-obfusk-jiten-webview /
  fd-shatteredpixeldungeon) staying white does NOT count against N11h. Canaries + wikipedia must stay lit (a
  regression refutes the gain); note wikipedia is a flaky key (its white can be the render lottery itself, so read it
  against its own flakiness, not as a hard control).
