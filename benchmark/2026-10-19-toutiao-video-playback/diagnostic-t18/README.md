# diagnostic-t18 — T16 observer specialized to one new bridge SHA (AudioTrack getter)

T18 re-links from the original 52-object baseline at **exact d4fa** and replaces a **single** audio object
(an AudioTrack getter), so the deployed bridge SHA changes. The base5-verified T16 admission gate pins
`MODULE_PINS['bridge']` to the old d4fa and will (correctly) refuse the new bridge. This directory is the
**thinnest** derivation that specializes **only that one pin** — it is **not** an arbitrary-pin interface.

## What it is / is not
- **Is:** `t18_observer.load_t18_core(t16_dir)` SHA-verifies the pinned `t16_core.py`, loads it into a
  uniquely-named **private** module, swaps **only** `MODULE_PINS['bridge']` to the one new SHA, and asserts
  every other pin/address/serial/tool SHA is byte-identical to the public T16 (else it raises). Its
  `t16_validate` is the T18 admission gate. `entry()` is `t16_observer.entry` with that one gate swapped; the
  reused R13 Session + injected 5cd Guard + the android/shim address triples are unchanged.
- **Is not:** a configurable pin. `NEW_BRIDGE_SHA` is a hardcoded constant; `load_t18_core` takes no
  `bridge=`/`pin=` argument. T16 files are never modified; loading T18 does not mutate the public `t16_core`.

## The one pin
- `bridge_new = dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9`
  (`$HOME/.local/share/westlake/t18-production/production-01/candidate.so`)
- `bridge_old = d4fae8e5…` (d4fa baseline, still the T16 pin)
- Strict source derivation pins: `t16_core.py 5c6cc445`, `t16_observer.py 0f03839a`.
- **base5 ABI review is in progress**; the derivation is ready but **deploy only on video_plan notify**. The
  Guard's on-device module-SHA check then verifies the deployed bridge == this new pin.

## Use
- Preview (0 device calls): `python3 -c "import t18_observer as T,json;print(json.dumps(T.preview()))"`
- Execute (outer only): `t18_observer.entry(admission, out, port, r13_dir, t16_dir)` inside the pinned SDK15
  host — validates with the T18 gate, then runs the reused Session (HW-only, 120 s, 4+4, bounded cleanup).
- Offline tests: `python3 test_t18.py` (8 tests: accept new bridge; refuse old d4fa + arbitrary; only-bridge
  invariance; public-T16-untouched; no-arbitrary-pin; strict source pin).

## Discipline
No board, no push, no HDC here; no new REA, no new binary patch. One object changed ⇒ one pin changed, proven
by assertion + tests. Everything else is the base5-verified T16.
