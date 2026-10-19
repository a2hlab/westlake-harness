# Fixed byte delta recipe for the next separately admitted playback window

This is a small host helper and shell recipe, not a device executor or a new
board framework. It does not acquire a lock, choose a PID, launch an app, click,
modify settings, or authorize T13 video work. No device operation was performed.

Reuse the exact identity guards and command recorder in the accepted
`benchmark/2026-10-20-5cd-icon-readiness/collect.py` `read()`/`run()` logic:
same boot, child and parent PID/birth/PPID, UID, live state, TracerPid=0 and exe
SHA. Keep the holder check and monotonic remaining-window budget. Do not reuse
T12's PID or boot blindly; bind a fresh identity receipt in the new window.

1. Before the actual visible play click, under those guards, confirm fd2's
   target is the known regular child log and use `stat_body(path)` to obtain
   device:inode:size. Save all command bytes/rc. Build `snapshot(...)` with the
   SHA of this window's identity receipt. No FIFO/socket, arbitrary path, or
   unknown pointer read is permitted.
2. After the outer's one normal UI action, use the same pinned identity and
   stat the same file. If identity, device or inode changed, or size shrank,
   refuse. No child reselection. The wrapper must independently verify fd2
   still names that regular file. Never use a whole-file hilog/grep pipeline.
3. `read_recipe(before, after, identity_guard, unique_marker)` produces one
   `dd bs=4096 skip=N count=M` bounded read, with identity and regular-file
   checks before/after. Default cap is 262,144 selected bytes; block alignment
   may capture up to 4,095 bytes before the offset and 4,095 bytes after the
   selected end. Both raw and exact selected bytes are preserved. Bytes
   appended after the after-snapshot are not part of the selected interval.
4. The existing outer may pass its exact HDC argv and at most
   `min(10, remaining_budget)` seconds to `capture(...)`. No retry is built in.
   Timeout retains stdout/stderr and yields PARTIAL_UNVERIFIED even if useful
   error text is present. The postguard marker is mandatory for bounded-byte
   completion, and completion is never a player-success or whole-window claim.

Example integration shape (not an executable board command):

```python
before = snapshot(path, existing_read(stat_body(path)), identity_receipt_sha)
# Outer only: one actual visible play action, under its separate admission.
after = snapshot(path, existing_read(stat_body(path)), identity_receipt_sha)
recipe = read_recipe(before, after, exact_existing_identity_guard, marker)
# Outer rechecks same holder + remaining monotonic budget before capture.
result = capture([hdc, '-t', admitted_serial, 'shell', recipe['script']],
                 fresh_persistent_output, recipe, min(10, remaining))
```

Integration limit: host tests use a real local shell/dd but adapt the metadata
stat syntax for macOS. They do not verify the OH dd/toolbox implementation or
HDC stdout/stderr separation. The recipe requires a separate stderr channel for
the marker/diagnostics. If HDC merges it, completion must remain unverified;
the outer must review transport framing before adoption, not weaken the marker
test. Saved raw bytes still remain evidence with this limitation. The helper
does not claim file immutability: append is expected; in-place overwrite or
truncate-and-regrow cannot be excluded by inode/size alone.

Interpret only actual executed loader/exception lines. Configuration JSON
matches are not execution. A cap cut, absent marker, or no observed player
attempt leaves the video cause unknown. The next action is an observation,
not an extraction or runtime repair.
