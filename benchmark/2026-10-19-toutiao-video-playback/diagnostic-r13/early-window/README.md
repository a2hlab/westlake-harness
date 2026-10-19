# R13 early-readiness window: restored, no attachment

**The first readiness check compared a truncated proc comm name with a full ps NAME.** It selected no child and expired. The correction fixed the full ps name and pinned the same parent/child births. Its nine maps reads all lacked the exact player path while the other four required paths were present. The debugger server was staged, but attach was never invoked, no admission was created, and the observer produced no samples. This is not a debugger failure or a playback result.

- Candidate identity: boot `a4dc8e54-9140-4a6a-b3b2-58bf8acb5c1d`, parent `5602/12828`, child `7462/14456`. The candidate feed image was independently viewed. This review does not investigate process exits or infer why the player was unmapped.
- First failure and corrected failure remain separate exact originals under `evidence/`. `name-correction.json` binds the actual ps row and proc stat; `maps-audit.json` independently repeats exact path checks against all nine retained maps responses. Path presence is not a provider/GOT or ABI proof.
- The original apply plan was rolled back, followed by fresh boot `dc29a1cf-ee43-42c5-8d72-839d50984a5e`. Parent `5455/7496`, child `8221/9117`; original run/media/player hashes and private inode equality verified, compat absent. Same-plan **64 targets / 351 labels** and comparable invariants are equal. Raw PID, uptime and mount strings are not required to remain equal across reboot.
- Final read-only receipts show child sleeping, `TracerPid=0`, no 5039 forward/listener and parameter absent (`errNum 106`). The independently viewed restored image shows the news feed. Feed visibility does not establish video playback.
- Lock `05:54:03`, unlock `06:05:37`, elapsed **694 seconds**. Window-close original is retained.

Main `run_facts.py` output is retained verbatim in [facts.txt](evidence/facts.txt):

```text
TOTAL keys=2 screenshots_captured=2/2 alive_t5=0 alive_last=0 alive_unknown=2
```

The two records do not supply the helper's standard liveness table. The separate final proc receipt does not rewrite this count. Runtime/tool fingerprint fields in facts remain unknown; exact restoration evidence is independently bound in `private-restore-review.json` and `snapshot-review.json`.

## Reproducible evidence review and raw preservation

`collect_evidence.py` only reads existing local evidence and runs the local facts helper. `SOURCE_REPO` selects MAIN; BASE19/BASE20 are the persistent directories under `$HOME/.local/share/westlake/`. `sources/` contains exact historical one-off scripts, including the erroneous first implementation and corrected r2. **They are evidence, not generic runnable deployment or admission tools.** No frozen observer or runtime was modified.

The full private archive includes both readiness failures, correction readout, all selected early-window preflight/apply/rollback/boot/live commands and logs, snapshots, server staging, restored checks, original execution scripts, and observer/spec source snapshots. Original bytes are preserved; public excerpts omit network rows and public record paths use aliases. The archive index records every member hash and size. Large raw logs, original command paths and the tar stay private.

Local archive: `.private/archive-01/window.tar.gz`; **4,825 members**, **2,281,380 bytes**, SHA256 `4c3bbc74f887b05998b7a3a40533f82f1e4bca5424421007ba6932f124e30f37`. Every member was re-read and hash/size checked; source files were rehashed after packing.

The lane's first SSH operation returned **255 / Operation not permitted**; it stopped before scp. This is a lane transport denial, not remote success. `archive/receipt.json` deliberately keeps `remote_verified=false`; `archive/upload-failure.txt` is a path-sanitized excerpt, with the original stderr SHA in the receipt. Outer can execute the exact three argv arrays in `.private/archive-01/remote-commands.private.json`, preserving each stdout/stderr/rc, and append its success receipt separately. Destination alias: `HW248_ARTIFACT_ROOT/toutiao-r13-early-20261020/window.tar.gz`. No retry, permission escalation or device command was issued by this reviewer.
