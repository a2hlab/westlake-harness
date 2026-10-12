# Restore v5: r3 low-fork audit, disabled 5cd derivative

The r2b ready-path diagnostic used six od calls and could consume the two-second
worker envelope. r3 removes only the ready-branch diagnostic and batches each
failure/pending diagnostic into one od call. This package integrates that frozen
helper and worker into the existing 5cd restoration binding. It does not claim
whole-worker timing, UI recovery or device acceptance.

Source: t0 commit `69e15c4ae058d1fe17ba5f4355883e460ac9859b`,
`benchmark/2026-10-12-child-readiness/r3-lowfork-audit/checkpoint-manifest.json`,
SHA `857e9704cf6ee3a98be3fa690fe6d9d830c32567275dea12f65f09120d5f229d`.
All 17 checkpoint files were checked against the Git-pinned manifest. Helper SHA
is `6bce7c3c8f84ad1047313c5dd76bcb084637d9095b9163dc710c88aaee12fe4c`;
worker SHA is `2d3ce1546c9df1e3a222e23f19c39f8f4aec82fb551d59f37dbe7fd343573717`.
Watchdog and launch remain unchanged. Frozen v4 is not modified.

## Narrow compiler change

The v4 guardian update admitted only the r2b helper. v5 additionally recognizes
`lowfork-audit-checkpoint/v1` and imports exactly helper and worker content.
Every checkpoint file is still checked; watchdog and launch must match the
measured control source. The existing entry/member/startup hash-chain compilation
uses those new bytes. No r3 candidate startup template is copied into the package.
`invoke` and `new_executor` remain AST-identical to v4; the generated executor is
byte-identical. Exact-seal checks, typed pins and rollback behavior are unchanged.

`build_binding.py` starts from the frozen v4 disabled 5cd binding and replaces only
the guardian source pin/provenance. All 487 target before/after records and every
directory declaration remain unchanged. The worker's absent before image still
comes from the measured absent **5cd** candidate ancestor, not the present61b
worker or the c30 composition. No 61b authorization or lock is imported.

The output has 24 control targets, 460 runtime targets and 3 stage targets;
13 boot members, 22 new directories and 6 existing-directory guards. Eight target
SHAs differ from v4: helper at three destinations, worker, entry, members,
startup.env and startup.expected.sha256. Metadata is unchanged for every target.

`evidence/startup-comparison.json` records the actual main-tree r3-package startup,
the frozen t0 template and the independently derived 5cd startup. The comparison
is read-only. Target serial, UID20011300, runtime/request SHA fields and disabled
policy derive from the existing 5cd binding. The 61b actual values and the template
are not interchangeable; neither supplies target preimages or execution authority.

## Limited validation and handoff

The final local compile is `package-r3-disabled`, manifest SHA
`0c5da8dadaec9e6fc4969d06f884b6204ce5601297f18f76b25fc0407f0d8ab5`.
Its plan SHA is `d1c1acbbdca508b86e9f35036b66135e629eca3953a60584cf4e7b736d8864eb`.
All manifest bytes and the 487-target hash mapping are verified. Review details
are in `evidence/package-and-delta-check.json` and `results.json`.

Only the actual-binding pin and r3 delta suite is run in this revision. The v4
full transaction/failure matrix remains the inherited evidence, with unchanged
transaction code; it is not rerun or represented as new v5 execution evidence.
Local helper/branch tests do not construct a production lock/owner or emulate the
c30 live guardian context. The missing c30 lock cannot authorize a worker run.

Zero encoding applies to the already-ready success branch. A transition through
root pending may still emit diagnostics before later success; each diagnostic
uses one od. No assertion of zero forks or a complete two-second bound follows.

Both deployment and startup remain disabled with approval PENDING. No board,
remote, install, signal, reboot, seal signing or authorization operation occurred.
User cross-board acceptance and outer/BMS admission remain pending. This freeze
is reviewable source/package evidence, not a signed seal or permission to execute.

Use `--compile --binding binding.5cd.r3.disabled.json --out <new-directory>` for a
new local reproduction. Keep this package and all earlier freezes unchanged.
Large payloads are transitively pinned and stay local; `landing-paths.txt` lists
small handoff files. Inputs remain in the recorded WORKSPACES/CAS locations.
