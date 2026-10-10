# Boot-bound sealed-child read-only probe

## Evidence and correction

The previous static report (master `dbe9143d67`,
`benchmark/2026-10-10-5ea-sigill-static/`) establishes **14 fresh 5ea forks**
failing bridge `dlopen` with `errno=13`, then loader result 10 and parent exit
123. It does **not** establish SIGILL or explain why only 5ea fails.
Healthy applications also emit handled signal-4 logs. Existing cross-board
snapshots used different plans; missing observations cannot be treated as
missing libraries. PID1's good label does not prove the failed child's path
view or execution-domain access.

This tool uses one fixed, hashed collection protocol on all three OH boards.
No deployment plan is required and no full-board snapshot PASS is claimed.
**Delivery validation is fixture-only. No HDC, VM, SSH, board lock, application
launch, reboot, relabel, bind, installer or deployment was performed.**
Wait for an outer-authorized idle-board window before `--capture`.

## One-command collection

Run from the lane worktree or landed master. `WORKSPACES` is the workspace root.
The full serial whitelist comes from `scripts/lab/lab_paths.py` and the master
`knowledge/boards.json`; short serials and arbitrary targets are refused.

```sh
PROBE="$WORKSPACES/westlake-harness/benchmark/2026-10-10-5ea-sealed-child-probe"
python3 "$PROBE/probe.py" \
  --serial 5ea34a4500000000000000001123012c \
  --serial 5cd1e3dd00000000000000000923012c \
  --serial 61b0657200000000000000000324012c
```

The command above is the **default dry-run**: prints protocol and serials,
does not instantiate HDC or contact any board. After explicit authorization,
use the same command with:

```sh
python3 "$PROBE/probe.py" \
  --serial 5ea34a4500000000000000001123012c \
  --serial 5cd1e3dd00000000000000000923012c \
  --serial 61b0657200000000000000000324012c \
  --capture --hdc hdc --out "$PROBE/.artifacts/capture"
```

Captures are sequential, **not simultaneous**. The flag is not authorization.
Output is `<out>/<full-serial>/<UTC-time>-<nonce>/probe.json` plus `raw/`.
Repeated calls and multiple boards can safely share the same controller output
root without overwriting earlier evidence. No file is written to a board.
The final stdout lists every JSON path and exit code.

Automatic discovery reads `ps -A -o PID,PPID,NAME`. It selects root
`appspawn-x` processes and their direct children, retaining all matches.
A child may inherit the name `appspawn-x`: PPID, not name alone, determines
its role. Host `/proc/PID/exe` must resolve to `/system/bin/appspawn-x`.
For a particular already-live child, use one serial with
`--host-pid <host> --child-pid <child>` (repeatable for multiple live PIDs).
An absent/foreign child is refused or reported unavailable. The probe never
starts an application to obtain a child. Without a live child it cannot answer
the child-domain question and returns a partial observation.

## Collected fields

- Fixed logical paths: `/system/android/lib64/liboh_adapter_bridge.so`,
  `/system/android/lib64/liboh_android_runtime.so`, `/system/bin/appspawn-x`.
- PID1, selected host and child: full raw `mountinfo`, mount-namespace link,
  executable link, status UID/GID/PPid, NUL-separated cmdline and `attr/current`.
- Each of the three paths **through each process's `/proc/PID/root`**:
  SHA256, `ls -ldnZ`, and ancestor-directory `ls -ldnZ` (mode, owner, label).
- Longest boundary-matching covering mount(s): root, mountpoint, filesystem,
  source, mount/super/optional flags, explicit `noexec` and `nosuid` booleans.
  Stacked equal-length matches are preserved, never arbitrarily selected.
  Mount root/source are evidence, not a guessed physical backing pathname.
- Boot UUID before/after; process PID+PPID+starttime and mountinfo before/after.
  A reboot, PID reuse or changing mountinfo makes that scope incomparable.
- `getenforce` and optional recover `receipt.env`: parsed fields and whether
  its `boot_id` matches this capture. Receipt absence/staleness stays explicit;
  it is diagnostic, not proof of current bind count or permission.
- Every read retains exact command, remote-exit sentinel, **host AND remote
  exit**, stdout/stderr, byte hashes, and start/end UTC timestamps. Host HDC
  exit zero is not accepted when the board command failed or the sentinel is
  missing. UTF8 decoding never discards the raw byte evidence.

Allowed remote operations are only `cat`, `ls`, `sha256sum`, `readlink`, `ps`,
`getenforce`, with a subshell/`printf` exit sentinel. No board tools such as
`tr` are required. Kernel/proc reads can fail or processes can disappear; their
failure output remains preserved. The protocol is not an atomic snapshot.
Reads via proc roots are made by the observer, **not by the app domain**;
successful reads do not prove the child's `dlopen` is permitted.

## Offline three-board comparison

```sh
python3 "$PROBE/probe.py" --compare \
  <5ea-probe.json> <5cd-probe.json> <61b-probe.json> > comparison.json
```

The comparison verifies equal protocol hashes and all raw-file SHA pins. It
emits a serial/boot/role/PID/path matrix with SHA, label, execution domain and
mount flags; known PID1 SHA/label/restriction differences are also listed.
Different PID numbers or mount-namespace inode numbers are not by themselves
drift. Host/child rows must be aligned by the operator to the intended live
application; the tool does not invent cross-board app identity or match a dead
historical child to a present one. Unknown child observations are listed in
`unavailable`, never counted as equal or safe.

Exit codes: **0 = requested observations complete**, not permission PASS or
lit; **1 = partial/unavailable scope**; **2 = boot-binding failure or invalid
input/evidence**. Optional receipt/cmdline failures remain visible even when
the required loader scope is complete. Current observations cannot retroactively
explain the failed boot `31259bd5-a7ff-416f-bf5a-248dbef17688`.

## Validation and handoff

```sh
python3 -m unittest discover -s "$PROBE" -p 'test_*.py' -v
```

`evidence/tests.txt` records 19 known-answer tests: valid scope, default no-contact
dry-run, read-only allowlist, all three serials, unknown child, boot/PID/mount
drift, longest/stacked/escaped mounts, HDC-host-zero/remote-failure, missing exit
sentinel, explicit/foreign PIDs, inherited child names, whitelist and injection
guards, repeated output roots, evidence tampering, diagnostic-only receipt,
known noexec delta, and an actual **local `/bin/sh`** sentinel test (no device).
`evidence/dry-run.json` was generated without board contact.

Landing: `landing-paths.txt`; path/size preflight output in `evidence/`.
`documentation.json` contains append-only README layout/DIGEST snippets for the
outer lane; it does not replace the lane's unrelated dirty documentation.
Live collection and determination of the 5ea access-denial cause remain pending
an authorized idle-board window. No window is requested or consumed here.
