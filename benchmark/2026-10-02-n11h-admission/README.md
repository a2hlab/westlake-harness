# N11h admission review — accepted bytes, not window authorization

The earlier handoff preserved the compat **helper**, but did not preserve its
**call timing or private-branch evaluation**. Unchanged helper source is not zero
behavior delta. This package makes that delta explicit, supplies nineteen exact
string allowance checkboxes, and rebinds identical findings without approving the
one new owner query. No device was accessed and no runtime or live registry changed.

## Immutable review identity

| Item | SHA256 / commit |
|---|---|
| Outer-landed candidate source | `3b05c71c1c` |
| r3 host | `65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284` |
| Accepted N11h host | `65ac50894de8d06e32439d2aee91f61eb1c45d6c0822826d529f671ca3c49aed` |
| Accepted audit package manifest | `37c48e2b07e5e757bc872f174f883d44cc0f369a19b035afe9035b2a115286bf` |
| Accepted audit inputs | `a825ba2387793c9904a18a8b6ee95d4f695f968511d1fb31921d63255b333fc3` |

The binaries remain in
`$WORKSPACES/westlake-harness-bms/benchmark/2026-10-02-n11h-host-owner/.artifacts/frozen-r1/{baseline,candidate}/appspawn-x`.
The accepted source/build/toolchain archive and gates stay in the previously
landed `benchmark/2026-10-02-n11h-host-owner/`. There is no new host build here.

## 1. Compat timing delta and smoke interpretation

Evidence: `evidence/timing-replay.json` contains the complete trace of the **actual
accepted C callbacks**, compiled against `timing_fixture.c` fake platform effects.
Bootstrap mapping is deliberately simulated, not claimed as a device observation.
The late case exposes compat only in sealed (default lookup unavailable), so the
late successful r3 inherit is specifically the same sealed parent needed by the
early N11h owner edge, not a default-only escape from the once-per-pair constraint.

| Fixture | r3 query / bootstrap sequence | N11h query / bootstrap sequence | Observation |
|---|---|---|---|
| Resident before callback | 13 / 6 | 18 / 26 | Both query-verified |
| Becomes resident during bootstrap | 13 / 6 | 18 / 23 | r3 verified; N11h unavailable; both callback rc=0 |
| Never resident | 13 / 6 | 18 / 23 | Both unavailable, nonfatal |
| Private app, resident early | 19 / 6 | no query / 22 | r3 queries; N11h short-circuits it |

The late fixture changes the ordinary app's compat-containing edge count from
1 to 0. For private apps the existing **two distinct parents**, sealed and
default, retain their compat-containing edges; this is not repeated inherit on
the same pair. Sequence numbers are fixture event indices, not elapsed time.

Source order is decisive:

- r3 `../2026-10-02-n11h-host-owner/inputs/host-r3.c:323` evaluates
  `U10ShareResidentCompat` **before** `!flutter_private && !native_private`.
  Its bootstrap was already opened. Private apps still emit query logs, but do
  not take the ordinary optional inherit branch.
- N11h `../2026-10-02-n11h-host-owner/src/candidate-stock-host.c:249` tests
  private guards before the helper, selects `owner_shared` at line253, and inherits
  at line255, all before bootstrap. Private/no-bridge callbacks emit no compat marker.

### Can the old timing and a single inherit both be preserved?

Not generally with the accepted namespace graph and conditional permissions.
For a sealed provider that first becomes resident during bootstrap, selecting
the merged compat whitelist from the old **post-bootstrap** query result cannot
also happen **before bootstrap**. Always pregranting compat could preserve a
later diagnostic but changes the old conditional whitelist. Repeating sealed
inherit reintroduces OH's overwrite bug; moving that edge after bootstrap breaks
the early owner-publication requirement; adding a new parent changes the graph.
If a provider were independently guaranteed to be default-only, a late separate
default-parent edge could avoid the same-pair conflict. No such invariant is
proven here. Restoring just private late diagnostics would not solve the ordinary
sealed-provider case. The accepted binary is therefore left unchanged.

### Exact board log observations, when a window is separately authorized

The unchanged helper `../2026-10-02-n11h-host-owner/inputs/resident-compat.h`
provides these outcomes:

- Line39: `[U10-COMPAT-VISIBLE] owner_verified view=... resident_view=westlake.sealed.child abort=... getter=... gnu=... inheritance=caller_owned`:
  resident handle/symbol-address check succeeded **at that query time**, not app
  relocation or inherited visibility proof.
- Line10: `unavailable missing resident namespace; no loading fallback; namespace continues`.
- Line15: `unavailable unmapped resident compat; no loading fallback; namespace continues`.
- Line42: `unavailable result=<nonzero>; no loading fallback; namespace continues`:
  missing symbols/address mismatch. An existing handle alone is insufficient.
- Candidate source line273: `unavailable inherit result=<nonzero>; namespace continues`:
  optional default-parent edge failed, even if `owner_verified` was logged earlier.
- No marker on declared private/no-bridge paths: expected query skip, **not success**.
  Without independently establishing that branch, absent logs are unknown.

`knowledge/smoke/n11h-compat-readout.json` is an **offline diagnostic rule, not an
activation_smoke execution spec**. `compat_readout.py` requires the app's known
PID; optional TID narrows scope. Feed one spawn/attempt, not merged attempts.
Malformed/unscoped markers, contradictory outcomes and unexplained absence remain
unknown. Verified addresses must be nonzero. All outputs leave `smoke_verdict`,
`compat_success`, and `relocation_success` null. Diagnostic rc=0 means the readout
was collected, not that compat worked. Unavailability alone is neither a smoke
failure nor compat success. A later actual relocation/control/owner failure still
fails its independent gate.

The coordinator must **not copy U10.1's mandatory `owner_verified` marker** into
the final N11h smoke unchanged, and must not turn `verified|unavailable` into a
PASS regex. Read this diagnostic separately. Preserve final package fingerprints,
controls, required owner checks/inherit rc=0, load-base counts and screenshot
gates. The current master `knowledge/smoke/n11h.json` is a separate unfilled window
template; it was not changed or executed here. This work does not fill its identity
or authorize its conditional owner-open branch.

Example offline readout (diagnostic only):

```sh
python3 benchmark/2026-10-02-n11h-admission/compat_readout.py \
  --hilog "$ONE_ATTEMPT_HILOG" --pid "$APP_PID" --branch ordinary
```

## 2. Exact string proposals

`STRINGS-CHECKLIST.md` and `strings-allow.json` cover **3 dropped / 16 added**, each
once, each with a source-file SHA, source line, raw value SHA and unchecked outer
decision. Two drops are old absolute `__FILE__` identities; their displayed
`$REPO` spelling is redacted, but the hashes bind the actual ELF value. The third
drop is the private four-library table replaced by those same four plus bridge.
New diagnostic filenames come from the accepted `-ffile-prefix-map`, not new
search roots. Every owner/table/action/log string has an individual reason.

No allowance was applied. The original `deployed_strings_diff` evidence remains
rc=1 in `../2026-10-02-n11h-host-owner/evidence/strings.txt`; accepting the source
does not mean accepting these nineteen rows. No broad path-prefix waiver is offered.

## 3. Manifest-bound exception proposals

- `registry-delta.json`: **103 N2**, exact finding-body matches and deep-equal N2
  details against approved r3; all issue IDs recomputed for 37c48e2b/a825ba23.
- `n1-existing-registry-delta.json`: **53 existing N1**, separate optional old-row
  rebind. Matching ignores only nested `evidence.line` relocation, not text,
  function, namespace, source, target or flags. This avoids silently dropping
  the old N1 bindings while keeping the new query out of auto-identical.
- `outer-review.json`: **one new N1**, `N11hResidentHandle:29`, exact issue
  `8b28c4cccd67bf635710e51b554e20927edc74df6e66b8adfa4f83e0ab83d4da`.
  Pending outer review; **no `approved_by` or `approved_at` fields**.

Existing rows copy each parent's removal condition unchanged, including any
before-frozen-record re-review restriction. The two old resident-compat findings
are syntactically identical, but their caller timing changed as documented above;
semantic matching is **not** a waiver of that restriction or the timing review.
The proposed `auto-identical` metadata describes the outer rule, not a mutation of
the real registry. All proposal files explicitly remain pending outer adoption.

Evidence paths were checked as files, including the real
`benchmark/2026-10-02-u10-1-t8-rerun/approved-native-gate.json`.
The nonexistent `.../native-gate.json` from the old delta is **not reused**.
`evidence/exception-lineage.json` records all 156 parent/new pairings and simulation:

| Simulated proposal adoption | N1 rejected / excepted | N2 rejected / excepted |
|---|---|---|
| N2 only | 54 / 0 | 0 / 103 |
| N2 + separately matched existing N1 | 1 / 53 | 0 / 103 |

Thus the complete candidate still rejects pending new N1 review; no full gate
PASS is fabricated. Real registry bytes were not changed. Any final generation
manifest/input drift requires an exact rebind, not transplanting these IDs.

### Why the new query cannot mint an owner copy

The old r3 sealed/default compat NOLOAD probes are precedent, not the same finding.
The new helper takes its namespace from `dlns_get("westlake.sealed.child")`,
receives only the two canonical paths in `N11hCheckOwners`, and uses
`RTLD_NOW | RTLD_LOCAL | RTLD_NOLOAD` (6). Missing handles return NULL/ENOENT;
`StockOpenNamespace` canonical matching uses this same resident helper, rejects
protected aliases and never falls back to app/default for those owners. The three
lowered NOLOAD sites are `da24/db38/dba0`, not new owner fresh-load sites.
Other old private runtime fresh opens remain: this argument **does not prove
global single-copy** or board success. Those independent gates remain mandatory.

## Reproduction and handoff

```sh
python3 benchmark/2026-10-02-n11h-admission/timing.py
python3 benchmark/2026-10-02-n11h-admission/package.py
python3 benchmark/2026-10-02-n11h-admission/test_admission.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test n11h_admission
agent-spec lifecycle specs/n11h-admission/t1-compat.spec.md --code tools/spec-checks --format json
agent-spec lifecycle specs/n11h-admission/t2-reviews.spec.md --code tools/spec-checks --format json
python3 benchmark/2026-10-02-n11h-admission/finalize.py
python3 "$WORKSPACES/westlake-harness/scripts/lab/land.py" "$REPO" \
  benchmark/2026-10-02-n11h-admission/landing-paths.txt -m x --preflight
```

Python 19 tests and Rust 4 selectors pass with no skipped tests. Contracts are in
`specs/n11h-admission/`; their executable scenarios verify offline artifacts,
not visual/window acceptance. `results.json` records pending review boundaries.
`documentation.json` carries only additive Layout/DIGEST lines, not whole shared
documents. Outer may land the listed files, then review timings, nineteen string
checkboxes and the new N1 request. This handoff is not permission to open a board.

Raw cargo/lifecycle output is retained under `.artifacts/raw-outputs/`; public
evidence changes only exact repository/workspaces path prefixes. Hashes and this
transformation are recorded in `evidence/raw-outputs.json`. Re-running `finalize.py`
does not erase a retained raw receipt; use a separate fresh raw-output archive for
a new validation run.
