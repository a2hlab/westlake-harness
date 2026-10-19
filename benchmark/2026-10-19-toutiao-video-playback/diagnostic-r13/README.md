# R13 bounded call observer

This is a diagnostic, not a playback fix. Outer owns the exclusive board lock,
exact NDK r23b server, serial-qualified forwarding and recovery. No device invocation
has been made by this implementation lane. Actual attach/hardware support remains
unknown until outer execution.

## Minimal execution

Fill `admission.disabled.example.json` with fresh independently read identities,
full held line, private-view metadata and local exact ELF inputs. The parent UID
is **0**, child UID **20011206**, both executable bytes are pinned to a7a358c6.
The supplied example cannot execute. Set `execution_enabled=true` only in the
outer-authorized fresh admission. `created_at` / `expires_at` are epoch seconds;
admission must be at most 300 seconds old and expire within 30 minutes.

```sh
python3 diagnostic-r13/observe.py --admission "$ADMISSION" --port 5039 --out "$PREVIEW"
python3 diagnostic-r13/observe.py --admission "$ADMISSION" --port 5039 --out "$RUN" --execute
```

Use the real repository-relative script path; each output directory must be new.
Port is a preexisting outer-controlled localhost forwarding endpoint, never a
remote hostname. Before connecting, runtime checks the held line, boot, exact
server PID/birth/UID/SHA, parent/child UID/birth/PPID/exeSHA, all five module full
SHA/private inode/maps. Actual player GOT chooses the provider instances.

LLDB explicitly selects `remote-ohos`, requires hardware breakpoints and requests
`--hardware` for every breakpoint. Unsupported allocation stops; no software
fallback, stepping, expression evaluation or target call is used. Resume must
advance GetStopID before a stop can be consumed. Raw x0/x2/x30 are persisted before
classification. Nonplayer callers are recorded and ignored, with a hard total
limit of 16 and the same 120-second deadline. Return association requires exact
TID/SP/PC; overlapping target fromSurface calls stop as unsupported.

At most four target fromSurface calls and four lock calls are recorded. Object
read failure/magic mismatch is unknown, not raw-OH classification. An unadmitted
winner is recorded with raw address and then stops the observer. Cross-event
object generation is always unknown. No observer result is playback PASS.

## Exit and recovery

Finally deletes only owned breakpoint IDs, uses SDK15 CLI
`process detach --keep-stopped false`, then independently verifies original
parent/child identity, TracerPid=0 and non-stopped state. Python SDK15 `Detach`
has no boolean overload. Cleanup failure requires outer recovery under the same
lock. The launcher grants 120 seconds observation plus bounded host cleanup;
a local-client timeout is always outer-recovery-required. It never kills the
parent/child/server. Outer removes only its own forwarding/server, or performs
the approved baseline recovery boot when detach cannot be verified.

RC 0 means event budget complete with verified cleanup, not video success.
RC 2 includes incomplete/refused observations and cleanup failures: inspect
`result.json`, `host.rc.json`, raw commands and identity evidence. A deadline
with fewer events is incomplete evidence, not proof of absence.

## Offline checks

`python3 test_observer.py -v` exercises actual admission, Guard collection parser,
return pairing, object reads, Session stop-ID handling, hardware rejection,
nonplayer filtering, unknown-winner persistence, cleanup and zero-call CLI refusal.
The Rust selectors only invoke these offline classes. No JSON self-declaration is
accepted in lieu of the runtime checks. Fresh admission/actual observations and
outer recovery remain separately reviewed device evidence.

## Successor scope and outer-owned staging

R11 remains unchanged. The five executable Python files differ only in the R13
version/receipt labels and the exact NDK server SHA. Object selection, hardware,
StopID, return pairing, budgets and cleanup are unchanged.

Outer must use a fresh owned directory `/data/local/tmp/r13-lldb-<boot8>-<tag>`
for `lldb-server`; never reuse or clean an R11/R12 directory. This prefix is an
outer staging/cleanup requirement, not a new device-mutation capability in the
observer. As in R11, the observer checks the actual server PID/birth/UID/exe SHA;
outer additionally pins its exact executable path, command line, port and unique
forward before generating admission. Pre-connect TracerPid must equal that server
PID; after detach it must be zero. No observer-created server or forwarding.

Client is the existing SDK15 LLDB (c6008509…); server is NDK r23b's static aarch64
`lldb-server` (13c0b4bf…). See the exact pins in core.py and the disabled template.
R12 proves two hardware stops and continuing detach on the owned probe only.
Business attach and window-object observations remain UNKNOWN until actual R13.
The tool path may be obtained from
`$HOME/Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/lib64/clang/12.0.8/lib/linux/aarch64/lldb-server`.
Outer starts rollback by 20 minutes and closes the entire window within 30 minutes;
120 seconds is the observer budget, not an extension of that window.
