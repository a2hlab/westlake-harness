# R5: preserve cmdline NUL across HDC shell transport

## Evidence first

The original HDC shell `cat /proc/4344/cmdline` dropped NUL bytes. The frozen
validator correctly rejected that lossy recording. Do not weaken its NUL test.
Outer independently proved OH `set -o pipefail` and `od -An -v -tx1` work in
`$WORKSPACES/westlake-harness/benchmark/2026-10-12-v1-seal-execution/61b-binary-read-probe/001-encoded-cmdline.{json,stdout}`.
The decoded **275 bytes** have board SHA
`02d57f611f6aeb98c4c796a5925fff85f8907113ab924b42c66f5aa0d6ddbf5c`.
The tests reproduce this decode locally; they do not claim a new device read.

## Narrow implementation

BinarySafeCollector subclasses the exact pinned original ReadOnlyCollector.
Only `host_cmdline` accepts the canonical logical command `cat /proc/PID/cmdline`.
Actual transport is `set -eu; set -o pipefail; cat ... | od -An -v -tx1`, followed
by a board SHA256 read. The original collector checks host/remote exits first.
Strict two-digit hex decoding and matching full board SHA precede acceptance.
Missing/truncated hex, repetition markers, wrong digest/path, transport failure
and missing/nonzero remote exit refuse; no accepted decoded output is emitted.
Every other read delegates unchanged to the original collector.

The original encoded stdout, transport stdout, stderr and transport JSON remain
intact. A separate `.decoded.stdout` retains the actual bytes including NUL.
`.binary.json` pins encoded/decoded evidence, logical cat, actual wrapped argv,
board SHA, decoder/adapter source SHA and acceptance status. The returned reading
uses the logical command and decoded typed stdout pin required by the unchanged
validator; its binary_transport pin explicitly identifies the real transport.

No compiler, validator, compare, frozen helper or existing pin file is modified.
The independent entry injects only this collector into original selfcheck or R3,
including after R3 selects its proof's frozen directory. Existing proof/history/
current-boot/WMS/UID checks and live-versus-offline status remain unchanged.

## Source WMS sampler import (outer only)

Import this class into the existing source sampler instead of the old collector:

```python
from binary_safe_collector import BinarySafeCollector
collector = BinarySafeCollector(hdc_path, serial, fresh_evidence_directory)
raw, reading = collector.read("host_cmdline", "cat /proc/4344/cmdline")
```

Use the independently observed host PID, not the example PID blindly. Keep the
parameter observation JSON beside the collector's evidence directory, or make
its stdout/binary_transport pins correctly relative/WORKSPACES-portable. Refresh
the complete source observation and independent boot/WMS/proc evidence; do not
silently replace old lossy evidence or treat a file-derived WID as proof. The
raw return is bytes; do not decode/re-encode it before passing to the validator.
Other source reads use the same collector unchanged.

## Both actual selfcheck entrypoints (outer only)

Set R5 to the landed review directory `r5-binary-collector`. The original flags
are forwarded unchanged after the explicit selector:

```sh
python3 "$R5/selfcheck_entry.py" --checker realization \
  --realization "$PROOF" --serial "$SERIAL" --boot-id "$CURRENT_BOOT" \
  --hdc "$HDC" --out "$FRESH_RECEIPT"

python3 "$R5/selfcheck_entry.py" --checker activation \
  --activation-binding "$ACTIVATION_BINDING" --binding-sha256 "$BINDING_SHA" \
  --serial "$SERIAL" --boot-id "$CURRENT_BOOT" --hdc "$HDC" --out "$FRESH_RECEIPT"
```

Replace --hdc with --observed for explicitly offline comparison; it cannot yield
live PASS. Missing/drifted pinned dependencies refuse. The activation checker
continues to require actual completed 487-ticket placement history and preserves
all final-seal extra static and non-file checks. No device read was executed by
the inner lane. Outer owns actual collection and final signoff.

## Reproduction

`python3 test_binary_collector.py` runs only narrow local/mock tests, including
actual probe byte decoding, unchanged strict NUL validator, other-read passthrough,
remote/host failure, malformed encoding/digest and both injection entrypoints.
Results and original stdout/stderr/exit are delivered beside these sources.
No old transaction matrix, build, VM, device write, privacy operation or reboot.
