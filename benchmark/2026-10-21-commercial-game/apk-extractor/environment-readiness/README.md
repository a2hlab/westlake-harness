# G10: stopped control plane, build inputs preserved

The previous inference to avoid is “three run timeouts mean the entire VM is
dead.” G09 actually recorded two fast `orb status` responses of `Stopped` (rc 1).
G10's fresh `orbctl status` returned the same result in 0.0073 seconds.
Installed CLI help defines this as **OrbStack-wide** state, not the state of
the individual `a2hlab` machine. The underlying cause and machine state remain
unknown. This is neither the RUNBOOK's both-commands-time-out case nor its
Running/self-healing case.

Five current CLI calls (four help calls and one status query) used a 15-second
subprocess deadline and retained argv, cwd, start/end, rc and both streams.
No Linux run was repeated while stopped. `evidence.json` contains sanitized
readable evidence and hashes of the original files in ignored `.private/`.
The original G09 SSH and process-query refusals were read and preserved;
neither operation was retried through another channel.

## Handoff to outer and cx-seal

The exact **outer-only**, not executed, startup command is:

```sh
orbctl start a2hlab
```

Installed `start --help` says a named machine is targeted. Bare `orbctl start`
would restore all previously running machines; do not substitute it. Starting
changes shared runtime state and belongs to the outer lane. No quit, restart,
kill, mount or permission operation is needed or authorized by this report.

After startup, outer should run `orbctl status`, then the following exact argv
through a 15-second wrapper that retains both streams and timestamps:

```text
["orbctl", "run", "-m", "a2hlab", "-w", "/", "true"]
```

On refusal or timeout, preserve the result and stop. A successful `true` proves
only command transport. Before cx resumes its single build, check Linux x86_64,
Python, `/usr/bin/ccache`, native tar, the pinned clang executable and its
libraries, Mac input visibility, and a new scratch/log destination. Do not run
the native build from this environment lane.

The existing G09 entry is
`$WORKSPACES/westlake-harness-t4/benchmark/2026-10-21-commercial-game/apk-extractor/native-build/build_native.py`.
Its adjacent `.private/exact-launch.argv.json` is data for cx/outer, not an
instruction executed here. Recheck its scratch/log names are unused and frozen
receipt is fresh before any future execution. It maps Mac inputs through
`/mnt/mac`; that mapping is not currently verified from Linux.

## Inputs and fallback

Seven local files were freshly hashed: **7/7 match** G09's pins, including the
478,511,698-byte archive `61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6`
and clang `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913`.
Exact paths, byte counts and complete hashes are in `local-inputs.json`.
Hashing an existing compiler on Mac does not establish Linux executability.

The older build-preflight raw receipt records hw248 x86_64, Python 3.10.12,
`/usr/bin/ccache`, and a same-size archive under
`$HW248_LAB_HOME/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/`.
Its remote archive SHA was not checked. G09's later SSH attempt was refused.
Current remote reachability, exact archive SHA and compiler SHA remain unknown;
hw248 is a **conditional fallback**, not a verified available environment.

Old `build.py` extraction incompatibility does not establish that Linux clang
or native tar cannot run there. Current G09 `build_native.py` uses `tar -xzf`
and no Python 3.12-only extraction API. If outer uses its authorized remote
channel, it must first verify the exact archive and extracted compiler pins,
Python/native dependencies, accepted G08 source/patch, original APK hash and
fresh frozen receipt. Use a new scratch tree and persistent raw build logs;
do not copy large assets or substitute another SDK for this investigation.
Baseline object `2e2a6247…` and library `51e1b525…` equality remain G09 gates;
build-directory debug metadata is still an unresolved reproducibility risk.

## Validation and scope

Contract at `47bdf7c706`: parse 5 sections / 3 scenarios; lint 100%.
The report validator checks actual evidence, unknowns, and input pins. Its Rust
selector is supplied for outer verification. No Cargo test was run because this
turn explicitly prohibits compilation; full lifecycle acceptance is pending.
This report does not claim a native build, deployment or working build channel.

Knowledge handoff (not written outside the card): `orbctl status` is global;
Stopped rc 1 plus bounded run timeouts does not prove a dead machine. Query help
before assigning status semantics. See RUNBOOK lines 49/50/184 and DIGEST's
existing frozen-clang/VM finding. No shared knowledge files were modified.
