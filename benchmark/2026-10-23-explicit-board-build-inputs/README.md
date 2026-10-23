# T118 — explicit pinned board configuration inputs

The wrapper previously changed serial while inheriting61b startup bindings and omitted nondefault arguments from its replay command. This change adds an explicit configuration path/SHA pair and complete shell-quoted argv/cwd recording. It does not change a runtime implementation, produce a real package or authorize deployment.

## Change

- New pair: `--startup-template FILE --startup-template-sha256 SHA256`. Either missing, malformed SHA or byte mismatch rejects before payload creation. The original default template path and SHA551169f5… remain intact.
- Explicit input is parsed as data, never sourced: required unique keys, conservative quoted field syntax, SHA fields, serial equality and OLD_STOP_SHA=NONE or a complete hash. Unknown JIT/request or malformed bindings reject. No dynamic shell text is evaluated.
- STARTUP_START_PARENT_SHA must equal the **actual packaged** real-start-parent-bounded.sh hash. T116's current5cd fc044… is not a substitute for a package containing f77f… . Mismatch rejects before generation.json.
- Actual argv is recorded in build-command.txt with every argument, including serial/root/UID/service/template/SHA; build-cwd.txt and startup-template-path.txt preserve its context. Paths containing spaces and apostrophes round-trip in tests.
- `--owner-uid` remains metadata only and is explicitly labeled as such. Source inputs and default pin checks remain in the original wrapper.
- External hashes being syntactically valid is not independent dependency attestation. Explicit-board output remains disabled; explicit `--enable` rejects, generation marks `deployable=false` and external bindings unverified. This is an offline package qualification limit, **not a request for new user authorization**. Outer still reviews the concrete package and actual dependency bindings before its separately dispatched window. The default template's prior enabled/approved behavior is retained, with the added non-deployability qualification.

## Actual tests and retained failures

Production wrapper logic runs against an isolated synthetic tree. Every payload is inert generated text; no controller or stopped implementation is imported, extracted or executed. Only fixture SHA literals are replaced with hashes of those synthetic files; production pins are not weakened. Substitution maps are retained.

- fixture-01:12/13. Explicit positive failed because the allowed data alphabet omitted parentheses in historical `outer(codex)`.
- fixture-02: test process failed while decoding the recorded command: apostrophe quoting was invalid. Raw output retained; not reported as a pass.
- fixture-03:13/13 after both corrections.
- fixture-04 (before independent peer review):**14/14**: default, explicit, missing pair×2, wrong SHA, wrong packaged parent, unknown JIT, unknown old-stop, missing/duplicate field, shell text, serial mismatch, explicit enable, default template drift.

Final shell syntax check passed. No real runtime build, actual package generation, device/remote/REA operation or stopped-flow retry occurred. Other worktree changes were retained.

## T116 binding

`target-bindings.json` pins the finalized T116 index and records its5cd boot/root/init/config fields. Those are expected configuration values, not a fresh attestation of all external JIT/request bytes. This card does not create a target template by mechanically copying the old parent hash. Remaining work is concrete package input qualification by outer, not new user permission.

## Replay with persistent receipts

From this worktree root, choose a new persistent output directory (existing output is rejected):

```sh
T118_REPLAY="$HOME/.local/share/westlake/t118-fixture-replay-$(date +%Y%m%dT%H%M%S)"
python3 benchmark/2026-10-23-explicit-board-build-inputs/test_fixture.py --out "$T118_REPLAY"
```

The fixture itself uses an isolated temporary synthetic tree and retains every executed case's argv/start/end/rc/stdout/stderr plus results under that persistent output. Four original runs remain under this card's `.private/`, indexed by raw-index.json; public results binds the final wrapper SHA. Public evidence does not copy private argv or raw stderr.

The exact main preimage SHA is in baseline.json; builder.patch is against that preimage. Landing includes only this wrapper and card deliverables. Shared Git refs were previously refused; no repeated Git write, author_commit=null, no push.

## Peer pass01 correction (frozen revision)

The peer found actual accepted-input corruption: ampersands in root/service/serial changed sed output, while quotes in service/UID produced invalid generation JSON with rc0. This was a real wrapper defect, not a fixture issue. Original peer pass01 is unchanged and its results SHA is recorded in peer-rerun-request.json.

Identity fields now reject before any output directory creation: serial is exactly61b or5cd from this package's supported board whitelist; UID is nonempty decimal digits; service starts with an ASCII letter/underscore and contains only letters/digits/underscore/dot/hyphen; root uses the original fixed prefix, safe path characters, a nonempty suffix and no dot/traversal/double-slash components. OUT/template paths remain unrestricted by these identifier rules and retain the positive space/apostrophe test.

fixture-05:22/22, including all prior14 plus the6 reported identifier defects, path traversal and negative UID. The source is now frozen for the existing peer's full24-case rerun; no peer PASS is claimed here.
