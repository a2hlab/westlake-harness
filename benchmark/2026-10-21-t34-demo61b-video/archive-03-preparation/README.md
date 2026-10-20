# W03 follow-up archive: prepared, not executed

No live files were snapshotted and no upload occurred. The persistent private script is `$HOME/.local/share/westlake/t34-window-archive-03-preparation/archive.py`, pinned in `results.json`. It reuses the original archive SSH/SCP argv configuration and the exact original command-2 remote verifier without publishing accounts or personal paths.

After root explicitly confirms W-03 and W-03-b closed and unlocked, provide a private JSON confirmation with `approved_by: outer(codex)`, `status: CLOSED_AND_UNLOCKED`, `windows: [W-03, W-03-b]`, and nonempty `evidence` entries containing local receipt `path` (HOME alias allowed) and `sha256`. Then run:

```sh
python3 "$HOME/.local/share/westlake/t34-window-archive-03-preparation/archive.py" \
  --execute --closed-confirmation "$PRIVATE/root-closed.json" \
  --out "$HOME/.local/share/westlake/t34-window-archive-03"
```

The output directory must be new and outside the source roots. Sources are exactly W-03, W-03-b and the network-readiness directory. Every regular source file is included, with per-file size/SHA, stat checks around reading and a final inventory stability comparison. Symlinks or source changes reject before upload. Local archive replay verifies payloads first.

Remote destination is `HW248_ARTIFACT_ROOT/t34-demo61b-video-20261021/window-03.tar.gz`. An exclusive reservation and hard-link publication refuse an existing destination; the old `window.tar.gz` is never a write target. Upload goes to the reserved staging path. Original remote member verification is command-3 in this new sequence (reserve/upload/publish/verify); exact argv/stdin/stdout/stderr/rc persist, including timeout partial output. Any failure stops without automatic retry. Reservation/staged bytes remain as evidence; do not blindly remove or reuse them.

The final `receipt.json` is written only after the remote archive SHA/size and every payload match. Root can then publish an actual receipt and append its exact API references. Current hashes/size/member count are deliberately null; this preparation does not assert closure, runtime recovery or video success.
