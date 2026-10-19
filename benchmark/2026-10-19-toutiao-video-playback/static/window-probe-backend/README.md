# Existing LLDB backend: concrete handoff

The installed DevEco SDK supplies a matching host LLDB15 and statically linked AArch64 OH server. Their exact hashes are in results.json. The host was started locally with --no-lldbinit, and actual help confirms gdb-remote, hardware breakpoints, detach and target.require-hardware-breakpoint. No board attach has been attempted, and no successful historical 61b attach/hardware-stop receipt was found in the stated bounded search.

Do not run the SDK lldb_python.py helper: it automatically writes/starts through unqualified hdc. The copied r10 server is a different build from this SDK server. Use the selected exact pair, not the PATH Homebrew LLDB22.

## Outer/CC command sequence (NOT executed; t6 must supply identities)

After outer validates serial, boot, child PID/birth/UID/PPID/exe, parent identity, TracerPid=0 and server identity, use only the approved diagnostic child. The server must already have been installed through the outer-authorized staging step. Check its gdbserver help before accepting this invocation; no device CLI syntax was tested here:

```sh
# target-side, launched only through outer serial-qualified guarded command
"$REMOTE_LLDB_SERVER" gdbserver 127.0.0.1:5039 --attach "$VERIFIED_CHILD_PID"
# host-side serial-qualified forwarding; only the created forward may be removed
"$HDC" -t "$SERIAL" fport tcp:5039 tcp:5039
"$OH_LLDB" --no-lldbinit
```

In the SDK host LLDB, before connection:

```text
settings set target.require-hardware-breakpoint true
gdb-remote 127.0.0.1:5039
process status
register read pc x0 x1 x2 x30 sp
```

CC supplies exact dynamically relocated addresses and thread/call correlation from the previous observation plan. Use `breakpoint set --hardware --address <validated-runtime-address>`; never ordinary software breakpoints, step-out implicit temporary software traps, expression evaluation calling target functions, or new target-side dlsym. Actual stop context and hardware allocation must be checked. A local setting does not prove that the remote kernel accepts hardware slots or that every internal loader breakpoint succeeds.

Exit on completion/error/deadline: remove only this session's breakpoint IDs, `process detach --keep-stopped false`, then independently verify the same surviving child is no longer traced/stopped and the original parent identity is intact. Never use process kill or kill a parent. Transport loss/timeout requires an independent cleanup owner that retains the server PID and child identity; do not kill the server before successful detach and assume the child resumed. No stale PID may be signalled after a birth mismatch. Fail cleanup explicitly instead of silently releasing the board lock.

This is a usable installed backend candidate, not an attach or OH kernel compatibility PASS. CC's bounded t6 implementation must close those runtime and cleanup conditions. Source/header presence alone is not evidence that a custom ptrace implementation is ready.
