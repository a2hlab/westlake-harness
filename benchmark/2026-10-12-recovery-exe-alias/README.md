# Exact Route B executable alias repair

The original three guards rejected the actually deployed executable path before
checking its otherwise valid identity. The captured parent5153 uses
`/data/local/tmp/asx/appspawn-x`, not the renamed `asx-spawner` path. Its captured
SHA is a7a358c6…, four root UIDs, birth15134, private mnt4026533005 versus
init4026531841, and matching run.sh inode66352:423788. The old run.sh source
at preimages-1915/target-08.preimage:42 already executes that exact path.

Only the three exact absolute-path case lists change. They accept the original
asx-spawner and the proven appspawn-x alias, with the existing deleted-exe form.
`/system/bin/appspawn-x` and `/tmp/appspawn-x` still reject. No basename/comm
matching, SHA/UID/birth/inode/namespace removal, signal or restart is added.
The helper remains child-UID-only; parent acceptance remains read-only. Its
namespace check belongs to the effective watchdog child_owned caller, not to
rb_owned alone. The tests exercise this exact call chain.

The independent candidates are launch-common.sh, watchdog.sh and
route-b-owner.sh. entry.sh has both new hard-coded digests. members.tsv is
rebuilt against the actual candidates and unchanged b093 members; startup.env
pins that new manifest, startup.expected.sha256 pins the new config. This
startup template remains PENDING/disabled. Applying it directly as an approved
live policy would be wrong. Outer must preserve the signed per-board live
policy values, change only its manifest pin, recompute its expected digest,
and bind the whole composed plan/new attempt to a fresh authorization. The
new attempt must retain historical stop/data objects; this package does not
clear them, launch a process, or repair the current failed attempt.

Six Python methods cover captured-field replay of both real and legacy paths,
parent/child roles and SHA/UID/birth/namespace/inode/path negative cases,
byte-exact one-line deltas and complete entry/member/startup bindings. They
execute the actual candidate shell functions in isolated local fixtures.
Readlink/SHA/stat responses replay explicitly captured proc fields; this is
not a new native/hardware executable observation. kill is intercepted and
any signal attempt is a failure. Raw output is in evidence/tests.*. Rust
selectors identity/reject/bindings run those new tests only. R1's already
accepted full suite is not rerun. Original976/80 and9436 remain unchanged.

The restore adapter draft is paused, uncommitted and outside this release.
No board/VM/remote/write/signature operation is part of this handoff.
