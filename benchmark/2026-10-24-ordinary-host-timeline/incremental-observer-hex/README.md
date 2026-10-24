# Ordinary increments: ASCII-hex transport revision

**Offline-tested; no device execution.** V1 was accepted before an actual HDC transport limitation was discovered. The outer observed plain cmdline capture lose NUL; its independent `/bin/od -An -tx1` output shows the terminating00. V1's raw binary frames therefore cannot be assumed valid on that channel. V1 source, manifest, validation and test originals are unchanged; `v1-reference.json` pins them.

Only transport changes: child cmdline's exact first-name-plus-NUL prefix and both log increments are read using `/bin/od -An -v -tx1 -j OFFSET -N COUNT`. `-v` prevents repeated-line `*` compression. Zero count emits empty hex without invoking od. Binary never enters a shell variable or the HDC stdout stream. ASCII frames carry an explicit decoded-byte count and ASCII body length. Local parsing rejects non-ASCII/NUL wire data, legacy transport, unknown/duplicate fields, malformed tokens, `*`, short data or length mismatch. Offset/identity/partial-birth rules are inherited unchanged. No request timing is inferred from log visibility.

The new external dependency is only **`/bin/od`**, whose path and ordinary usage are documented by the existing outer receipt. The full offset/length/noncompression invocation has been tested locally, not yet on the board; outer smoke remains necessary. Remote command whitelist: `cat`, `ps`, `readlink`, `stat`, `/bin/od`, plus POSIX shell builtins. No awk/tr/wc, no device writes or process control.

## Entry (no execution in this task)

Fresh BOOT/PARENT_PID/PARENT_BIRTH must come from the outer's read-only identity. Output must be new. Preview only:

```sh
python3 benchmark/2026-10-24-ordinary-host-timeline/incremental-observer-hex/observe.py \
  --boot "$BOOT" --parent-pid "$PARENT_PID" --parent-birth "$PARENT_BIRTH" \
  --out "$NEW_PREVIEW_OUT"
```

For a separately authorized observation the outer may use a different new output directory plus `--execute`. Same fixed61b serial/UID,1s serial sampling,90s total,10s per command and1MiB combined captured stdout/stderr limits. **Hex expansion counts against that1MiB limit**; payload capacity is smaller than binary transport. No automatic UI/launch/stop/retry. Timeout cancellation affects only the local HDC client.

Every command retains exact argv, ASCII stdout, stderr and receipt in a new command directory. Sample ranges and hashes refer to decoded original bytes; wire receipts hash the encoded output. A birth transition keeps raw evidence and unaccepted offsets for re-reading. Repeated observations may overlap by design.

## Actual offline verification

17 tests pass, retaining the15 prior behaviors and adding strict-hex errors and NUL-loss transport comparison. The actual shell fixture uses local synthetic proc/log files and local od, with restricted PATH excluding awk/tr/ip/route/wpa_cli/ndc/wc; HDC is not invoked. It applies NUL deletion to the emitted stream and checks exact restoration of cmdline and log bytes including00/ff. Old v1 framing fails the same simulated loss. The18,592-byte ps fixture completes90 samples with714,210 captured bytes in the first final run; byte counts may vary slightly with fixture inode numbers. No guarantee is made that arbitrary real log volume permits the full90seconds.

Validation/raw evidence and source hashes are recorded separately here. The accepted v1 manifests are not rewritten. Runtime/UI/signature source files, stopped control objects and REA were not accessed.
