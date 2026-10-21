# G34 closed: runtime restored, game failed

**CLOSED_RESTORED_GAME_FAILED** at **2026-10-21 23:31:28.437446 +08:00**, elapsed **1179.437446 seconds**. Original U7 apply reached `active_verified` (rc0,36 operations); original rollback reached `rolled_back` (rc0). This package is an offline evidence compilation, not a new device execution or game acceptance.

The first UI attempt failed before clicking: the remote layout directory was absent. Its local command rc0 carried a remote marker1 and the original failure is retained. The second attempt contains **one ordinary Genshin icon click**. The first actual image is white content with system bars; the later image is the launcher. Parent27555 reports child29761 exited with **signal11** at23:22:11.437 (hilog L3791). No game frame, fault PC or stack was obtained. Prior locale relocation messages were not seen in the supplied log; that does not establish a general API freeze or a provider winner.

## Restored state and limits

Offline comparison of actual records confirmed **319 direct and319 parent-view hashes** exactly equal the original apply-plan baseline, **61 tracked mount-target stacks** equal, and the Boat3 stdout byte-identical before/after. Control images before the game and after rollback were actually read: both show Hello World's own controls and CREATED/RESUMED text. Those images prove the control UI only. Subsequent power readback is **SLEEP / Timeout30000 / Override10000**. Unlock returned0; held-after returned1 with empty stdout.

The original cleanup helper checked UID/PPID but **did not recheck stat-birth in the kill shell**; this is not full birth-bracketed cleanup. Two final force-stop bodies reported10106401 despite marker0, so they are not counted as successful stop operations. The later repeated process tables show no processes with the test UIDs20011065 and20011077. Independent closure review `8ae5c0fe…` confirms these scoped findings.

## Diagnostic failures remain evidence

The in-window Dfx query combined `-x` and `-z`: outer rc0, but stdout **CODE:-31**, so it was not a successful empty query. After closure, the standard single-mode tag query returned rc0/empty output. A full-buffer query then hit25 seconds and returned only a partial log ending23:17:38, **before the23:22 target**. Neither result proves that no system crash record exists. Signal11 is established; cause, faulting TID/PC and stack remain unknown. No speculative GLES/libc-warning attribution is made.

## Facts, originals and admission

`facts.txt` is the original normalized facts-view output, copied without alteration. It reports game screenshots2/2, t5 unknown (not sampled) and t20 no. Its `child_hilog=0` field does not mean the separately indexed664,781-byte hilog is absent. The four unmodified public images are the two game images plus two separate control images; they are not four game samples. Earlier generic tool output in the triage packet used a different layout and is not rewritten here.

`private-raw-index.json` records every regular file under the closed window using `$HOME` paths, SHA256 and byte length. Full journals, stderr, large logs and desktop layouts stay private. `postclose-input-index.json` separately records the later diagnostics. Selected receipts are exact bytes where possible; `receipts-index.json` marks path-only sanitization and retains each original SHA. Remote archive verification is **pending**; the outer archive process is not treated as a verified receipt.

`admission-retirement.json` is a **post-window declaration**, not a changed signature. The original admission is retained, including its legacy `approved_by=outer(claude)` protocol field and actual reviewer `outer(codex)`. The actual retirement receipt records318 exceptions retired and the registry restored. Closed holder/start/admission authorize no further writes. This packager changed neither registry nor original admission.

Validation: `python3 check_closed.py` checks public evidence; `--raw` additionally verifies the exact persistent input index and recomputes restoration from the original plan/hashes. Neither mode invokes devices, VM, compilation or deployment. No shared Git index write is retried; outer may land `landing-paths.txt` (JPEG files require force-add under repository ignore rules).
