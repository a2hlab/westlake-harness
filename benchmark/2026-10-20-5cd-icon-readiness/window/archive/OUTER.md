# Raw archive handoff

The full archive is locally verified. The lane SSH attempt stopped at rc255 before upload; its original command/stdout/stderr/rc remain under `.private/archive-01/`. No remote success is claimed.

Outer should execute the three argv arrays in `.private/archive-01/remote-commands.private.json` in order, stopping on any nonzero rc. Persist each command and its stdout/stderr/rc in a new output directory. Compare remote SHA and size to `receipt.json`. Add a separate success receipt; never overwrite the failed lane record or rebuild this archive.

The private package is `window/.private/archive-01/window.tar.gz`. Public `members.json` binds all raw bytes, including failed attempts, old before-only producer, current collector, both UI scripts, BMS implementation, facts helper, and the packaging source. `archive/members.json` is the additional archive member.
