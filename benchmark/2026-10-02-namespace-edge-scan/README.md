# Namespace-edge scanner: deployed-byte known answers

## What was missing

The original scanner enumerated library-open sites but did not list namespace
creation, configuration, lookup or inheritance. Numeric PC order alone would
wrongly mark U9's `0xccd8` and `0xccf0` as inheritance after an open. Conversely,
matching raw register expressions misses the real U10 r2 repeated inheritance:
the same child and named parent are passed through two different functions.

This extension preserves the seven existing tests and adds twelve tests. The
19 Python cases and four Rust selectors pass, with no skips in this replay.
It changes no native binary, generation, U10.1/T8 package or device.

## Pinned results

| Input | Full identity in results.json | Open sites | Namespace edges | INHERIT-REPEAT |
| --- | --- | --- | --- | --- |
| Signed U9 host | `1d3b08816969` | 6 | 14 | 0 |
| U10 actually activated r2 host | `71901abc64e2` | 8 | 17 direct + 1 projected | 1 |
| Accepted r3 host | `65cc3535ebf2` | 8 | 17 | 0 |
| Next-round comparison host | `67753f770088` | 8 | 17 | 0 |

The r2 input is the explicit U10 v3 bundle selected by activation-smoke and
outer ACK(90) 11:40:39, not the unactivated `d51d8d6a` comparison. The r3 input
is the persistent U10.1 bundle, not a recreated source-shaped baseline. Every
known input is hash-checked before scanning; the four outputs and JSON records
are in `evidence/`. The spill comparison still lives in the lane's retained
artifact directory, identified by its full SHA; no binary is copied into git.

### r2 overwrite proof

The first edge at `StockCreateConfiguredNamespaces@0xd008` shares
`liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so` from the named
`westlake.sealed.child` parent. A syntactically reachable later direct call at
`0xcf80` reaches `U10ShareResidentCompat@0xd694`, whose shared table is only
`libbionic_compat.so`. Normalizing both parent handles by `dlns_get` names and
substituting the helper's child parameter with its caller argument identifies
the same child/parent pair. OH inheritance replaces this edge's whitelist;
the differing shared tables are retained verbatim in the finding.

The later executed site has a lower PC. Hence repeat detection also requires
a CFG path, rather than sorting by PC or globally counting same-looking calls.
The accepted r3 contains no corresponding helper inherit and reports no repeat.

### U9 control-flow negative and positive controls

All required PCs are asserted: init `0xcacc/0xcb7c`, create2 `0xcadc/0xcb8c`,
inherit `0xcc64/0xccd8/0xccf0`, get `0xccac/0xccc0`. Get names resolve to
`default` and `westlake.sealed.child`; configuration calls are listed as well.

The ABI open `0xcc90` is numerically before inherit `0xccd8/0xccf0`, but its
success and failure branches terminate without reaching either inherit. The
edges retain `pc_before_inherit=true, reachable=false`; no AFTER-OPEN finding
is emitted for those two PCs. Runtime/OpenSLES opens `0xcd70/0xce10` *can* reach
the original bridge inherit `0xcc64` via a backward branch and produce two
may-path AFTER-OPEN findings. r3 and comparison677 each retain four may-path
AFTER-OPEN findings. These are not repeat findings or proof of a new regression;
the extension does not suppress them to manufacture a clean result.

The mixed-register spill before comparison677's open `0xcf0c` now resolves to
`stack:frame slot [sp, #24]`, not `unknown:ldp ...`. Paired loads retain the
second slot's +8 offset. Existing epilogue-skip behavior remains tested.

## Interface and limits

- `scan()` still returns `(sites, elf)`. Existing site fields remain unchanged
  except the requested spill resolution. Namespace records and findings are
  attached to that ELF; `findings()` appends the new finding kinds.
- Text includes a `== namespace edges` section. Each JSON binary has additive
  `namespace_edges`, with raw namespace expressions, normalized identities,
  literal names/shared tables, configuration values and tail-call flags.
- Named handles normalize by `dlns_init/get`; dynamic names retain scoped
  expression identities. Unknown/clobbered expressions do not become names.
- Projected inherits have `projected=true` and `via_call` with callee, actual
  inherit PC and depth1. Only direct function-entry calls/tails are expanded;
  internal `Function+offset` branches and unreachable helper bodies are not
  calls. Caller expansion is not recursive or indirect-call analysis.
- CFG includes conditional/unconditional branches, backward edges, returns,
  and direct tail exits. TBZ/TBNZ target parsing uses the final operand, not
  their hexadecimal bit-index immediate. Indirect branches terminate static
  traversal; branch values and failure returns are not symbolically executed.
- Reachability is a **syntactic may-path** within a function, not a dynamic
  ownership proof. Register resolution remains the existing linear backward
  analysis. Unresolved pointers, memory aliases and indirect calls still need
  review. No inheritance is auto-approved and no exception table changes.
- Default listing exit0 is not a safety PASS. `--strict` retains its existing
  confirmed owner MULTI-NS meaning; callers must inspect the new findings too.

## Replay and verification

Run `python3 benchmark/2026-10-02-namespace-edge-scan/replay.py`, then
`python3 -m unittest discover -s scripts/lab/tests -p test_open_site_scan.py -v`.
The Rust bridge is `tools/spec-checks/tests/namespace_edge_scan.rs`; the task
contract is `specs/namespace-edge-scan/t1-edges.spec.md` (lint100%). Its four
selectors run the real Python groups; lifecycle must report four passes.

`results.json` pins inputs, scanner/tests, commands and raw/display hashes.
Public evidence substitutes workspace prefixes only; unfiltered stdout/stderr
remain in `.artifacts/raw/` and are appended verbatim to the canonical board.
`landing-paths.txt` contains only this tool handoff plus its spec/tests. Shared
README/DIGEST changes are additive `documentation.json`, not whole-file copies.
The final preflight and validation logs are separate receipts. No full-tree
regression or namespace/deployment admission is claimed.
