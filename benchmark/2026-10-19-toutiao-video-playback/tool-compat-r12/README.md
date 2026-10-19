# R12 dedicated debugger compatibility probe

R11 SDK15 server asserted during initial handshake, before any target call or
breakpoint. This package validates a different existing server on a new owned
probe only. It does not attach Toutiao or change R11 pins. All device actions
belong to the outer operator on **5cd1e3dd00000000000000000923012c**, under a fresh
exclusive lock and a 15-minute window. This lane performed only local build/tests.

## Built input

`payload/probe` is the actual OH AArch64 PIE built from `probe.c`, SHA
`8ab9acaff7c92098f764aa602272e51aeab5b4935af9ef42875c578b874e6c3c`.
The noinline marker is ELF `0x1af0`, verified against its symbol and current maps.
It prints an increasing count every 250 ms and self-exits at 120 seconds. It uses
the normal OH libc loader; it is not an Android runtime/app experiment.
`build-public.json` binds source/recipe/tools and every original raw log; exact
originals remain in `.private/build-01/` (persistent, not /tmp). The binary was
not executed here. `build_probe.py --sdk "$OH_NATIVE" --source-repo "$MAIN" --out
"$FRESH_PERSISTENT_OUT" --run` reproduces the build command and writes raw receipts.
Different compiler/source paths can change debug bytes; admission always requires
the published payload SHA, not a silently rebuilt replacement.

Server: existing NDK r23b static AArch64 file:
`$HOME/Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/lib64/clang/12.0.8/lib/linux/aarch64/lldb-server`,
SHA `13c0b4bfcb0b8b83cd9d73df2be0ebffcb1cc5fea2eb420cb7b2f5629254a06a`.
No PT_INTERP/DT_NEEDED; this is static evidence, not OH compatibility proof.
Host is SDK15 c6008509, exact path in the disabled admission template.

## Outer sequence and admission

1. Hold the board lock. Pick new root
   `/data/local/tmp/wl-debug-compat-<boot-first8>-<random-8-to32-lower-alnum>`.
   Execute `preflight.sh ROOT` through serial-qualified HDC and save original
   stdout/rc. It is read-only: boot bookends, kernel, SELinux, root absence,
   preexisting PID inventory and TCP/TCP6. Port 5039 must have no listener.
2. Outer stages only the exact probe/server in that new root and preserves their
   actual modes/inodes. Start probe **with no arguments**, stdout to
   `ROOT/probe.stdout`. Start exact server argv:
   `ROOT/lldb-server gdbserver 127.0.0.1:5039 --attach PROBE_PID`.
   Record the actual launch output, never fabricate prior records. Its binding
   lines must each occur once: `R12_OWNED_ROOT ROOT`, `R12_BOOT BOOT`,
   `R12_PROBE_PID PID`, `R12_SERVER_PID PID` (expand actual values).
   Capture raw launch commands, return codes, server version/help and streams.
3. Outer owns a fresh serial-specific 5039 forwarding and verifies it is only this
   mapping. Populate `admission.disabled.json` in a separate fresh file, set true
   only under outer authorization, with exact held entire line, boot, kernel,
   SELinux, new PID/birth/UID, executable dev/inode, local tool SHA and pinned
   preflight/launch stdout. `created_at`/`expires_at` are epoch seconds; maximum
   admission age180s/window900s. Start promptly so the 120s self-exit does not
   consume the observation budget before attach.
4. Run the published script (all output directories must be fresh):

```sh
python3 "$R12/observe.py" --admission "$ADMISSION" --out "$VALIDATE" --validate-only
python3 "$R12/observe.py" --admission "$ADMISSION" --out "$RUN" --execute
```

Default invocation refuses with zero device calls. Validate-only is local and
cannot prove current remote identity. Runtime independently checks cmdline through
raw `od` bytes, boot/birth/UID/exeSHA/inode, lock, new-root scope, and the pre-connect
loopback listener inode in the admitted server's fd list. Child TracerPid must
already equal that server PID. No existing PID from preflight is accepted.

## Observation and cleanup

Explicit remote-ohos, hardware-only and disabled memory cache precede connection.
One hardware breakpoint is created at actual ELF/maps-derived marker. Two
Continue calls must each yield a new StopID and exact PC/hardware ID. Same TID
and increasing x0 are required. 60 seconds is fixed; JSON cannot increase it.

Finally deletes only its breakpoint, explicitly detaches with keep-stopped false,
then independently verifies TracerPid0/non-stopped state and reads counter twice
600ms apart to prove forward progress. Connection failure still leaves FAILED
and requires outer cleanup; self-exit is never substitute evidence. The observer
never issues kill, deploy, reboot or fport commands. On uncertain detach, outer
must freshly verify boot/PID/birth/exeSHA/cmdline before terminating **only** its
own server/probe and record failure, then remove only its own forwarding. Existing
applications/parents and system/runtime/config are untouched. Retain all files.

RC0 means two probe hits plus independently verified detach/progress; final status
remains `PROBE_COMPATIBILITY_ONLY_PENDING_OUTER_FORWARD_CLEANUP`. Outer must bind
actual forwarding removal and process cleanup before signing tool compatibility.
Missing handshake, hits, cleanup or receipts is failed/unknown. Toutiao remains
unknown and needs a separately reviewed successor before using this server.
