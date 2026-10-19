# T11 5cd window: start failed before a business child

The initial launch was rejected by the launcher-focus guard before selecting or clicking an icon. The associated image is a lock screen, not an application failure. The outer operator then used the separately preserved unlock helper and clicked the exact host icon once on desktop page 9. Its first image shows **Westlake IME host**. The final image is another lock screen; it cannot establish why a feed was not observed.

The 366-second window closed at 06:43:18 on 2026-10-20. Both collectors reported no business child. The historical before-only collector returned 0; the fixed after-ui collector returned 2. Guardian raw evidence says `START_FAILED`, sequence 0, `spawn_command_nonzero`; its event identifies parent 19163/birth 7265322, while the state header retains `parent=none`. No child-exit cause is inferred.

`facts.txt` is the unmodified output of MAIN run_facts over the actual five record directories: four captured images, five unknown liveness results. The failed first launch has zero screenshots and is retained. Images were inspected independently: three lock screens and one host screen. There is no feed or playback success claim.

## Evidence and source boundary

- `close.json`, `results.json`, `evidence/`, `records/`, and `screenshots/` bind the actual window.
- `source-provenance.json` distinguishes the frozen 703 before-only producer from the fixed 67ece after-ui collector and the two historical outer UI scripts. Scripts are execution evidence, not portable authorization to replay this window.
- `public-source-index.json` binds original SHA/size and sanitized public bytes. Private paths use BASE20, WORKSPACES and HOME aliases. Original bytes and command stdout/stderr/rc remain in the raw archive.
- No runtime source/build, deployment, reboot, debugger attach, GOT read, settings change, or video tap occurred. UI wake, unlock swipe, desktop navigation, one icon click and screenshots did occur.
- Archive status is recorded separately; local packing must not be described as remote verification.

No frozen implementation, earlier review, API table, or device was changed by this evidence review. Startup-chain analysis belongs to the separately assigned lane.
