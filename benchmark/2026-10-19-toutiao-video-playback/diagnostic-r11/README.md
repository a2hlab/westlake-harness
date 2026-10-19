# R11 bounded call observer

This is a diagnostic, not a playback fix. Outer owns the exclusive board lock,
exact SDK server, serial-qualified forwarding and recovery. No device invocation
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
python3 diagnostic-r11/observe.py --admission "$ADMISSION" --port 5039 --out "$PREVIEW"
python3 diagnostic-r11/observe.py --admission "$ADMISSION" --port 5039 --out "$RUN" --execute
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
