# G21 bounded paired-loader trial

Original U7 preflight in OrbStack returned rc0, `gates_passed=true` and
`deployable=true` for bundle `7eca21993f23dd6e1f5fbbe582ca9a905928e2d091c02a1cd742ae1d3864521c`.
This is **preflight evidence only**. Device activation and game results require
their own actual journal, logs and screenshots.

The exact G20 assembly-02 was cloned into persistent `g21-rollout-01`; its only
semantic bundle change is the outer-approved `rollout_ready: false → true`.
The source assemblies remain unchanged. G22 fixes U7's missing start context,
preserving the original label recipe and service-start implementation. Its
candidate and recovery manifests are selected explicitly, even with identical
host executable hashes.

`preflight-05-summary.json` records 319 baseline/expected targets, 32 planned
binds (30 same-SHA), a verified paired build receipt, G1/G2 PASS and both native
gate PASS results under the explicit current exceptions. G2 compares 36
instructions on each side. Original complete output, including the two large
oatdump streams, is retained under the indexed persistent private roots.

The real VM required its existing clang-15 and Android build-tools directories
on PATH. Its SSH configuration does not resolve `hw248`, so
`oatdump-via-mac.sh` forwards to the unchanged Mac `oatdump_remote.sh`.
OrbStack automatically translates absolute paths in arguments: passing the
remote LAB_HOME as an argv assignment rewrote it into a local OrbStack path.
The documented `ORBENV=LAB_HOME` mechanism preserves the value; an actual
before/after SHA comparison passed. G2 scratch must be under a Mac/VM shared
directory so the Mac sees the original temporary images. The adapter records
original probe argv/stdout/stderr/rc and preserves their output and exit status.
No gate or runtime policy was relaxed.

Earlier attempts remain intact: preflight-01 lacked LLVM on PATH;
preflight-02 failed before executing the gate because the launcher used runpy
without the script import path; preflight-03 produced empty disassembly;
preflight-04 retained the decisive rc127 oatdump wrong-prefix errors.
The successful attempt is separately numbered 05.

`prelock-02-summary.json` binds the original system configuration, root parent
6274/birth245324, unchanged boot, and four BMS control/game identities. No live
direct child or control/game UID process was observed in those reads. These
are preparation observations; the actual transaction must recheck identity
under its board lock. The G21 contract requires same-window rollback and
restoration, with no permanent-retain decision.
